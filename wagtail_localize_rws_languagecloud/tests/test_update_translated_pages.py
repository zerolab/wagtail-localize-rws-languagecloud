from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from wagtail.core.models import Locale

from wagtail_localize.models import Translation

from ..models import (
    LanguageCloudProject,
    LanguageCloudProjectSettings,
    LanguageCloudStatus,
)
from .helpers import create_editor_user, create_test_page


@override_settings(
    WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
        "TEMPLATE_ID": "123",
    }
)
class TestUpdateTranslatedPages(TestCase):
    def setUp(self):
        self.locale_en = Locale.objects.get(language_code="en")
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.locale_de = Locale.objects.create(language_code="de")
        self.user = create_editor_user()
        self.client.force_login(self.user)

        # First make a page
        self.page, self.source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )
        self.page.last_published_at = timezone.now()
        self.page.save()

        # Then translate it into the other languages
        self.fr_translation = Translation.objects.create(
            source=self.source,
            target_locale=self.locale_fr,
        )
        self.fr_translation.save_target(publish=True)
        self.de_translation = Translation.objects.create(
            source=self.source,
            target_locale=self.locale_de,
        )
        self.de_translation.save_target(publish=True)

    def test_should_create_language_cloud_project(self):
        call_command("update_translated_pages")

        project_settings = LanguageCloudProjectSettings.objects.get()
        self.assertEqual(project_settings.translation_source, self.source)
        self.assertEqual(
            list(project_settings.translations.all()),
            [self.fr_translation, self.de_translation],
        )

    def test_should_skip_up_to_date_pages(self):
        self.source.last_updated_at = timezone.now()
        self.source.save()

        call_command("update_translated_pages")

        self.assertEqual(0, LanguageCloudProjectSettings.objects.count())

    def test_should_skip_pages_with_ongoing_lc_projects(self):
        LanguageCloudProject.objects.create(
            translation_source=self.source,
            source_last_updated_at=self.source.last_updated_at,
            internal_status=LanguageCloudProject.STATUS_NEW,
            lc_project_status=LanguageCloudStatus.IN_PROGRESS,
            lc_project_id="proj",
        )

        call_command("update_translated_pages")

        self.assertEqual(0, LanguageCloudProjectSettings.objects.count())

    def test_should_skip_pages_with_ongoing_and_completed_lc_projects(self):
        # Old, completed LC project
        LanguageCloudProject.objects.create(
            translation_source=self.source,
            source_last_updated_at=self.source.last_updated_at,
            internal_status=LanguageCloudProject.STATUS_IMPORTED,
            lc_project_status=LanguageCloudStatus.ARCHIVED,
            lc_project_id="proj",
        )

        # New, ongoing LC project
        LanguageCloudProject.objects.create(
            translation_source=self.source,
            source_last_updated_at=self.source.last_updated_at + timedelta(days=1),
            internal_status=LanguageCloudProject.STATUS_NEW,
            lc_project_status=LanguageCloudStatus.IN_PROGRESS,
            lc_project_id="proj",
        )

        call_command("update_translated_pages")

        self.assertEqual(0, LanguageCloudProjectSettings.objects.count())
