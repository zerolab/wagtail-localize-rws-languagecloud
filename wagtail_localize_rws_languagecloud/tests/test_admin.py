from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls.base import reverse
from wagtail.core.models import Locale
from wagtail.tests.utils import WagtailTestUtils

from wagtail_localize.models import Translation

from .helpers import create_editor_user, create_snippet, create_test_page


class TestPageEditTranslateButton(TestCase, WagtailTestUtils):
    def setUp(self):
        self.editor_user = create_editor_user()
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.locale_de = Locale.objects.create(language_code="de")
        self.client.force_login(self.editor_user)

        self.test_page, source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

    def test_translate_button_in_action_menu(self):
        resp = self.client.get(
            reverse("wagtailadmin_pages:edit", args=[self.test_page.pk])
        )

        self.assertContains(
            resp,
            f'<a class="button" href="/admin/localize/submit/page/{self.test_page.pk}/"><svg class="icon icon-site icon" aria-hidden="true" focusable="false"><use href="#icon-site"></use></svg>Translate this page</a>',
        )

    def test_translate_button_no_permission(self):
        group = Group.objects.get(name="Editors")
        group.permissions.remove(Permission.objects.get(codename="submit_translation"))

        resp = self.client.get(
            reverse("wagtailadmin_pages:edit", args=[self.test_page.pk])
        )

        self.assertNotContains(
            resp,
            f'<a class="button" href="/admin/localize/submit/page/{self.test_page.pk}/"><svg class="icon icon-site icon" aria-hidden="true" focusable="false"><use href="#icon-site"></use></svg>Translate this page</a>',
        )

    def test_translate_button_no_available_locales(self):
        self.locale_fr.delete()
        self.locale_de.delete()

        resp = self.client.get(
            reverse("wagtailadmin_pages:edit", args=[self.test_page.pk])
        )

        self.assertNotContains(
            resp,
            f'<a class="button" href="/admin/localize/submit/page/{self.test_page.pk}/"><svg class="icon icon-site icon" aria-hidden="true" focusable="false"><use href="#icon-site"></use></svg>Translate this page</a>',
        )


class TestPageEditSyncTranslationsButton(TestCase, WagtailTestUtils):
    def setUp(self):
        self.editor_user = create_editor_user()
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.locale_de = Locale.objects.create(language_code="de")
        self.client.force_login(self.editor_user)

        self.test_page, self.test_page_source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

        # Create translations for test page
        Translation.objects.create(
            source=self.test_page_source, target_locale=self.locale_fr
        )
        Translation.objects.create(
            source=self.test_page_source, target_locale=self.locale_de
        )

    def test_sync_button_in_action_menu(self):
        resp = self.client.get(
            reverse("wagtailadmin_pages:edit", args=[self.test_page.pk])
        )

        self.assertContains(
            resp,
            f'<a class="button" href="/admin/localize/update/{self.test_page_source.pk}/"><svg class="icon icon-repeat icon" aria-hidden="true" focusable="false"><use href="#icon-repeat"></use></svg>Sync translated pages</a>',
        )

    def test_sync_button_no_permission(self):
        group = Group.objects.get(name="Editors")
        group.permissions.remove(Permission.objects.get(codename="submit_translation"))

        resp = self.client.get(
            reverse("wagtailadmin_pages:edit", args=[self.test_page.pk])
        )

        self.assertNotContains(
            resp,
            f'<a class="button" href="/admin/localize/update/{self.test_page_source.pk}/"><svg class="icon icon-repeat icon" aria-hidden="true" focusable="false"><use href="#icon-repeat"></use></svg>Sync translated pages</a>',
        )

    def test_sync_button_no_translations(self):
        self.locale_fr.delete()
        self.locale_de.delete()

        resp = self.client.get(
            reverse("wagtailadmin_pages:edit", args=[self.test_page.pk])
        )

        self.assertNotContains(
            resp,
            f'<a class="button" href="/admin/localize/update/{self.test_page_source.pk}/"><svg class="icon icon-repeat icon" aria-hidden="true" focusable="false"><use href="#icon-repeat"></use></svg>Sync translated pages</a>',
        )


class TestSnippetEditTranslateButton(TestCase, WagtailTestUtils):
    def setUp(self):
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

        self.editor_user = create_editor_user()
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.locale_de = Locale.objects.create(language_code="de")
        self.client.force_login(self.editor_user)

        self.test_snippet, source = create_snippet()

    def test_translate_button_in_action_menu(self):
        resp = self.client.get(
            reverse(
                "wagtailsnippets:edit",
                args=[
                    "wagtail_localize_rws_languagecloud_test",
                    "examplesnippet",
                    self.test_snippet.pk,
                ],
            )
        )

        self.assertContains(
            resp,
            f'<a class="button" href="/admin/localize/submit/snippet/wagtail_localize_rws_languagecloud_test/examplesnippet/{self.test_snippet.pk}/"><svg class="icon icon-site icon" aria-hidden="true" focusable="false"><use href="#icon-site"></use></svg>Translate this snippet</a>',
        )

    def test_translate_button_no_permission(self):
        group = Group.objects.get(name="Editors")
        group.permissions.remove(Permission.objects.get(codename="submit_translation"))

        resp = self.client.get(
            reverse(
                "wagtailsnippets:edit",
                args=[
                    "wagtail_localize_rws_languagecloud_test",
                    "examplesnippet",
                    self.test_snippet.pk,
                ],
            )
        )

        self.assertNotContains(
            resp,
            f'<a class="button" href="/admin/localize/submit/snippet/wagtail_localize_rws_languagecloud_test/examplesnippet/{self.test_snippet.pk}/"><svg class="icon icon-site icon" aria-hidden="true" focusable="false"><use href="#icon-site"></use></svg>Translate this snippet</a>',
        )

    def test_translate_button_no_available_locales(self):
        self.locale_fr.delete()
        self.locale_de.delete()

        resp = self.client.get(
            reverse(
                "wagtailsnippets:edit",
                args=[
                    "wagtail_localize_rws_languagecloud_test",
                    "examplesnippet",
                    self.test_snippet.pk,
                ],
            )
        )

        self.assertNotContains(
            resp,
            f'<a class="button" href="/admin/localize/submit/snippet/wagtail_localize_rws_languagecloud_test/examplesnippet/{self.test_snippet.pk}/"><svg class="icon icon-site icon" aria-hidden="true" focusable="false"><use href="#icon-site"></use></svg>Translate this snippet</a>',
        )


class TestSnippetEditSyncTranslationsButton(TestCase, WagtailTestUtils):
    def setUp(self):
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

        self.editor_user = create_editor_user()
        self.locale_fr = Locale.objects.create(language_code="fr")
        self.locale_de = Locale.objects.create(language_code="de")
        self.client.force_login(self.editor_user)

        self.test_snippet, self.test_snippet_source = create_snippet()

        # Create translations for test snippet
        Translation.objects.create(
            source=self.test_snippet_source, target_locale=self.locale_fr
        )
        Translation.objects.create(
            source=self.test_snippet_source, target_locale=self.locale_de
        )

    def test_sync_button_in_action_menu(self):
        resp = self.client.get(
            reverse(
                "wagtailsnippets:edit",
                args=[
                    "wagtail_localize_rws_languagecloud_test",
                    "examplesnippet",
                    self.test_snippet.pk,
                ],
            )
        )

        self.assertContains(
            resp,
            f'<a class="button" href="/admin/localize/update/{self.test_snippet_source.pk}/"><svg class="icon icon-repeat icon" aria-hidden="true" focusable="false"><use href="#icon-repeat"></use></svg>Sync translated snippets</a>',
        )

    def test_sync_button_no_permission(self):
        group = Group.objects.get(name="Editors")
        group.permissions.remove(Permission.objects.get(codename="submit_translation"))

        resp = self.client.get(
            reverse(
                "wagtailsnippets:edit",
                args=[
                    "wagtail_localize_rws_languagecloud_test",
                    "examplesnippet",
                    self.test_snippet.pk,
                ],
            )
        )

        self.assertNotContains(
            resp,
            f'<a class="button" href="/admin/localize/update/{self.test_snippet_source.pk}/"><svg class="icon icon-repeat icon" aria-hidden="true" focusable="false"><use href="#icon-repeat"></use></svg>Sync translated snippets</a>',
        )

    def test_sync_button_no_translations(self):
        self.locale_fr.delete()
        self.locale_de.delete()

        resp = self.client.get(
            reverse(
                "wagtailsnippets:edit",
                args=[
                    "wagtail_localize_rws_languagecloud_test",
                    "examplesnippet",
                    self.test_snippet.pk,
                ],
            )
        )

        self.assertNotContains(
            resp,
            f'<a class="button" href="/admin/localize/update/{self.test_snippet_source.pk}/"><svg class="icon icon-repeat icon" aria-hidden="true" focusable="false"><use href="#icon-repeat"></use></svg>Sync translated snippets</a>',
        )
