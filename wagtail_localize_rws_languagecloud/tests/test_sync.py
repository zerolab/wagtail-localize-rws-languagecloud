import logging

from unittest.mock import Mock

from django.test import TestCase, override_settings
from requests.exceptions import RequestException
from wagtail.core.models import Locale

import wagtail_localize_rws_languagecloud.sync as sync

from wagtail_localize.models import Translation

from ..models import LanguageCloudFile, LanguageCloudProject
from ..rws_client import ApiClient
from .helpers import create_test_page, create_test_po, create_test_project_settings


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
            self.assertEqual(file_.combined_status, "Translations ready for review")

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
            self.assertEqual(
                file_.combined_status, "Translations happening in LanguageCloud"
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
        for proj in self.lc_projects:
            proj.refresh_from_db()
        for file_ in self.lc_files:
            file_.refresh_from_db()

        self.assertEqual(
            self.lc_projects[0].internal_status, LanguageCloudProject.STATUS_NEW
        )
        self.assertEqual(self.lc_files[0].internal_status, LanguageCloudFile.STATUS_NEW)
        self.assertEqual(
            self.lc_files[0].combined_status, "Translations happening in LanguageCloud"
        )

        self.assertEqual(
            self.lc_projects[1].internal_status, LanguageCloudProject.STATUS_IMPORTED
        )
        self.assertEqual(
            self.lc_files[1].internal_status, LanguageCloudFile.STATUS_IMPORTED
        )
        self.assertEqual(
            self.lc_files[1].combined_status, "Translations ready for review"
        )

    def test_import_no_records_to_process(self):
        self.lc_projects[0].internal_status = LanguageCloudProject.STATUS_IMPORTED
        self.lc_projects[0].save()
        self.lc_projects[1].lc_project_status = "archived"
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

        for file_ in self.lc_files:
            file_.refresh_from_db()
        self.assertEqual(
            self.lc_files[0].combined_status, "Translations ready for review"
        )
        self.assertEqual(
            self.lc_files[1].combined_status, "Translations happening in LanguageCloud"
        )


@override_settings(WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={"LOCATION_ID": 123})
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
            fr_translation = Translation.objects.create(
                source=source,
                target_locale=self.locale_fr,
            )
            self.translations.append(fr_translation)
            de_translation = Translation.objects.create(
                source=source,
                target_locale=self.locale_de,
            )
            self.translations.append(de_translation)
            create_test_project_settings(source, [fr_translation, de_translation])

        self.get_project_templates_mock = Mock(
            side_effect=[
                {
                    "items": [
                        {
                            "id": "123456",
                            "name": "Project X",
                            "location": {"id": "1337", "name": "Project Folder"},
                        }
                    ],
                    "itemCount": 1,
                }
            ],
            spec=True,
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
        client.get_project_templates = self.get_project_templates_mock
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
        self.assertEqual(
            proj1_files[0].combined_status, "Translations happening in LanguageCloud"
        )
        self.assertEqual(proj1_files[1].lc_source_file_id, "file2")
        self.assertEqual(proj1_files[1].create_attempts, 1)
        self.assertEqual(
            proj1_files[1].combined_status, "Translations happening in LanguageCloud"
        )

        self.assertEqual(lc_projects[1].lc_project_id, "proj2")
        self.assertEqual(lc_projects[1].create_attempts, 1)
        proj2_files = (
            lc_projects[1].languagecloudfile_set.all().order_by("lc_source_file_id")
        )
        self.assertEqual(proj2_files[0].lc_source_file_id, "file3")
        self.assertEqual(proj2_files[0].create_attempts, 1)
        self.assertEqual(
            proj2_files[0].combined_status, "Translations happening in LanguageCloud"
        )
        self.assertEqual(proj2_files[1].lc_source_file_id, "file4")
        self.assertEqual(proj2_files[1].create_attempts, 1)
        self.assertEqual(
            proj2_files[1].combined_status, "Translations happening in LanguageCloud"
        )

    def test_export_all_create_project_api_calls_fail(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(side_effect=RequestException("oh no"), spec=True)
        client.create_source_file = Mock(
            side_effect=ValueError("this should never be called"), spec=True
        )
        client.get_project_templates = self.get_project_templates_mock
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
            self.assertEqual(file_.combined_status, "Request created")

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
        client.get_project_templates = self.get_project_templates_mock

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
        self.assertEqual(proj1_files[0].combined_status, "Request created")
        self.assertEqual(proj1_files[1].lc_source_file_id, "")
        self.assertEqual(proj1_files[1].create_attempts, 0)
        self.assertEqual(proj1_files[1].combined_status, "Request created")

        self.assertEqual(lc_projects[1].lc_project_id, "proj2")
        self.assertEqual(lc_projects[1].create_attempts, 1)
        proj2_files = (
            lc_projects[1].languagecloudfile_set.all().order_by("lc_source_file_id")
        )
        self.assertEqual(proj2_files[0].lc_source_file_id, "file3")
        self.assertEqual(proj2_files[0].create_attempts, 1)
        self.assertEqual(
            proj2_files[0].combined_status, "Translations happening in LanguageCloud"
        )
        self.assertEqual(proj2_files[1].lc_source_file_id, "file4")
        self.assertEqual(proj2_files[1].create_attempts, 1)
        self.assertEqual(
            proj2_files[1].combined_status, "Translations happening in LanguageCloud"
        )

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
        client.get_project_templates = self.get_project_templates_mock
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
        self.assertEqual(proj1_files[0].combined_status, "Request created")
        self.assertEqual(proj1_files[1].lc_source_file_id, "file2")
        self.assertEqual(proj1_files[1].create_attempts, 1)
        self.assertEqual(proj1_files[1].combined_status, "Request created")

        self.assertEqual(lc_projects[1].lc_project_id, "proj2")
        self.assertEqual(lc_projects[1].create_attempts, 1)
        proj2_files = (
            lc_projects[1].languagecloudfile_set.all().order_by("lc_source_file_id")
        )
        self.assertEqual(proj2_files[0].lc_source_file_id, "")
        self.assertEqual(proj2_files[0].create_attempts, 1)
        self.assertEqual(proj2_files[0].combined_status, "Request created")
        self.assertEqual(proj2_files[1].lc_source_file_id, "file3")
        self.assertEqual(proj2_files[1].create_attempts, 1)
        self.assertEqual(proj2_files[1].combined_status, "Request created")

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
        client.get_project_templates = self.get_project_templates_mock
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
        client.get_project_templates = self.get_project_templates_mock
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

    def test_export_will_create_projects_if_they_have_settings(self):
        _, source = create_test_page(
            title="Test page N",
            slug="test-page-n",
            test_charfield="Some test translatable content",
        )
        Translation.objects.create(
            source=source,
            target_locale=self.locale_fr,
        )

        # create a translation that is not included in any project settings
        Translation.objects.create(
            source=self.sources[0],
            target_locale=Locale.objects.create(language_code="ru"),
        )

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
        client.get_project_templates = self.get_project_templates_mock
        sync._export(client, self.logger)

        self.assertEqual(LanguageCloudProject.objects.count(), 2)
        self.assertEqual(client.create_project.call_count, 2)
        self.assertEqual(client.create_source_file.call_count, 4)


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

    def _create_project_settings(self, lc_project):
        lc_project.save()
        settings, _ = create_test_project_settings(
            translation_source=self.translation.source,
            translations=[self.translation],
            lc_project=lc_project,
        )
        return settings

    @override_settings(WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={"LOCATION_ID": 123})
    def test_create_remote_project_success(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        self._create_project_settings(lc_project)

        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(return_value={"id": "abc123"}, spec=True)
        id_ = sync._create_remote_project(
            lc_project, {"project_template_id": "project_location_id"}, client
        )
        lc_project.refresh_from_db()
        self.assertEqual(id_, "abc123")
        self.assertEqual(lc_project.lc_project_id, "abc123")
        self.assertEqual(lc_project.create_attempts, 1)

    @override_settings(WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={"LOCATION_ID": 123})
    def test_create_remote_project_fail(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        self._create_project_settings(lc_project)

        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(side_effect=RequestException("oh no"), spec=True)
        with self.assertRaises(RequestException):
            sync._create_remote_project(
                lc_project,
                {"project_template_id": "project_location_id"},
                client,
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

    def test_should_not_export_already_imported(self):
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
        self._create_project_settings(lc_project)
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
        self._create_project_settings(lc_project)
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
        self._create_project_settings(lc_project)
        LanguageCloudFile.objects.create(
            translation=self.translation,
            project=lc_project,
            create_attempts=3,
        )
        self.assertFalse(sync._should_export(self.logger, lc_project))

    def test_should_export_new_project(self):
        lc_project = LanguageCloudProject(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
        )
        self._create_project_settings(lc_project)
        self.assertTrue(sync._should_export(self.logger, lc_project))

    def test_should_export_fails_under_threshold(self):
        lc_project = LanguageCloudProject.objects.create(
            translation_source=self.translation.source,
            source_last_updated_at=self.translation.source.last_updated_at,
            create_attempts=2,
        )
        self._create_project_settings(lc_project)
        LanguageCloudFile.objects.create(
            translation=self.translation,
            project=lc_project,
            create_attempts=2,
        )
        self.assertTrue(sync._should_export(self.logger, lc_project))
