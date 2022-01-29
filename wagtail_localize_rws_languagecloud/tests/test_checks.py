from django.conf import settings
from django.core.checks import Error
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from wagtail_localize_rws_languagecloud.checks import languagecloud_settings_check


class ChecksTests(SimpleTestCase):
    def check_error_codes(self, expected):
        errors = languagecloud_settings_check(None)
        self.assertEqual(len(errors), len(expected))
        self.assertTrue(all(isinstance(e, Error) for e in errors))
        self.assertEqual([e.id for e in errors], expected)
        return errors

    @override_settings()
    def test_missing_settings_fails(self):
        del settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD
        self.check_error_codes(["wagtail_localize_rws_languagecloud.E001"])

    def test_defaults_pass_check(self):
        call_command("check")

    @override_settings(WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={})
    def test_required(self):
        with override_settings(SILENCED_SYSTEM_CHECKS=[]):
            self.check_error_codes(["wagtail_localize_rws_languagecloud.E002"] * 5)

    def test_language_code_map(self):
        with override_settings(
            WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
                "CLIENT_ID": "",
                "CLIENT_SECRET": "",
                "ACCOUNT_ID": "",
                "TEMPLATE_ID": "",
                "LOCATION_ID": "",
                "LANGUAGE_CODE_MAP": "",
            }
        ):
            self.check_error_codes(["wagtail_localize_rws_languagecloud.E003"])

        with override_settings(
            WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
                "CLIENT_ID": "",
                "CLIENT_SECRET": "",
                "ACCOUNT_ID": "",
                "TEMPLATE_ID": "",
                "LOCATION_ID": "",
                "LANGUAGE_CODE_MAP": {"a": "b"},
            }
        ):
            self.check_error_codes([])
