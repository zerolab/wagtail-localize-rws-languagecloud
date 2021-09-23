import json
import logging
from django.conf import settings
import requests


class NotAuthenticated(Exception):
    pass


class NotFound(Exception):
    pass


class ApiClient:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
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
        self.is_authenticated = False

    def authenticate(self):
        self.logger.debug("authenticate")
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
        self.logger.debug(r.text)
        r.raise_for_status()

        self.is_authenticated = True
        self.token = r.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "X-LC-Tenant": settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD["ACCOUNT_ID"],
        }

    def create_project(self, name, due_by, description):
        self.logger.debug("create_project")
        if not self.is_authenticated:
            raise NotAuthenticated()

        body = json.dumps(
            {
                "name": name,
                "dueBy": due_by,
                "description": description,
                "projectTemplate": {
                    "id": settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD["TEMPLATE_ID"]
                },
                "location": settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD["LOCATION_ID"],
            }
        )
        r = requests.post(
            f"{self.api_base}/projects",
            body,
            headers=self.headers,
        )
        self.logger.debug(r.text)
        r.raise_for_status()
        return r.json()

    def create_source_file(
        self, project_id, po_file, filename, source_locale, target_locale
    ):
        self.logger.debug("create_source_file")
        if not self.is_authenticated:
            raise NotAuthenticated()

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
        self.logger.debug(r.text)
        r.raise_for_status()
        return r.json()

    def get_project(self, project_id):
        self.logger.debug("get_project")
        if not self.is_authenticated:
            raise NotAuthenticated()

        r = requests.get(
            f"{self.api_base}/projects/{project_id}",
            params={"fields": "id,name,description,dueBy,createdAt,status"},
            headers=self.headers,
        )
        self.logger.debug(r.text)
        r.raise_for_status()
        return r.json()

    def download_target_file(self, project_id, source_file_id):
        self.logger.debug("download_target_file")
        if not self.is_authenticated:
            raise NotAuthenticated()

        list_req = requests.get(
            f"{self.api_base}/projects/{project_id}/target-files",
            params={"fields": "sourceFile,latestVersion"},
            headers=self.headers,
        )
        self.logger.debug(list_req.text)
        list_req.raise_for_status()
        target_files = list_req.json()

        matches = [
            tf
            for tf in target_files["items"]
            if tf["sourceFile"]["id"] == source_file_id
            and tf["latestVersion"]["type"] == "native"
        ]
        if len(matches) != 1:
            raise NotFound(f"Expected 1 target file, found {len(matches)}")

        download_req = requests.get(
            f"{self.api_base}/projects/{project_id}/target-files/{matches[0]['id']}/versions/{matches[0]['latestVersion']['id']}/download",
            headers=self.headers,
        )
        self.logger.debug(download_req.text)
        download_req.raise_for_status()

        return download_req.text
