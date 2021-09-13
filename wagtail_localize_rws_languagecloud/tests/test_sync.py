import datetime
import logging
from unittest.mock import Mock
from django.test import TestCase, override_settings
from wagtail.core.models import Page, Locale
from wagtail_localize.models import TranslationSource, Translation
from wagtail_localize.test.models import TestPage
from freezegun import freeze_time
from requests.exceptions import RequestException
from ..rws_client import ApiClient, NotAuthenticated
import wagtail_localize_rws_languagecloud.sync as sync


def create_test_page(**kwargs):
    parent = kwargs.pop("parent", None) or Page.objects.get(id=1)
    page = parent.add_child(instance=TestPage(**kwargs))
    revision = page.save_revision()
    revision.publish()
    source, created = TranslationSource.get_or_create_from_instance(page)
    return page, source


class TestExport(TestCase):
    def setUp(self):
        self.locale_en = Locale.objects.get(language_code="en")
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.translations = []
        for i in range(0, 2):
            _, source = create_test_page(
                title=f"Test page {i}",
                slug=f"test-page-{i}",
                test_charfield=f"Some test translatable content {i}",
            )
            self.translations.append(
                Translation.objects.create(
                    source=source,
                    target_locale=self.locale_fr,
                )
            )
        self.logger = logging.getLogger(__name__)
        logging.disable()  # supress log output under test

    def test_exports_all_api_calls_succeed(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(return_value={"id": "abc123"}, spec=True)
        client.create_source_file = Mock(return_value={"id": "abc123"}, spec=True)
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 2)
        self.assertEqual(client.create_source_file.call_count, 2)

    def test_all_create_project_api_calls_fail(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(side_effect=RequestException("oh no"), spec=True)
        client.create_source_file = Mock(
            side_effect=ValueError("this should never be called"), spec=True
        )
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 2)
        self.assertEqual(client.create_source_file.call_count, 0)

    def test_some_create_project_api_calls_fail(self):
        client = ApiClient()
        client.is_authorized = True
        client.create_project = Mock(
            side_effect=[RequestException("oh no"), {"id": "abc123"}], spec=True
        )
        client.create_source_file = Mock(return_value={"id": "abc123"}, spec=True)
        sync._export(client, self.logger)
        self.assertEqual(client.create_project.call_count, 2)
        self.assertEqual(client.create_source_file.call_count, 1)


class TestHelpers(TestCase):
    def setUp(self):
        self.locale_en = Locale.objects.get(language_code="en")
        self.locale_fr = Locale.objects.create(language_code="fr")
        _, source = create_test_page(
            title=f"Test page",
            slug=f"test-page",
            test_charfield=f"Some test translatable content",
        )
        self.translation = Translation.objects.create(
            source=source,
            target_locale=self.locale_fr,
        )

    def test_get_project_name_without_custom_prefix(self):
        self.assertEqual(
            sync._get_project_name(self.translation, self.locale_en), "Test page_fr"
        )

    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={"PROJECT_PREFIX": "Website_"},
    )
    def test_get_project_name_with_custom_prefix(self):
        self.assertEqual(
            sync._get_project_name(self.translation, self.locale_en),
            "Website_Test page_fr",
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
