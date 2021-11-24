import logging

from django.test import TestCase
from wagtail.core.models import Locale

from wagtail_localize.models import Translation

from ..importer import Importer
from ..models import LanguageCloudFile, LanguageCloudProject
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
        self.assertEqual(
            self.file.combined_status, LanguageCloudFile.COMBINED_STATUS_NEW
        )

    def test_disabled(self):
        self.translation.enabled = False
        self.translation.save()
        self.file.save()
        self.project.save()
        self.file.refresh_from_db()
        self.assertEqual(
            self.file.combined_status,
            LanguageCloudFile.COMBINED_STATUS_TRANSLATIONS_DISABLED,
        )

    def test_project_archived(self):
        self.project.lc_project_id = "12345"
        self.file.lc_source_file_id = "67890"
        self.project.lc_project_status = "archived"
        self.file.save()
        self.project.save()
        self.file.refresh_from_db()
        self.assertEqual(
            self.file.combined_status,
            LanguageCloudFile.COMBINED_STATUS_PROJECT_ARCHIVED,
        )

    def test_translations_ready(self):
        self.project.lc_project_id = "12345"
        self.file.lc_source_file_id = "67890"
        self.file.internal_status = LanguageCloudFile.STATUS_IMPORTED
        importer = Importer(self.file, logging.getLogger("dummy"))
        importer.import_po(self.translation, str(self.po_file))
        self.file.save()
        self.project.save()
        self.file.refresh_from_db()
        self.assertEqual(
            self.file.combined_status,
            LanguageCloudFile.COMBINED_STATUS_TRANSLATIONS_READY,
        )

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
        self.translation.save()
        self.file.save()
        self.project.save()
        self.file.refresh_from_db()
        self.assertEqual(
            self.file.combined_status,
            LanguageCloudFile.COMBINED_STATUS_TRANSLATIONS_PUBLISHED,
        )

    def test_project_create_failed(self):
        self.project.create_attempts = 3
        self.file.save()
        self.project.save()
        self.file.refresh_from_db()
        self.assertEqual(
            self.file.combined_status, LanguageCloudFile.COMBINED_STATUS_PROJECT_FAILED
        )

    def test_po_upload_failed(self):
        self.project.lc_project_id = "12345"
        self.file.create_attempts = 3
        self.file.save()
        self.project.save()
        self.file.refresh_from_db()
        self.assertEqual(
            self.file.combined_status,
            LanguageCloudFile.COMBINED_STATUS_PO_EXPORT_FAILED,
        )

    def test_po_import_failed(self):
        self.project.lc_project_id = "12345"
        self.file.lc_source_file_id = "67890"
        self.file.internal_status = LanguageCloudFile.STATUS_ERROR
        self.file.save()
        self.project.save()
        self.file.refresh_from_db()
        self.assertEqual(
            self.file.combined_status,
            LanguageCloudFile.COMBINED_STATUS_PO_IMPORT_FAILED,
        )

    def test_translations_in_progress(self):
        self.project.lc_project_id = "12345"
        self.file.lc_source_file_id = "67890"
        self.file.save()
        self.project.save()
        self.file.refresh_from_db()
        self.assertEqual(
            self.file.combined_status,
            LanguageCloudFile.COMBINED_STATUS_PROJECT_IN_PROGRESS,
        )
