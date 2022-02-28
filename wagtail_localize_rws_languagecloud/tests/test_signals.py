import logging

from unittest.mock import MagicMock, Mock

from django.test import TestCase
from wagtail.core.models import Locale

import wagtail_localize_rws_languagecloud.sync as sync

from wagtail_localize.models import Translation

from ..models import LanguageCloudFile, LanguageCloudProject, LanguageCloudStatus
from ..rws_client import ApiClient
from ..signals import translation_imported
from .helpers import create_test_page, create_test_po


class TestSignals(TestCase):
    def setUp(self):
        self.po_file = create_test_po(
            [
                (
                    "test_charfield",
                    "Some test translatable content",
                    "Certains tests de contenu traduisible",
                )
            ]
        )
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.page, source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )
        translation = Translation.objects.create(
            source=source,
            target_locale=self.locale_fr,
        )
        self.project = LanguageCloudProject.objects.create(
            translation_source=source,
            source_last_updated_at=source.last_updated_at,
            internal_status=LanguageCloudProject.STATUS_NEW,
            lc_project_id="proj",
        )
        LanguageCloudFile.objects.create(
            translation=translation,
            project=self.project,
            lc_source_file_id="file",
            internal_status=LanguageCloudFile.STATUS_NEW,
        )

        self.logger = logging.getLogger(__name__)
        logging.disable()  # supress log output under test

    def test_translation_imported_signal(self):
        # Create signal handler
        signal_handler = MagicMock()
        translation_imported.connect(signal_handler)

        # Set up mocks
        client = ApiClient()
        client.is_authorized = True
        client.get_project = Mock(
            side_effect=[{"status": "completed"}, {"status": "inProgress"}], spec=True
        )
        client.download_target_file = Mock(side_effect=[str(self.po_file)], spec=True)
        client.complete_project = Mock(spec=True)

        # Run sync import
        sync._import(client, self.logger)

        # Check sync import worked
        self.project.refresh_from_db()
        self.assertEqual(
            self.project.internal_status, LanguageCloudProject.STATUS_IMPORTED
        )
        self.assertEqual(self.project.lc_project_status, LanguageCloudStatus.COMPLETED)

        # Check signal handler was called
        signal_handler.assert_called_once_with(
            signal=translation_imported,
            sender=LanguageCloudProject,
            instance=self.project,
            source_object=self.page,
            translated_object=self.page.get_translation(self.locale_fr),
        )
