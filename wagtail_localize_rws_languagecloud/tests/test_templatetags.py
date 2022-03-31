from datetime import date

from django.test import TestCase
from wagtail.core.models import Locale

from wagtail_localize.models import Translation

from ..models import LanguageCloudFile, LanguageCloudProject
from ..templatetags.wagtaillocalizerwslanguagecloud_tags import translation_statuses
from .helpers import create_test_page


class TestLanguageCloudStatusesTags(TestCase):
    def setUp(self):
        self.locale_en = Locale.objects.get(language_code="en")
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.locale_de = Locale.objects.create(language_code="de")

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
        de_translation = Translation.objects.create(
            source=source,
            target_locale=self.locale_de,
        )
        de_translation.save_target(publish=True)

        self.projects = []
        self.fr_lc_files = []
        self.de_lc_files = []

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

            de_lc_file = LanguageCloudFile.objects.create(
                translation=de_translation,
                project=project,
                lc_source_file_id="file_de",
                internal_status=LanguageCloudFile.STATUS_NEW,
            )

            self.de_lc_files.append(de_lc_file)

        latest_fr_lc_file = self.fr_lc_files[-1]
        latest_fr_lc_file.internal_status = "???"
        latest_fr_lc_file.save()

        latest_de_lc_file = self.de_lc_files[-1]
        latest_de_lc_file.internal_status = LanguageCloudFile.STATUS_ERROR
        latest_de_lc_file.save()

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
        # 1 + (1 [en]) + (1 + 1 [fr]) (1 + 1 [de]) = 6 queries
        with self.assertNumQueries(6):
            context = {"page": page}
            statuses = translation_statuses(context)

        self.assertEqual(2, len(statuses))
        self.assertIn(
            (self.locale_fr.id, "Translations happening in LanguageCloud"), statuses
        )
        self.assertIn((self.locale_de.id, "Error importing PO file"), statuses)
