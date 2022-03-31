from datetime import date

from django.test import TestCase
from django.urls import reverse
from wagtail.core.models import Locale

from wagtail_localize.models import Translation

from ..models import LanguageCloudFile, LanguageCloudProject
from ..templatetags.wagtaillocalizerwslanguagecloud_tags import translation_statuses
from .helpers import create_editor_user, create_snippet, create_test_page


class TestTranslationStatusesTags(TestCase):
    def setUp(self):
        user = create_editor_user()
        self.client.force_login(user)

        self.locale_en = Locale.objects.get(language_code="en")
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.locale_es = Locale.objects.create(language_code="es")

        # First make a page
        self.page, source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

        dates = [
            date(2020, 1, 1),
            date(2020, 1, 2),
            date(2020, 1, 3),
        ]

        # Then translate it into the other languages
        fr_translation = Translation.objects.create(
            source=source,
            target_locale=self.locale_fr,
        )
        fr_translation.save_target(publish=True)
        es_translation = Translation.objects.create(
            source=source,
            target_locale=self.locale_es,
        )
        es_translation.save_target(publish=True)

        self.projects = []
        self.fr_lc_files = []
        self.es_lc_files = []

        # Simulate sending the translation to language cloud multiple times
        for date_ in dates:
            project = LanguageCloudProject.objects.create(
                translation_source=source,
                source_last_updated_at=date_,
                internal_status=LanguageCloudProject.STATUS_NEW,
                lc_project_id=f"proj_{date_}",
            )
            self.projects.append(project)

            fr_lc_file = LanguageCloudFile.objects.create(
                translation=fr_translation,
                project=project,
                lc_source_file_id="file_fr",
                internal_status=LanguageCloudFile.STATUS_NEW,
            )

            self.fr_lc_files.append(fr_lc_file)

            es_lc_file = LanguageCloudFile.objects.create(
                translation=es_translation,
                project=project,
                lc_source_file_id="file_es",
                internal_status=LanguageCloudFile.STATUS_NEW,
            )

            self.es_lc_files.append(es_lc_file)

        latest_fr_lc_file = self.fr_lc_files[-1]
        latest_fr_lc_file.internal_status = "???"
        latest_fr_lc_file.save()

        latest_es_lc_file = self.es_lc_files[-1]
        latest_es_lc_file.internal_status = LanguageCloudFile.STATUS_ERROR
        latest_es_lc_file.save()

    def test_translation_statuses_tag(self):
        page = self.page

        # 6 queries total:
        # 1 to get the used locales for the page
        # AND
        # Then for every locale:
        # 1 for to get the LanguageCloudFile
        # 1 for prefetch IF there is a LanguageCloudFile for that locale
        #
        # In this test there are 3 locales, 2 having LanguageCloudFiles, so
        # that's:
        # 1 + (1 [en]) + (1 + 1 [fr]) (1 + 1 [es]) = 6 queries
        with self.assertNumQueries(6):
            context = {"page": page}
            statuses = translation_statuses(context)

        self.assertEqual(2, len(statuses))
        self.assertIn(
            (self.locale_fr.id, "Translations happening in LanguageCloud"), statuses
        )
        self.assertIn((self.locale_es.id, "Error importing PO file"), statuses)

    def test_page_template_overrides(self):
        expected_text_fr = "French (Translations happening in LanguageCloud)"
        expected_text_es = "Spanish (Error importing PO file)"

        urls = [
            reverse("wagtailadmin_explore", args=[self.page.id]),
            reverse("wagtailadmin_pages:edit", args=[self.page.id]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, expected_text_fr, html=True)
                self.assertContains(response, expected_text_es, html=True)

    def test_snippet_template_overrides(self):
        # Create the snippet
        snippet, source = create_snippet()

        # Create the translations
        fr_translation = Translation.objects.create(
            source=source,
            target_locale=self.locale_fr,
        )
        fr_translation.save_target(publish=True)
        es_translation = Translation.objects.create(
            source=source,
            target_locale=self.locale_es,
        )
        es_translation.save_target(publish=True)

        # Simulate sending the translation to language cloud
        project = LanguageCloudProject.objects.create(
            translation_source=source,
            source_last_updated_at=date(2020, 1, 1),
            internal_status=LanguageCloudProject.STATUS_NEW,
            lc_project_id="proj",
        )

        LanguageCloudFile.objects.create(
            translation=fr_translation,
            project=project,
            lc_source_file_id="file_fr",
            internal_status=LanguageCloudFile.STATUS_NEW,
        )

        LanguageCloudFile.objects.create(
            translation=es_translation,
            project=project,
            lc_source_file_id="file_es",
            internal_status=LanguageCloudFile.STATUS_ERROR,
        )

        # Check that the status appears in the edit snippet view
        expected_text_fr = "French (Translations happening in LanguageCloud)"
        expected_text_es = "Spanish (Error importing PO file)"

        url = reverse(
            "wagtailsnippets:edit",
            args=[snippet._meta.app_label, snippet._meta.model_name, snippet.id],
        )

        response = self.client.get(url)
        self.assertContains(response, expected_text_fr, html=True)
        self.assertContains(response, expected_text_es, html=True)
