import json

from urllib.parse import parse_qs

import responses

from django.test import TestCase, override_settings
from requests.exceptions import RequestException

from ..rws_client import ApiClient, NotAuthenticated, NotFound, rws_language_code


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

    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
            "CLIENT_ID": "fakeid",
            "CLIENT_SECRET": "fakesecret",
            "ACCOUNT_ID": "fakeaccount",
        },
    )
    @responses.activate
    def test_authenticate_success(self):
        responses.add(
            responses.POST,
            "https://sdl-prod.eu.auth0.com/oauth/token",
            json={
                "access_token": "abc123",
                "expires_in": 86400,
                "token_type": "Bearer",
            },
            status=200,
        )
        client = ApiClient()
        client.authenticate()

        self.assertEqual(len(responses.calls), 1)
        self.assertDictEqual(
            {
                "grant_type": ["client_credentials"],
                "audience": ["https://api.sdl.com"],
                "client_id": ["fakeid"],
                "client_secret": ["fakesecret"],
            },
            parse_qs(responses.calls[0].request.body),
        )

        self.assertEqual(client.token, "abc123")
        self.assertEqual(client.is_authenticated, True)
        self.assertEqual(client.headers["Authorization"], "Bearer abc123")
        self.assertEqual(client.headers["X-LC-Tenant"], "fakeaccount")

    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
            "CLIENT_ID": "fakeid",
            "CLIENT_SECRET": "fakesecret",
            "ACCOUNT_ID": "fakeaccount",
        },
    )
    @responses.activate
    def test_authenticate_fail(self):
        responses.add(
            responses.POST,
            "https://sdl-prod.eu.auth0.com/oauth/token",
            json={"error": "access_denied", "error_description": "Unauthorized"},
            status=401,
        )
        client = ApiClient()
        with self.assertRaises(RequestException):
            client.authenticate()
        self.assertEqual(len(responses.calls), 1)

    def test_create_project_not_authenticated(self):
        client = ApiClient()
        with self.assertRaises(NotAuthenticated):
            client.create_project(
                "faketitle",
                "2020-01-01T00:00:01.000Z",
                "fakedesc",
                "faketemplate",
                "fakelocation",
                "en",
                ["fr"],
            )

    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
            "TEMPLATE_ID": "faketemplate",
            "LOCATION_ID": "fakelocation",
        },
    )
    @responses.activate
    def test_create_project_success(self):
        responses.add(
            responses.POST,
            "https://lc-api.sdl.com/public-api/v1/projects",
            json={"id": "123456"},
            status=200,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        resp = client.create_project(
            "faketitle",
            "2020-01-01T00:00:01.000Z",
            "fakedesc",
            "faketemplate",
            "fakelocation",
            "en",
            ["fr", "de-de"],
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertDictEqual(
            {
                "name": "faketitle",
                "dueBy": "2020-01-01T00:00:01.000Z",
                "description": "fakedesc",
                "projectTemplate": {"id": "faketemplate"},
                "location": "fakelocation",
                "languageDirections": [
                    {
                        "sourceLanguage": {"languageCode": "en"},
                        "targetLanguage": {"languageCode": "fr"},
                    },
                    {
                        "sourceLanguage": {"languageCode": "en"},
                        "targetLanguage": {"languageCode": "de-de"},
                    },
                ],
            },
            json.loads(responses.calls[0].request.body),
        )
        self.assertEqual(resp, {"id": "123456"})

    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
            "TEMPLATE_ID": "faketemplate",
            "LOCATION_ID": "fakelocation",
        },
    )
    @responses.activate
    def test_create_project_fail(self):
        responses.add(
            responses.POST,
            "https://lc-api.sdl.com/public-api/v1/projects",
            json={"errorCode": "BAD REQUEST", "message": "nope", "details": []},
            status=400,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        with self.assertRaises(RequestException):
            client.create_project(
                "faketitle",
                "2020-01-01T00:00:01.000Z",
                "fakedesc",
                "faketemplate",
                "fakelocation",
                "en",
                ["fr"],
            )
        self.assertEqual(len(responses.calls), 1)

    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
            "TEMPLATE_ID": "faketemplate",
            "LOCATION_ID": "fakelocation",
        },
    )
    @responses.activate
    def test_create_project_with_special_characters(self):
        responses.add(
            responses.POST,
            "https://lc-api.sdl.com/public-api/v1/projects",
            json={"id": "123456"},
            status=200,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        resp = client.create_project(
            "my project_My page #!?@#$%^&*()_+-= But without special characters",
            "2020-01-01T00:00:01.000Z",
            "fakedesc",
            "faketemplate",
            "fakelocation",
            "en",
            ["fr", "de-de"],
        )
        self.assertEqual(len(responses.calls), 1)

        resp_data = json.loads(responses.calls[0].request.body)
        self.assertEqual(
            "my project_My page _- But without special characters", resp_data["name"]
        )
        self.assertEqual(resp, {"id": "123456"})

    def test_create_source_file_not_authenticated(self):
        client = ApiClient()
        with self.assertRaises(NotAuthenticated):
            client.create_source_file(
                "fakeproject", "fakepo", "fakefilename.po", "en-US", "fr-CA"
            )

    @responses.activate
    def test_create_source_file_success(self):
        responses.add(
            responses.POST,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject/source-files",
            json={"id": "123456"},
            status=200,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        resp = client.create_source_file(
            "fakeproject", "fakepo", "fakefilename.po", "en-US", "fr-CA"
        )
        self.assertEqual(len(responses.calls), 1)
        # TODO: assert POST body/files contents
        self.assertEqual(resp, {"id": "123456"})

    @responses.activate
    def test_create_source_file_fail(self):
        responses.add(
            responses.POST,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject/source-files",
            json={"errorCode": "BAD REQUEST", "message": "nope", "details": []},
            status=400,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        with self.assertRaises(RequestException):
            client.create_source_file(
                "fakeproject", "fakepo", "fakefilename.po", "en-US", "fr-CA"
            )
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_get_project_success(self):
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject",
            json={"id": "123456", "status": "inProgress"},
            status=200,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        resp = client.get_project("fakeproject")
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(resp, {"id": "123456", "status": "inProgress"})

    @responses.activate
    def test_get_project_fail(self):
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject",
            json={"errorCode": "BAD REQUEST", "message": "nope", "details": []},
            status=400,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        with self.assertRaises(RequestException):
            client.get_project("fakeproject")
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_download_target_file_success(self):
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject/target-files",
            json={
                "items": [
                    {
                        "id": "12345",
                        "latestVersion": {"id": "678910", "type": "native"},
                        "sourceFile": {"id": "faketargetfile", "role": "translatable"},
                    }
                ],
                "itemCount": 1,
            },
            status=200,
        )
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject/target-files/12345/versions/678910/download",
            body='msgid ""...',
            status=200,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        resp = client.download_target_file("fakeproject", "faketargetfile")
        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(resp, 'msgid ""...')

    @responses.activate
    def test_download_target_file_fail_list_target_files(self):
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject/target-files",
            json={"errorCode": "BAD REQUEST", "message": "nope", "details": []},
            status=400,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        with self.assertRaises(RequestException):
            client.download_target_file("fakeproject", "faketargetfile")
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_download_target_file_fail_no_matching_target_files(self):
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject/target-files",
            json={
                "items": [
                    {
                        "id": "12345",
                        "latestVersion": {"id": "678910", "type": "bcm"},
                        "sourceFile": {"id": "faketargetfile", "role": "translatable"},
                    }
                ],
                "itemCount": 1,
            },
            status=200,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        with self.assertRaises(NotFound):
            client.download_target_file("fakeproject", "faketargetfile")
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_download_target_file_fail_many_matching_target_files(self):
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject/target-files",
            json={
                "items": [
                    {
                        "id": "12345",
                        "latestVersion": {"id": "678910", "type": "native"},
                        "sourceFile": {"id": "faketargetfile", "role": "translatable"},
                    },
                    {
                        "id": "12345",
                        "latestVersion": {"id": "678911", "type": "native"},
                        "sourceFile": {"id": "faketargetfile", "role": "translatable"},
                    },
                ],
                "itemCount": 2,
            },
            status=200,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        with self.assertRaises(NotFound):
            client.download_target_file("fakeproject", "faketargetfile")
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_download_target_file_fail_download(self):
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject/target-files",
            json={
                "items": [
                    {
                        "id": "12345",
                        "latestVersion": {"id": "678910", "type": "native"},
                        "sourceFile": {"id": "faketargetfile", "role": "translatable"},
                    }
                ],
                "itemCount": 1,
            },
            status=200,
        )
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/projects/fakeproject/target-files/12345/versions/678910/download",
            json={"errorCode": "BAD REQUEST", "message": "nope", "details": []},
            status=400,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        with self.assertRaises(RequestException):
            client.download_target_file("fakeproject", "faketargetfile")
        self.assertEqual(len(responses.calls), 2)

    @responses.activate
    def test_get_project_templates_success(self):
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/project-templates",
            json={"items": [{"id": "123456", "name": "Project X"}]},
            status=200,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        resp = client.get_project_templates()
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(resp, {"items": [{"id": "123456", "name": "Project X"}]})

    @responses.activate
    def test_get_project_templates_fail(self):
        responses.add(
            responses.GET,
            "https://lc-api.sdl.com/public-api/v1/projects-templates",
            json={"errorCode": "BAD REQUEST", "message": "nope", "details": []},
            status=400,
        )
        client = ApiClient()

        # fake the auth step
        client.is_authenticated = True
        client.headers = {}

        with self.assertRaises(RequestException):
            client.get_project_templates()
        self.assertEqual(len(responses.calls), 1)

    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={
            "LANGUAGE_CODE_MAP": {"en": "en-US", "fr": "fr-FR"}
        }
    )
    def test_rws_language_code(self):
        self.assertEqual(rws_language_code("en"), "en-US")
        self.assertEqual(rws_language_code("fr"), "fr-FR")
        self.assertEqual(rws_language_code("de"), "de")
