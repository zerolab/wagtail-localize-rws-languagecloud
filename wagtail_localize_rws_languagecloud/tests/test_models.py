import datetime
import logging

from django.test import TestCase
from wagtail.core.models import Locale

from wagtail_localize.models import Translation

from ..importer import Importer
from ..models import (
    LanguageCloudFile,
    LanguageCloudProject,
    LanguageCloudProjectSettings,
    LanguageCloudStatus,
)
from .helpers import create_test_page, create_test_po


class TestLanguageCloudFileCombinedStatus(TestCase):
    def setUp(self):
        self.locale_fr = Locale.objects.create(language_code="fr")
        _, source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

        self.translation = Translation.objects.create(
            source=source, target_locale=self.locale_fr
        )
        self.translation.save_target()
        self.po_file = create_test_po(
            [
                (
                    "test_charfield",
                    "Some test translatable content",
                    "Certains tests de contenu traduisible",
                )
            ]
        )

        self.project = LanguageCloudProject.objects.create(
            translation_source=source,
            source_last_updated_at=source.last_updated_at,
            internal_status=LanguageCloudProject.STATUS_NEW,
        )
        self.file = LanguageCloudFile.objects.create(
            translation=self.translation,
            project=self.project,
            internal_status=LanguageCloudFile.STATUS_NEW,
        )

    def test_request_created(self):
        self.assertEqual(self.file.combined_status, "Request created")

    def test_disabled(self):
        self.translation.enabled = False
        self.translation.save()
        self.assertEqual(self.file.combined_status, "Translations disabled in Wagtail")

    def test_project_archived(self):
        self.project.lc_project_id = "12345"
        self.file.lc_source_file_id = "67890"
        self.project.lc_project_status = LanguageCloudStatus.ARCHIVED
        self.project.save()
        self.file.save()
        self.assertEqual(self.file.combined_status, "LanguageCloud project archived")

    def test_translations_ready(self):
        self.project.lc_project_id = "12345"
        self.file.lc_source_file_id = "67890"
        self.file.internal_status = LanguageCloudFile.STATUS_IMPORTED
        importer = Importer(self.file, logging.getLogger("dummy"))
        importer.import_po(self.translation, str(self.po_file))
        self.project.save()
        self.file.save()
        self.assertEqual(self.file.combined_status, "Translations ready for review")

    def test_translations_published(self):
        self.project.lc_project_id = "12345"
        self.file.lc_source_file_id = "67890"
        self.file.internal_status = LanguageCloudFile.STATUS_IMPORTED
        importer = Importer(self.file, logging.getLogger("dummy"))
        importer.import_po(self.translation, str(self.po_file))
        instance = self.translation.source.get_translated_instance(
            self.translation.target_locale
        )
        instance.get_latest_revision().publish()
        self.project.save()
        self.file.save()
        self.translation.save()
        self.assertEqual(self.file.combined_status, "Translations published")

    def test_project_create_failed(self):
        self.project.create_attempts = 3
        self.project.save()
        self.file.save()
        self.assertEqual(self.file.combined_status, "Project creation failed")

    def test_po_upload_failed(self):
        self.project.lc_project_id = "12345"
        self.file.create_attempts = 3
        self.project.save()
        self.file.save()
        self.assertEqual(self.file.combined_status, "PO File upload failed")

    def test_po_import_failed(self):
        self.project.lc_project_id = "12345"
        self.file.lc_source_file_id = "67890"
        self.file.internal_status = LanguageCloudFile.STATUS_ERROR
        self.project.save()
        self.file.save()
        self.assertEqual(self.file.combined_status, "Error importing PO file")

    def test_translations_in_progress(self):
        self.project.lc_project_id = "12345"
        self.file.lc_source_file_id = "67890"
        self.project.save()
        self.file.save()
        self.assertEqual(
            self.file.combined_status, "Translations happening in LanguageCloud"
        )


class TestLanguageCloudProjectSettings(TestCase):
    def setUp(self):
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.page, self.source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

        self.translation = Translation.objects.create(
            source=self.source, target_locale=self.locale_fr
        )
        self.translation.save_target()

    def test_settings_creation_includes_source_title(self):
        settings_data = {"name": "the prefix", "due_date": datetime.datetime.now()}
        (
            settings,
            _,
        ) = LanguageCloudProjectSettings.get_or_create_from_source_and_translation_data(
            self.source, [self.translation], **settings_data
        )

        self.assertEqual(settings.name, f"the prefix_{str(self.page)}")

    def test_settings_creation_doesnt_add_double_underscore_if_prefix_ends_with_it(
        self,
    ):
        settings_data = {"name": "prefix_", "due_date": datetime.datetime.now()}
        (
            settings,
            _,
        ) = LanguageCloudProjectSettings.get_or_create_from_source_and_translation_data(
            self.source, [self.translation], **settings_data
        )

        self.assertEqual(settings.name, f"prefix_{str(self.page)}")

    def test_language_code_properties(self):
        settings_data = {"name": "the prefix", "due_date": datetime.datetime.now()}
        (
            settings,
            _,
        ) = LanguageCloudProjectSettings.get_or_create_from_source_and_translation_data(
            self.source, [self.translation], **settings_data
        )
        self.assertEqual(settings.source_language_code, "en")
        self.assertListEqual(settings.target_language_codes, ["fr"])


class TestLanguageCloudProject(TestCase):
    def test_lc_project_status_label(self):
        _, source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

        statuses = LanguageCloudStatus.choices

        for value, label in statuses:
            with self.subTest(value=value, label=label):
                project = LanguageCloudProject(lc_project_status=value)

                self.assertEqual(label, project.lc_project_status_label)

    def test_lc_project_status_label_unknown_value(self):
        _, source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

        project = LanguageCloudProject(lc_project_status="some-unknown-value")

        self.assertEqual("some-unknown-value", project.lc_project_status_label)
