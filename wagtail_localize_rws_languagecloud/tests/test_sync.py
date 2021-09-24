import datetime
import logging
import polib
from unittest.mock import Mock
from django.test import TestCase, override_settings
from wagtail.core.models import Page, Locale
from wagtail_localize.models import TranslationSource, Translation
from wagtail_localize.test.models import TestPage
from freezegun import freeze_time
from requests.exceptions import RequestException
from ..models import LanguageCloudProject
from ..rws_client import ApiClient, NotAuthenticated
import wagtail_localize_rws_languagecloud.sync as sync


def create_test_page(**kwargs):
    parent = kwargs.pop("parent", None) or Page.objects.get(slug="home")
    page = parent.add_child(instance=TestPage(**kwargs))
    revision = page.save_revision()
    revision.publish()
    source, created = TranslationSource.get_or_create_from_instance(page)
    return page, source


def create_test_po(entries):
    po = polib.POFile(wrapwidth=200)
    po.metadata = {
        "POT-Creation-Date": str(datetime.datetime.utcnow()),
        "MIME-Version": "1.0",
        "Content-Type": "text/html; charset=utf-8",
    }

    for entry in entries:
        po.append(polib.POEntry(msgctxt=entry[0], msgid=entry[1], msgstr=entry[2]))

    return po


class TestImport(TestCase):
    def setUp(self):
        self.locale_en = Locale.objects.get(language_code="en")
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.translations = []
        self.po_files = []
        self.lc_projects = []
        for i in range(0, 2):
            _, source = create_test_page(
                title=f"Test page {i}",
                slug=f"test-page-{i}",
                test_charfield=f"Some test translatable content {i}",
            )
            self.translations.append(
                Translation.objects.create(
                    source=source,
                    target_locale=self.locale_fr,
                )
            )
            self.po_files.append(
                create_test_po(
                    [
                        (
                            "test_charfield",
                            f"Some test translatable content {i}",
                            f"Certains tests de contenu traduisible {i}",
                        )
                    ]
                )
            )
            self.lc_projects.append(
                LanguageCloudProject.objects.create(
                    translation=self.translations[i],
                    source_last_updated_at=self.translations[i].source.last_updated_at,
                    internal_status=LanguageCloudProject.STATUS_NEW,
                    lc_project_id=f"proj{i}",
                    lc_source_file_id=f"file{i}",
                )
            )
        self.logger = logging.getLogger(__name__)
        logging.disable()  # supress log output under test

    def test_import_all_api_calls_succeed(self):
        client = ApiClient()
        client.is_authorized = True
        client.get_project = Mock(
            side_effect=[{"status": "completed"}, {"status": "completed"}], spec=True
        )
        client.download_target_file = Mock(
            side_effect=[str(self.po_files[0]), str(self.po_files[1])], spec=True
        )
        sync._import(client, self.logger)
        self.assertEqual(client.get_project.call_count, 2)
        self.assertEqual(client.download_target_file.call_count, 2)
        lc_projects = [
            LanguageCloudProject.objects.all().get(
                translation=t, source_last_updated_at=t.source.last_updated_at
            )
            for t in self.translations
        ]
        self.assertEqual(
            lc_projects[0].internal_status, LanguageCloudProject.STATUS_IMPORTED
        )
        self.assertEqual(
            lc_projects[1].internal_status, LanguageCloudProject.STATUS_IMPORTED
        )

    def test_import_all_get_project_calls_fail(self):
        client = ApiClient()
        client.is_authorized = True
        client.get_project = Mock(side_effect=RequestException("oh no"), spec=True)
        client.download_target_file = Mock(
            side_effect=ValueError("this should never be called"), spec=True
        )
        sync._import(client, self.logger)
        self.assertEqual(client.get_project.call_count, 2)
        self.assertEqual(client.download_target_file.call_count, 0)
        lc_projects = [
            LanguageCloudProject.objects.all().get(
                translation=t, source_last_updated_at=t.source.last_updated_at
            )
            for t in self.translations
        ]
        self.assertEqual(
            lc_projects[0].internal_status, LanguageCloudProject.STATUS_NEW
        )
        self.assertEqual(
            lc_projects[1].internal_status, LanguageCloudProject.STATUS_NEW
        )

    def test_import_some_get_project_calls_fail(self):
        client = ApiClient()
        client.is_authorized = True
        client.get_project = Mock(
            side_effect=[RequestException("oh no"), {"status": "completed"}], spec=True
        )
        client.download_target_file = Mock(
            side_effect=[str(self.po_files[0]), str(self.po_files[1])], spec=True
        )
        sync._import(client, self.logger)
        self.assertEqual(client.get_project.call_count, 2)
        self.assertEqual(client.download_target_file.call_count, 1)
        lc_projects = [
            LanguageCloudProject.objects.all().get(
                translation=t, source_last_updated_at=t.source.last_updated_at
            )
            for t in self.translations
        ]
        self.assertEqual(
            lc_projects[0].internal_status, LanguageCloudProject.STATUS_NEW
        )
        self.assertEqual(
            lc_projects[1].internal_status, LanguageCloudProject.STATUS_IMPORTED
        )

    def test_import_no_records_to_process(self):
        self.lc_projects[0].internal_status = LanguageCloudProject.STATUS_IMPORTED
        self.lc_projects[0].save()
        self.lc_projects[1].internal_status = LanguageCloudProject.STATUS_IMPORTED
        self.lc_projects[1].save()

        client = ApiClient()
        client.is_authorized = True
        client.get_project = Mock(
            side_effect=[{"status": "complete"}, {"status": "complete"}], spec=True
        )
        client.download_target_file = Mock(
            side_effect=[self.po_files[0], self.po_files[1]], spec=True
        )
        sync._import(client, self.logger)
        self.assertEqual(client.get_project.call_count, 0)
        self.assertEqual(client.download_target_file.call_count, 0)


class TestExport(TestCase):
    def setUp(self):
        self.locale_en = Locale.objects.get(language_code="en")
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.translations = []
        for i in range(0, 2):
            _, source = create_test_page(
                title=f"Test page {i}",
                slug=f"test-page-{i}",
                test_charfield=f"Some test translatable content {i}",
            )
            self.translations.append(
                Translation.objects.create(
                    source=source,
                    target_locale=self.locale_fr,
                )
            )
        self.logger = logging.getLogger(__name__)
        logging.disable()  # supress log output under test

    def test_export_all_api_calls_succeed(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(
            side_effect=[{"id": "abc123"}, {"id": "abc456"}], spec=True
        )
        client.create_source_file = Mock(
            side_effect=[{"id": "def123"}, {"id": "def456"}], spec=True
        )
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 2)
        self.assertEqual(client.create_source_file.call_count, 2)
        lc_projects = [
            LanguageCloudProject.objects.all().get(
                translation=t, source_last_updated_at=t.source.last_updated_at
            )
            for t in self.translations
        ]
        self.assertEqual(lc_projects[0].lc_project_id, "abc123")
        self.assertEqual(lc_projects[0].lc_source_file_id, "def123")
        self.assertEqual(lc_projects[0].project_create_attempts, 1)
        self.assertEqual(lc_projects[0].source_file_create_attempts, 1)
        self.assertEqual(lc_projects[1].lc_project_id, "abc456")
        self.assertEqual(lc_projects[1].lc_source_file_id, "def456")
        self.assertEqual(lc_projects[1].project_create_attempts, 1)
        self.assertEqual(lc_projects[1].source_file_create_attempts, 1)

    def test_export_all_create_project_api_calls_fail(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(side_effect=RequestException("oh no"), spec=True)
        client.create_source_file = Mock(
            side_effect=ValueError("this should never be called"), spec=True
        )
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 2)
        self.assertEqual(client.create_source_file.call_count, 0)
        lc_projects = [
            LanguageCloudProject.objects.all().get(
                translation=t, source_last_updated_at=t.source.last_updated_at
            )
            for t in self.translations
        ]
        self.assertEqual(lc_projects[0].lc_project_id, "")
        self.assertEqual(lc_projects[0].lc_source_file_id, "")
        self.assertEqual(lc_projects[0].project_create_attempts, 1)
        self.assertEqual(lc_projects[0].source_file_create_attempts, 0)
        self.assertEqual(lc_projects[1].lc_project_id, "")
        self.assertEqual(lc_projects[1].lc_source_file_id, "")
        self.assertEqual(lc_projects[1].project_create_attempts, 1)
        self.assertEqual(lc_projects[1].source_file_create_attempts, 0)

    def test_export_some_create_project_api_calls_fail(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(
            side_effect=[RequestException("oh no"), {"id": "abc456"}], spec=True
        )
        client.create_source_file = Mock(side_effect=[{"id": "def456"}], spec=True)
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 2)
        self.assertEqual(client.create_source_file.call_count, 1)
        lc_projects = [
            LanguageCloudProject.objects.all().get(
                translation=t, source_last_updated_at=t.source.last_updated_at
            )
            for t in self.translations
        ]
        self.assertEqual(lc_projects[0].lc_project_id, "")
        self.assertEqual(lc_projects[0].lc_source_file_id, "")
        self.assertEqual(lc_projects[0].project_create_attempts, 1)
        self.assertEqual(lc_projects[0].source_file_create_attempts, 0)
        self.assertEqual(lc_projects[1].lc_project_id, "abc456")
        self.assertEqual(lc_projects[1].lc_source_file_id, "def456")
        self.assertEqual(lc_projects[1].project_create_attempts, 1)
        self.assertEqual(lc_projects[1].source_file_create_attempts, 1)

    def test_export_no_records_to_process(self):
        LanguageCloudProject.objects.create(
            translation=self.translations[0],
            source_last_updated_at=self.translations[0].source.last_updated_at,
            internal_status=LanguageCloudProject.STATUS_IMPORTED,
        )
        LanguageCloudProject.objects.create(
            translation=self.translations[1],
            source_last_updated_at=self.translations[1].source.last_updated_at,
            internal_status=LanguageCloudProject.STATUS_IMPORTED,
        )
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(
            side_effect=[{"id": "abc123"}, {"id": "abc456"}], spec=True
        )
        client.create_source_file = Mock(
            side_effect=[{"id": "def123"}, {"id": "def456"}], spec=True
        )
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 0)
        self.assertEqual(client.create_source_file.call_count, 0)


class TestHelpers(TestCase):
    def setUp(self):
        self.locale_en = Locale.objects.get(language_code="en")
        self.locale_fr = Locale.objects.create(language_code="fr")
        _, source = create_test_page(
            title=f"Test page",
            slug=f"test-page",
            test_charfield=f"Some test translatable content",
        )
        self.translation = Translation.objects.create(
            source=source,
            target_locale=self.locale_fr,
        )
        self.logger = logging.getLogger(__name__)
        logging.disable()  # supress log output under test

    @freeze_time("2018-02-02 12:00:01")
    def test_get_project_name_without_custom_prefix(self):
        self.assertEqual(
            sync._get_project_name(self.translation, self.locale_en),
            "Test page_French_2018-02-02"
        )

    @freeze_time("2018-02-02 12:00:01")
    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={"PROJECT_PREFIX": "Website_"},
    )
    def test_get_project_name_with_custom_prefix(self):
        self.assertEqual(
            sync._get_project_name(self.translation, self.locale_en),
            "Website_Test page_French_2018-02-02",
        )

    @freeze_time("2018-02-02 12:00:01")
    def test_get_project_due_date_without_custom_delta(self):
        self.assertEqual(sync._get_project_due_date(), "2018-02-09T12:00:01.000Z")

    @freeze_time("2018-02-02 12:00:01")
    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={"DUE_BY_DELTA": datetime.timedelta(days=14)},
    )
    def test_get_project_due_date_with_custom_delta(self):
        self.assertEqual(sync._get_project_due_date(), "2018-02-16T12:00:01.000Z")

    def test_create_project_success(self):
        lc_project = LanguageCloudProject(
            translation=self.translation,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(return_value={"id": "abc123"}, spec=True)
        id_ = sync._create_project(
            lc_project,
            client,
            "faketitle",
            "2020-01-01T00:00:01.000Z",
            "fakedesc",
        )
        lc_project.refresh_from_db()
        self.assertEqual(id_, "abc123")
        self.assertEqual(lc_project.lc_project_id, "abc123")
        self.assertEqual(lc_project.project_create_attempts, 1)

    def test_create_project_fail(self):
        lc_project = LanguageCloudProject(
            translation=self.translation,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(side_effect=RequestException("oh no"), spec=True)
        with self.assertRaises(RequestException):
            sync._create_project(
                lc_project,
                client,
                "faketitle",
                "2020-01-01T00:00:01.000Z",
                "fakedesc",
            )
        lc_project.refresh_from_db()
        self.assertEqual(lc_project.lc_project_id, "")
        self.assertEqual(lc_project.project_create_attempts, 1)

    def test_create_source_file_success(self):
        lc_project = LanguageCloudProject(
            translation=self.translation,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        client = ApiClient()
        client.is_authorized = True
        client.create_source_file = Mock(return_value={"id": "abc123"}, spec=True)
        sync._create_source_file(
            lc_project,
            client,
            "fakeproject",
            "fakepo",
            "fakefilename.po",
            "en-US",
            "fr-CA",
        )
        lc_project.refresh_from_db()
        self.assertEqual(lc_project.lc_source_file_id, "abc123")
        self.assertEqual(lc_project.source_file_create_attempts, 1)

    def test_create_source_file_fail(self):
        lc_project = LanguageCloudProject(
            translation=self.translation,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        client = ApiClient()
        client.is_authorized = True
        client.create_source_file = Mock(
            side_effect=RequestException("oh no"), spec=True
        )
        with self.assertRaises(RequestException):
            sync._create_source_file(
                lc_project,
                client,
                "fakeproject",
                "fakepo",
                "fakefilename.po",
                "en-US",
                "fr-CA",
            )
        lc_project.refresh_from_db()
        self.assertEqual(lc_project.lc_source_file_id, "")
        self.assertEqual(lc_project.source_file_create_attempts, 1)

    def test_should_export_already_imported(self):
        self.assertFalse(
            sync._should_export(
                self.logger,
                LanguageCloudProject(
                    translation=self.translation,
                    source_last_updated_at=self.translation.source.last_updated_at,
                    internal_status=LanguageCloudProject.STATUS_IMPORTED,
                ),
            )
        )

    def test_should_export_project_and_source_file_created(self):
        self.assertFalse(
            sync._should_export(
                self.logger,
                LanguageCloudProject(
                    translation=self.translation,
                    source_last_updated_at=self.translation.source.last_updated_at,
                    lc_project_id="abc123",
                    lc_source_file_id="def456",
                ),
            )
        )

    def test_should_export_too_many_fails(self):
        self.assertFalse(
            sync._should_export(
                self.logger,
                LanguageCloudProject(
                    translation=self.translation,
                    source_last_updated_at=self.translation.source.last_updated_at,
                    project_create_attempts=3,
                    source_file_create_attempts=0,
                ),
            )
        )
        self.assertFalse(
            sync._should_export(
                self.logger,
                LanguageCloudProject(
                    translation=self.translation,
                    source_last_updated_at=self.translation.source.last_updated_at,
                    project_create_attempts=0,
                    source_file_create_attempts=3,
                ),
            )
        )

    def test_should_should_export(self):
        self.assertTrue(
            sync._should_export(
                self.logger,
                LanguageCloudProject(
                    translation=self.translation,
                    source_last_updated_at=self.translation.source.last_updated_at,
                ),
            )
        )
        self.assertTrue(
            sync._should_export(
                self.logger,
                LanguageCloudProject(
                    translation=self.translation,
                    source_last_updated_at=self.translation.source.last_updated_at,
                    project_create_attempts=2,
                    source_file_create_attempts=0,
                ),
            )
        )
        self.assertTrue(
            sync._should_export(
                self.logger,
                LanguageCloudProject(
                    translation=self.translation,
                    source_last_updated_at=self.translation.source.last_updated_at,
                    project_create_attempts=2,
                    source_file_create_attempts=2,
                ),
            )
        )
