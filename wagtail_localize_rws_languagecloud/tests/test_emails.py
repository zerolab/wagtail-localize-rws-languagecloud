from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from wagtail.core.models import Locale

from wagtail_localize.models import Translation
from wagtail_localize_rws_languagecloud import emails

from .helpers import create_test_page, create_test_po


def _create_user(username, email):
    user_model = get_user_model()
    user_data = {}
    user_data[user_model.USERNAME_FIELD] = username
    user_data["email"] = email
    user_data["password"] = "abc123"
    return user_model.objects.create_user(**user_data)


class TestEmails(TestCase):
    def setUp(self):
        submit_translation_group = Group.objects.create(name="submit_translation_group")
        submit_translation_group.permissions.add(
            Permission.objects.get(
                content_type__app_label="wagtail_localize",
                codename="submit_translation",
            )
        )
        submit_translation_user = _create_user(
            "submit_translation_user", "submit_translation_user@example.com"
        )
        submit_translation_user.groups.add(submit_translation_group)

        add_translation_group = Group.objects.create(name="add_translation_group")
        add_translation_group.permissions.add(
            Permission.objects.get(
                content_type__app_label="wagtail_localize",
                codename="add_translation",
            )
        )
        add_translation_user = _create_user(
            "add_translation_user", "add_translation_user@example.com"
        )
        add_translation_user.groups.add(add_translation_group)

        view_translation_group = Group.objects.create(name="view_translation_group")
        view_translation_group.permissions.add(
            Permission.objects.get(
                content_type__app_label="wagtail_localize",
                codename="view_translation",
            )
        )
        view_translation_user = _create_user(
            "view_translation_user", "view_translation_user@example.com"
        )
        view_translation_user.groups.add(view_translation_group)

        Locale.objects.get(language_code="en")
        locale_fr = Locale.objects.create(language_code="fr")
        _, source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )
        self.translation = Translation.objects.create(
            source=source,
            target_locale=locale_fr,
        )

        po_file = create_test_po(
            [
                (
                    "test_charfield",
                    "Some test translatable content",
                    "Certains tests de contenu traduisible",
                )
            ]
        )
        self.translation.import_po(po_file)
        self.translation.save_target(publish=False)

    def test_get_recipients(self):
        recipients = emails.get_recipients()
        self.assertIn("submit_translation_user@example.com", recipients)
        self.assertIn("add_translation_user@example.com", recipients)
        self.assertNotIn("view_translation_user@example.com", recipients)

    @mock.patch("wagtail_localize_rws_languagecloud.emails.send_mail")
    def test_send_email(self, send_mail):
        emails.send_emails(self.translation)
        self.assertEqual(send_mail.call_count, 2)

    @override_settings(BASE_URL="https://foobar.com")
    def test_compose_email(self):
        _, body = emails.compose_email(self.translation)
        self.assertIn(
            "https://foobar.com" + self.translation.get_target_instance_edit_url(), body
        )
