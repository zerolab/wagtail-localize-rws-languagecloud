from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls.base import reverse
from wagtail.core.models.i18n import Locale
from wagtail.tests.utils import WagtailTestUtils

from .helpers import create_editor_user, create_test_page


class TestTranslateButton(TestCase, WagtailTestUtils):
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
