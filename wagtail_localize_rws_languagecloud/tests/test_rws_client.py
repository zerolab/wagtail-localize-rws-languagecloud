from django.test import TestCase, override_settings
from ..rws_client import ApiClient, NotAuthenticated


class TestApiClient(TestCase):
    def test_init_uses_defaults_if_settings_not_supplied(self):
        client = ApiClient()
        self.assertEqual(
            client.auth_base,
            "https://sdl-prod.eu.auth0.com/oauth/token",
        )
        self.assertEqual(
            client.auth_audience,
            "https://api.sdl.com",
        )
        self.assertEqual(
            client.api_base,
            "https://lc-api.sdl.com/public-api/v1",
        )

    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
            "AUTH_BASE": "https://fakeauthbase.example.com/",
            "AUTH_AUDIENCE": "https://fakeauthaudience.example.com/",
            "API_BASE": "https://fakeapibase.example.com/",
        },
    )
    def test_init_overrides_defaults_with_settings(self):
        client = ApiClient()
        self.assertEqual(
            client.auth_base,
            "https://fakeauthbase.example.com/",
        )
        self.assertEqual(
            client.auth_audience,
            "https://fakeauthaudience.example.com/",
        )
        self.assertEqual(
            client.api_base,
            "https://fakeapibase.example.com/",
        )

    def test_create_project_not_authenticated(self):
        client = ApiClient()
        with self.assertRaises(NotAuthenticated):
            client.create_project("a", "b", "c")

    def test_create_source_file_not_authenticated(self):
        client = ApiClient()
        with self.assertRaises(NotAuthenticated):
            client.create_source_file("a", "b", "c", "d", "e")
