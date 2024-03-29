from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone


try:
    from wagtail.models import Locale
except ImportError:
    from wagtail.core.models import Locale

from wagtail_localize.models import Translation

from ..models import LanguageCloudFile, LanguageCloudProject, LanguageCloudStatus
from .helpers import create_editor_user, create_test_page


@override_settings(
    WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
        "CLIENT_ID": "fakeid",
        "CLIENT_SECRET": "fakesecret",
        "ACCOUNT_ID": "fakeaccount",
    },
)
class TestUpdateTranslationsOverride(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.locale_en = Locale.objects.get(language_code="en")
        cls.locale_fr = Locale.objects.create(language_code="fr")
        cls.locale_de = Locale.objects.create(language_code="de")
        cls.user = create_editor_user()

        # First make a page
        cls.page, cls.source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

        # Then translate it into the other languages
        fr_translation = Translation.objects.create(
            source=cls.source,
            target_locale=cls.locale_fr,
        )
        fr_translation.save_target(publish=True)
        de_translation = Translation.objects.create(
            source=cls.source,
            target_locale=cls.locale_de,
        )
        de_translation.save_target(publish=True)

        # Simulate sending the translation to language cloud
        cls.project = LanguageCloudProject.objects.create(
            translation_source=cls.source,
            source_last_updated_at=timezone.now(),
            internal_status=LanguageCloudProject.STATUS_NEW,
            lc_project_id="proj",
        )

        LanguageCloudFile.objects.create(
            translation=fr_translation,
            project=cls.project,
            lc_source_file_id="file_fr",
            internal_status=LanguageCloudFile.STATUS_NEW,
        )

        LanguageCloudFile.objects.create(
            translation=de_translation,
            project=cls.project,
            lc_source_file_id="file_de",
            internal_status=LanguageCloudFile.STATUS_NEW,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_should_show_unable_to_update_translations_message(self):
        statuses = [
            LanguageCloudStatus.CREATED,
            LanguageCloudStatus.IN_PROGRESS,
            "some-unknown-status",
        ]

        for status in statuses:
            with self.subTest(lc_project_status=status):
                self.project.lc_project_status = status
                self.project.save()

                response = self.client.get(
                    reverse(
                        "wagtail_localize:update_translations", args=[self.source.pk]
                    )
                )

                # Response should be overridden by us
                self.assertEqual(200, response.status_code)
                self.assertTemplateUsed(
                    response,
                    "wagtail_localize_rws_languagecloud/admin/update_translations_override.html",
                )

    def test_should_allow_update_translations(self):
        statuses = [
            LanguageCloudStatus.COMPLETED,
            LanguageCloudStatus.ARCHIVED,
        ]

        for status in statuses:
            with self.subTest(lc_project_status=status):
                self.project.lc_project_status = status
                self.project.save()

                response = self.client.get(
                    reverse(
                        "wagtail_localize:update_translations", args=[self.source.pk]
                    )
                )

                # Check that the page is served by wagtail-localize
                self.assertEqual(200, response.status_code)
                self.assertTemplateUsed(
                    response, "wagtail_localize/admin/update_translations.html"
                )
