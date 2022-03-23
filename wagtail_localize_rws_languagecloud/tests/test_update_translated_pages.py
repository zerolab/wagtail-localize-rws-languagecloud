from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from wagtail.core.models import Locale

from wagtail_localize.models import Translation

from ..models import LanguageCloudProject
from .helpers import create_editor_user, create_test_page


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
        fr_translation = Translation.objects.create(
            source=self.source,
            target_locale=self.locale_fr,
        )
        fr_translation.save_target(publish=True)
        de_translation = Translation.objects.create(
            source=self.source,
            target_locale=self.locale_de,
        )
        de_translation.save_target(publish=True)

    def test_should_create_language_cloud_project(self):
        call_command("update_translated_pages")
        lc_project = LanguageCloudProject.objects.get(source=self.source)

        self.assertTrue(lc_project)

    def test_should_skip_creating_language_cloud_project(self):
        self.fail()

    def test_only_set_locales_are_translated(self):
        self.fail()
