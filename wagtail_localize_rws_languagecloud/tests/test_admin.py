from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls.base import reverse
from wagtail.tests.utils import WagtailTestUtils


try:
    from wagtail.models import Locale
except ImportError:
    from wagtail.core.models import Locale

from wagtail_localize.models import Translation

from .helpers import (
    create_editor_user,
    create_snippet,
    create_test_page,
    get_snippet_edit_url,
)


class TestPageEditTranslateButton(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor_user = create_editor_user()
        cls.locale_fr = Locale.objects.create(language_code="fr")
        cls.locale_de = Locale.objects.create(language_code="de")

        cls.test_page, source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

        cls.test_page_edit_url = reverse(
            "wagtailadmin_pages:edit", args=[cls.test_page.pk]
        )

    def setUp(self):
        self.client.force_login(self.editor_user)

    def test_translate_button_in_action_menu(self):
        resp = self.client.get(self.test_page_edit_url)

        self.assertContains(
            resp,
            f'href="/admin/localize/submit/page/{self.test_page.pk}/"',
        )
        self.assertContains(resp, "Translate this page")

    def test_translate_button_no_permission(self):
        group = Group.objects.get(name="Editors")
        group.permissions.remove(Permission.objects.get(codename="submit_translation"))

        resp = self.client.get(self.test_page_edit_url)

        self.assertNotContains(
            resp, f'href="/admin/localize/submit/page/{self.test_page.pk}/"'
        )
        self.assertNotContains(resp, "Translate this page")

    def test_translate_button_no_available_locales(self):
        self.locale_fr.delete()
        self.locale_de.delete()

        resp = self.client.get(self.test_page_edit_url)

        self.assertNotContains(
            resp, f'href="/admin/localize/submit/page/{self.test_page.pk}/"'
        )
        self.assertNotContains(resp, "Translate this page")


class TestPageEditSyncTranslationsButton(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor_user = create_editor_user()
        cls.locale_fr = Locale.objects.create(language_code="fr")
        cls.locale_de = Locale.objects.create(language_code="de")

        cls.test_page, cls.test_page_source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

        # Create translations for test page
        Translation.objects.create(
            source=cls.test_page_source, target_locale=cls.locale_fr
        )
        Translation.objects.create(
            source=cls.test_page_source, target_locale=cls.locale_de
        )

        cls.test_page_edit_url = reverse(
            "wagtailadmin_pages:edit", args=[cls.test_page.pk]
        )

    def setUp(self):
        self.client.force_login(self.editor_user)

    def test_sync_button_in_action_menu(self):
        resp = self.client.get(self.test_page_edit_url)

        self.assertContains(
            resp,
            f'href="/admin/localize/update/{self.test_page_source.pk}/"',
        )
        self.assertContains(resp, "Sync translated pages")

    def test_sync_button_no_permission(self):
        group = Group.objects.get(name="Editors")
        group.permissions.remove(Permission.objects.get(codename="submit_translation"))

        resp = self.client.get(self.test_page_edit_url)

        self.assertNotContains(
            resp,
            f'href="/admin/localize/update/{self.test_page_source.pk}/"',
        )
        self.assertNotContains(resp, "Sync translated pages")

    def test_sync_button_no_translations(self):
        self.locale_fr.delete()
        self.locale_de.delete()

        resp = self.client.get(self.test_page_edit_url)

        self.assertNotContains(
            resp,
            f'href="/admin/localize/update/{self.test_page_source.pk}/"',
        )
        self.assertNotContains(resp, "Sync translated pages")


class TestSnippetEditTranslateButton(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        group = Group.objects.get(name="Editors")

        # Add snippet permissions
        group.permissions.add(
            *Permission.objects.filter(
                codename__in=[
                    "add_examplesnippet",
                    "change_examplesnippet",
                    "delete_examplesnippet",
                ]
            )
        )

        cls.editor_user = create_editor_user()
        cls.locale_fr = Locale.objects.create(language_code="fr")
        cls.locale_de = Locale.objects.create(language_code="de")

        cls.test_snippet, source = create_snippet()
        cls.test_snippet_edit_url = get_snippet_edit_url(cls.test_snippet)

    def setUp(self):
        self.client.force_login(self.editor_user)

    def test_translate_button_in_action_menu(self):
        resp = self.client.get(self.test_snippet_edit_url)

        self.assertContains(
            resp,
            f'href="/admin/localize/submit/snippet/wagtail_localize_rws_languagecloud_test/examplesnippet/{self.test_snippet.pk}/"',
        )
        self.assertContains(resp, "Translate this snippet")

    def test_translate_button_no_permission(self):
        group = Group.objects.get(name="Editors")
        group.permissions.remove(Permission.objects.get(codename="submit_translation"))

        resp = self.client.get(self.test_snippet_edit_url)

        self.assertNotContains(
            resp,
            f'href="/admin/localize/submit/snippet/wagtail_localize_rws_languagecloud_test/examplesnippet/{self.test_snippet.pk}/"',
        )
        self.assertNotContains(resp, "Translate this snippet")

    def test_translate_button_no_available_locales(self):
        self.locale_fr.delete()
        self.locale_de.delete()

        resp = self.client.get(self.test_snippet_edit_url)

        self.assertNotContains(
            resp,
            f'href="/admin/localize/submit/snippet/wagtail_localize_rws_languagecloud_test/examplesnippet/{self.test_snippet.pk}/"',
        )
        self.assertNotContains(resp, "Translate this snippet")


class TestSnippetEditSyncTranslationsButton(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        group = Group.objects.get(name="Editors")

        # Add snippet permissions
        group.permissions.add(
            *Permission.objects.filter(
                codename__in=[
                    "add_examplesnippet",
                    "change_examplesnippet",
                    "delete_examplesnippet",
                ]
            )
        )

        cls.editor_user = create_editor_user()
        cls.locale_fr = Locale.objects.create(language_code="fr")
        cls.locale_de = Locale.objects.create(language_code="de")

        cls.test_snippet, cls.test_snippet_source = create_snippet()

        # Create translations for test snippet
        Translation.objects.create(
            source=cls.test_snippet_source, target_locale=cls.locale_fr
        )
        Translation.objects.create(
            source=cls.test_snippet_source, target_locale=cls.locale_de
        )

        cls.test_snippet_edit_url = get_snippet_edit_url(cls.test_snippet)

    def setUp(self):
        self.client.force_login(self.editor_user)

    def test_sync_button_in_action_menu(self):
        resp = self.client.get(self.test_snippet_edit_url)

        self.assertContains(
            resp,
            f'href="/admin/localize/update/{self.test_snippet_source.pk}/"',
        )
        self.assertContains(resp, "Sync translated snippets")

    def test_sync_button_no_permission(self):
        group = Group.objects.get(name="Editors")
        group.permissions.remove(Permission.objects.get(codename="submit_translation"))

        resp = self.client.get(self.test_snippet_edit_url)

        self.assertNotContains(
            resp,
            f'href="/admin/localize/update/{self.test_snippet_source.pk}/"',
        )
        self.assertNotContains(resp, "Sync translated snippets")

    def test_sync_button_no_translations(self):
        self.locale_fr.delete()
        self.locale_de.delete()

        resp = self.client.get(self.test_snippet_edit_url)

        self.assertNotContains(
            resp,
            f'href="/admin/localize/update/{self.test_snippet_source.pk}/"',
        )
        self.assertNotContains(resp, "Sync translated snippets")
