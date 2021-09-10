import json
from django.conf import settings
import requests


class ApiClient:
    def __init__(self):
        self.auth_base = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
            "AUTH_BASE",
            "https://sdl-prod.eu.auth0.com/oauth/token",
        )
        self.auth_audience = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
            "AUTH_AUDIENCE",
            "https://api.sdl.com",
        )
        self.api_base = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
            "API_BASE",
            "https://lc-api.sdl.com/public-api/v1",
        )
        self.token = self._authenticate()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "X-LC-Tenant": settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD["ACCOUNT_ID"],
        }

    def _authenticate(self):
        r = requests.post(
            self.auth_base,
            {
                "grant_type": "client_credentials",
                "audience": self.auth_audience,
                "client_id": settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD["CLIENT_ID"],
                "client_secret": settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD[
                    "CLIENT_SECRET"
                ],
            },
        )
        r.raise_for_status()
        return r.json()["access_token"]

    def create_project(self, name, due_by, description):
        body = json.dumps(
            {
                "name": name,
                "dueBy": due_by,
                "description": description,
                "projectTemplate": {
                    "id": settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD["TEMPLATE_ID"]
                },
            }
        )
        r = requests.post(
            f"{self.api_base}/projects",
            body,
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json()

    def create_source_file(self, project_id, po_file, filename, source_locale, target_locale):
        body = {
            "properties": json.dumps(
                {
                    "name": filename,
                    "role": "translatable",
                    "type": "native",
                    "language": source_locale,
                    "targetLanguages": [target_locale],
                }
            )
        }
        files = {"file": (filename, po_file, "text/plain")}
        r = requests.post(
            f"{self.api_base}/projects/{project_id}/source-files",
            data=body,
            files=files,
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json()
