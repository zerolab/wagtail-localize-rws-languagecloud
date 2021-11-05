import datetime
import logging
from unittest.mock import Mock

import polib
from django.test import TestCase, override_settings
from freezegun import freeze_time
from requests.exceptions import RequestException
from wagtail.core.models import Locale, Page
from wagtail_localize.models import Translation, TranslationSource
from wagtail_localize.test.models import TestPage

import wagtail_localize_rws_languagecloud.sync as sync

from ..models import LanguageCloudFile, LanguageCloudProject
from ..rws_client import ApiClient


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
        self.lc_files = []
        for i in range(0, 2):
            _, source = create_test_page(
                title=f"Test page {i}",
                slug=f"test-page-{i}",
                test_charfield=f"Some test translatable content {i}",
            )
            translation = Translation.objects.create(
                source=source,
                target_locale=self.locale_fr,
            )
            self.translations.append(translation)
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
            project = LanguageCloudProject.objects.create(
                translation_source=source,
                source_last_updated_at=source.last_updated_at,
                internal_status=LanguageCloudProject.STATUS_NEW,
                lc_project_id=f"proj{i}",
            )
            self.lc_projects.append(project)
            file_ = LanguageCloudFile.objects.create(
                translation=translation,
                project=project,
                lc_source_file_id=f"file{i}",
                internal_status=LanguageCloudFile.STATUS_NEW,
            )
            self.lc_files.append(file_)

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
        for proj in self.lc_projects:
            proj.refresh_from_db()
            self.assertEqual(proj.internal_status, LanguageCloudProject.STATUS_IMPORTED)
        for file_ in self.lc_files:
            file_.refresh_from_db()
            self.assertEqual(file_.internal_status, LanguageCloudFile.STATUS_IMPORTED)

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
        for proj in self.lc_projects:
            proj.refresh_from_db()
            self.assertEqual(proj.internal_status, LanguageCloudProject.STATUS_NEW)
        for file_ in self.lc_files:
            file_.refresh_from_db()
            self.assertEqual(file_.internal_status, LanguageCloudFile.STATUS_NEW)

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
        for proj in self.lc_projects:
            proj.refresh_from_db()
        for file_ in self.lc_files:
            file_.refresh_from_db()
        self.assertEqual(
            self.lc_projects[0].internal_status, LanguageCloudProject.STATUS_NEW
        )
        self.assertEqual(self.lc_files[0].internal_status, LanguageCloudFile.STATUS_NEW)
        self.assertEqual(
            self.lc_projects[1].internal_status, LanguageCloudProject.STATUS_IMPORTED
        )
        self.assertEqual(
            self.lc_files[1].internal_status, LanguageCloudFile.STATUS_IMPORTED
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

    def test_import_with_an_exception_finished_processing(self):
        client = ApiClient()
        client.is_authorized = True
        client.get_project = Mock(
            side_effect=[{"status": "completed"}, Exception()], spec=True
        )
        client.download_target_file = Mock(
            side_effect=[str(self.po_files[0]), str(self.po_files[1])], spec=True
        )

        sync._import(client, self.logger)
        self.assertEqual(client.get_project.call_count, 2)
        self.assertEqual(client.download_target_file.call_count, 1)

        self.lc_projects[0].refresh_from_db()
        self.assertEqual(
            self.lc_projects[0].internal_status, LanguageCloudProject.STATUS_IMPORTED
        )

        self.lc_projects[1].refresh_from_db()
        self.assertEqual(
            self.lc_projects[1].internal_status, LanguageCloudProject.STATUS_NEW
        )


class TestExport(TestCase):
    def setUp(self):
        self.locale_en = Locale.objects.get(language_code="en")
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.locale_de = Locale.objects.create(language_code="de")
        self.translations = []
        self.sources = []
        for i in range(0, 2):
            _, source = create_test_page(
                title=f"Test page {i}",
                slug=f"test-page-{i}",
                test_charfield=f"Some test translatable content {i}",
            )
            self.sources.append(source)
            self.translations.append(
                Translation.objects.create(
                    source=source,
                    target_locale=self.locale_fr,
                )
            )
            self.translations.append(
                Translation.objects.create(
                    source=source,
                    target_locale=self.locale_de,
                )
            )
        self.logger = logging.getLogger(__name__)
        logging.disable()  # supress log output under test

    def test_export_all_api_calls_succeed(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(
            side_effect=[{"id": "proj1"}, {"id": "proj2"}], spec=True
        )
        client.create_source_file = Mock(
            side_effect=[
                {"id": "file1"},
                {"id": "file2"},
                {"id": "file3"},
                {"id": "file4"},
            ],
            spec=True,
        )
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 2)
        self.assertEqual(client.create_source_file.call_count, 4)
        lc_projects = [
            LanguageCloudProject.objects.all().get(
                translation_source=s,
                source_last_updated_at=s.last_updated_at,
            )
            for s in self.sources
        ]

        self.assertEqual(lc_projects[0].lc_project_id, "proj1")
        self.assertEqual(lc_projects[0].create_attempts, 1)
        proj1_files = (
            lc_projects[0].languagecloudfile_set.all().order_by("lc_source_file_id")
        )
        self.assertEqual(proj1_files[0].lc_source_file_id, "file1")
        self.assertEqual(proj1_files[0].create_attempts, 1)
        self.assertEqual(proj1_files[1].lc_source_file_id, "file2")
        self.assertEqual(proj1_files[1].create_attempts, 1)

        self.assertEqual(lc_projects[1].lc_project_id, "proj2")
        self.assertEqual(lc_projects[1].create_attempts, 1)
        proj2_files = (
            lc_projects[1].languagecloudfile_set.all().order_by("lc_source_file_id")
        )
        self.assertEqual(proj2_files[0].lc_source_file_id, "file3")
        self.assertEqual(proj2_files[0].create_attempts, 1)
        self.assertEqual(proj2_files[1].lc_source_file_id, "file4")
        self.assertEqual(proj2_files[1].create_attempts, 1)

    def test_export_all_create_project_api_calls_fail(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(side_effect=RequestException("oh no"), spec=True)
        client.create_source_file = Mock(
            side_effect=ValueError("this should never be called"), spec=True
        )
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 4)
        self.assertEqual(client.create_source_file.call_count, 0)

        lc_projects = LanguageCloudProject.objects.all()
        self.assertEqual(len(lc_projects), 2)
        for proj in lc_projects:
            self.assertEqual(proj.lc_project_id, "")
            self.assertEqual(proj.create_attempts, 2)

        lc_files = LanguageCloudFile.objects.all()
        self.assertEqual(len(lc_files), 4)
        for file_ in lc_files:
            self.assertEqual(file_.lc_source_file_id, "")
            self.assertEqual(file_.create_attempts, 0)

    def test_export_some_create_project_api_calls_fail(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(
            side_effect=[
                RequestException("oh no"),
                RequestException("oh no"),
                {"id": "proj2"},
            ],
            spec=True,
        )
        client.create_source_file = Mock(
            side_effect=[{"id": "file3"}, {"id": "file4"}], spec=True
        )
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 3)
        self.assertEqual(client.create_source_file.call_count, 2)
        lc_projects = [
            LanguageCloudProject.objects.all().get(
                translation_source=s,
                source_last_updated_at=s.last_updated_at,
            )
            for s in self.sources
        ]

        self.assertEqual(lc_projects[0].lc_project_id, "")
        self.assertEqual(lc_projects[0].create_attempts, 2)
        proj1_files = (
            lc_projects[0].languagecloudfile_set.all().order_by("lc_source_file_id")
        )
        self.assertEqual(proj1_files[0].lc_source_file_id, "")
        self.assertEqual(proj1_files[0].create_attempts, 0)
        self.assertEqual(proj1_files[1].lc_source_file_id, "")
        self.assertEqual(proj1_files[1].create_attempts, 0)

        self.assertEqual(lc_projects[1].lc_project_id, "proj2")
        self.assertEqual(lc_projects[1].create_attempts, 1)
        proj2_files = (
            lc_projects[1].languagecloudfile_set.all().order_by("lc_source_file_id")
        )
        self.assertEqual(proj2_files[0].lc_source_file_id, "file3")
        self.assertEqual(proj2_files[0].create_attempts, 1)
        self.assertEqual(proj2_files[1].lc_source_file_id, "file4")
        self.assertEqual(proj2_files[1].create_attempts, 1)

    def test_export_some_create_file_api_calls_fail(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(
            side_effect=[{"id": "proj1"}, {"id": "proj2"}], spec=True
        )
        client.create_source_file = Mock(
            side_effect=[
                RequestException("oh no"),
                {"id": "file2"},
                {"id": "file3"},
                RequestException("oh no"),
            ],
            spec=True,
        )
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 2)
        self.assertEqual(client.create_source_file.call_count, 4)
        lc_projects = [
            LanguageCloudProject.objects.all().get(
                translation_source=s,
                source_last_updated_at=s.last_updated_at,
            )
            for s in self.sources
        ]

        self.assertEqual(lc_projects[0].lc_project_id, "proj1")
        self.assertEqual(lc_projects[0].create_attempts, 1)
        proj1_files = (
            lc_projects[0].languagecloudfile_set.all().order_by("lc_source_file_id")
        )
        self.assertEqual(proj1_files[0].lc_source_file_id, "")
        self.assertEqual(proj1_files[0].create_attempts, 1)
        self.assertEqual(proj1_files[1].lc_source_file_id, "file2")
        self.assertEqual(proj1_files[1].create_attempts, 1)

        self.assertEqual(lc_projects[1].lc_project_id, "proj2")
        self.assertEqual(lc_projects[1].create_attempts, 1)
        proj2_files = (
            lc_projects[1].languagecloudfile_set.all().order_by("lc_source_file_id")
        )
        self.assertEqual(proj2_files[0].lc_source_file_id, "")
        self.assertEqual(proj2_files[0].create_attempts, 1)
        self.assertEqual(proj2_files[1].lc_source_file_id, "file3")
        self.assertEqual(proj2_files[1].create_attempts, 1)

    def test_export_no_records_to_process(self):
        LanguageCloudProject.objects.create(
            translation_source=self.sources[0],
            source_last_updated_at=self.sources[0].last_updated_at,
            internal_status=LanguageCloudProject.STATUS_IMPORTED,
        )
        LanguageCloudProject.objects.create(
            translation_source=self.sources[1],
            source_last_updated_at=self.sources[1].last_updated_at,
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

    def test_export_with_an_exception_finished_processing(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(
            side_effect=[{"id": "proj1"}, Exception()], spec=True
        )
        client.create_source_file = Mock(
            side_effect=[{"id": "file1"}, {"id": "file2"}, {"id": "file3"}],
            spec=True,
        )
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 3)
        self.assertEqual(client.create_source_file.call_count, 2)

        lc_projects = [
            LanguageCloudProject.objects.all().get(
                translation_source=s,
                source_last_updated_at=s.last_updated_at,
            )
            for s in self.sources
        ]
        self.assertEqual(len(lc_projects), 2)


class TestHelpers(TestCase):
    def setUp(self):
        self.locale_en = Locale.objects.get(language_code="en")
        self.locale_fr = Locale.objects.create(language_code="fr")
        _, source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
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
            sync._get_project_name(self.translation.source, self.locale_en),
            "Test page_2018-02-02",
        )

    @freeze_time("2018-02-02 12:00:01")
    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={"PROJECT_PREFIX": "Website_"},
    )
    def test_get_project_name_with_custom_prefix(self):
        self.assertEqual(
            sync._get_project_name(self.translation.source, self.locale_en),
            "Website_Test page_2018-02-02",
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

    def test_create_remote_project_success(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(return_value={"id": "abc123"}, spec=True)
        id_ = sync._create_remote_project(
            lc_project,
            client,
            "faketitle",
            "2020-01-01T00:00:01.000Z",
            "fakedesc",
        )
        lc_project.refresh_from_db()
        self.assertEqual(id_, "abc123")
        self.assertEqual(lc_project.lc_project_id, "abc123")
        self.assertEqual(lc_project.create_attempts, 1)

    def test_create_remote_project_fail(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(side_effect=RequestException("oh no"), spec=True)
        with self.assertRaises(RequestException):
            sync._create_remote_project(
                lc_project,
                client,
                "faketitle",
                "2020-01-01T00:00:01.000Z",
                "fakedesc",
            )
        lc_project.refresh_from_db()
        self.assertEqual(lc_project.lc_project_id, "")
        self.assertEqual(lc_project.create_attempts, 1)

    def test_create_remote_source_file_success(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        lc_source_file = LanguageCloudFile.objects.create(
            translation=self.translation,
            project=lc_project,
        )
        client = ApiClient()
        client.is_authorized = True
        client.create_source_file = Mock(return_value={"id": "abc123"}, spec=True)
        sync._create_remote_source_file(
            lc_source_file,
            client,
            "fakeproject",
            "fakepo",
            "fakefilename.po",
            "en-US",
            "fr-CA",
        )
        lc_source_file.refresh_from_db()
        self.assertEqual(lc_source_file.lc_source_file_id, "abc123")
        self.assertEqual(lc_source_file.create_attempts, 1)

    def test_create_remote_source_file_fail(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        lc_source_file = LanguageCloudFile.objects.create(
            translation=self.translation,
            project=lc_project,
        )
        client = ApiClient()
        client.is_authorized = True
        client.create_source_file = Mock(
            side_effect=RequestException("oh no"), spec=True
        )
        with self.assertRaises(RequestException):
            sync._create_remote_source_file(
                lc_source_file,
                client,
                "fakeproject",
                "fakepo",
                "fakefilename.po",
                "en-US",
                "fr-CA",
            )
        lc_source_file.refresh_from_db()
        self.assertEqual(lc_source_file.lc_source_file_id, "")
        self.assertEqual(lc_source_file.create_attempts, 1)

    def test_should_export_already_imported(self):
        self.assertFalse(
            sync._should_export(
                self.logger,
                LanguageCloudProject(
                    translation_source=self.translation.source,
                    source_last_updated_at=self.translation.source.last_updated_at,
                    internal_status=LanguageCloudProject.STATUS_IMPORTED,
                ),
            )
        )

    def test_should_export_project_and_source_file_created(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
            lc_project_id="abc123",
        )
        LanguageCloudFile.objects.create(
            translation=self.translation,
            project=lc_project,
            lc_source_file_id="def456",
        )
        self.assertFalse(sync._should_export(self.logger, lc_project))

    def test_should_export_too_many_project_fails(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
            create_attempts=3,
        )
        LanguageCloudFile.objects.create(
            translation=self.translation,
            project=lc_project,
            create_attempts=0,
        )
        self.assertFalse(sync._should_export(self.logger, lc_project))

    def test_should_export_too_many_file_fails(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
            create_attempts=0,
        )
        LanguageCloudFile.objects.create(
            translation=self.translation,
            project=lc_project,
            create_attempts=3,
        )
        self.assertFalse(sync._should_export(self.logger, lc_project))

    def test_should_export_new_project(self):
        self.assertTrue(
            sync._should_export(
                self.logger,
                LanguageCloudProject(
                    translation_source=self.translation.source,
                    source_last_updated_at=self.translation.source.last_updated_at,
                ),
            )
        )

    def test_should_export_fails_under_threshold(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
            create_attempts=2,
        )
        LanguageCloudFile.objects.create(
            translation=self.translation,
            project=lc_project,
            create_attempts=2,
        )
        self.assertTrue(sync._should_export(self.logger, lc_project))
