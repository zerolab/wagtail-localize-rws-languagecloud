import json
import logging
import re

from time import sleep

import requests

from django.conf import settings


safe_characters = re.compile(r"[^\w\- ]+")


def rws_language_code(language_code):
    """
    Returns the mapped RWS language code, if found in the LANGUAGE_CODE_MAP setting.
    Defaults to the original value.
    """
    language_code_map = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
        "LANGUAGE_CODE_MAP", {}
    )
    return language_code_map.get(language_code, language_code)


class NotAuthenticated(Exception):
    pass


class NotFound(Exception):
    pass


REQUEST_TIMEOUT = 10


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
        self.api_sleep_seconds = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
            "API_SLEEP_SECONDS", 0
        )

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
            timeout=REQUEST_TIMEOUT,
        )
        self.logger.debug(r.text)
        r.raise_for_status()
        sleep(self.api_sleep_seconds)

        self.is_authenticated = True
        self.token = r.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "X-LC-Tenant": settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD["ACCOUNT_ID"],
        }

    def create_project(
        self,
        name,
        due_by,
        description,
        template_id,
        location_id,
        source_locale,
        target_locales,
    ):
        """
        Creates a new project.
        https://languagecloud.sdl.com/lc/api-docs/rest-api/project/createproject
        """
        self.logger.debug("create_project")
        if not self.is_authenticated:
            raise NotAuthenticated()

        # Ensure the name doesn't include special characters
        cleaned_name = safe_characters.sub("", name)

        source_language_code = rws_language_code(source_locale)
        body = json.dumps(
            {
                "name": cleaned_name,
                "dueBy": due_by,
                "description": description,
                "projectTemplate": {"id": template_id},
                "location": location_id,
                "languageDirections": [
                    {
                        "sourceLanguage": {"languageCode": source_language_code},
                        "targetLanguage": {
                            "languageCode": rws_language_code(target_locale)
                        },
                    }
                    for target_locale in target_locales
                ],
            }
        )
        r = requests.post(
            f"{self.api_base}/projects",
            body,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT,
        )
        self.logger.debug(r.text)
        r.raise_for_status()
        sleep(self.api_sleep_seconds)
        return r.json()

    def start_project(self, project_id):
        """
        Starts a project, given a project_id
        https://languagecloud.sdl.com/lc/api-docs/rest-api/project/startproject
        """
        self.logger.debug(f"start_project {project_id}")
        if not self.is_authenticated:
            raise NotAuthenticated()

        r = requests.put(
            f"{self.api_base}/projects/{project_id}/start",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT,
        )
        self.logger.debug(r.text)
        r.raise_for_status()
        sleep(self.api_sleep_seconds)

    def create_source_file(
        self, project_id, po_file, filename, source_locale, target_locale
    ):
        """
        Adds a source file to a project.
        https://languagecloud.sdl.com/lc/api-docs/rest-api/source-file/addsourcefile
        """
        self.logger.debug("create_source_file")
        if not self.is_authenticated:
            raise NotAuthenticated()

        body = {
            "properties": json.dumps(
                {
                    "name": filename,
                    "role": "translatable",
                    "type": "native",
                    "language": rws_language_code(source_locale),
                    "targetLanguages": [rws_language_code(target_locale)],
                }
            )
        }
        files = {"file": (filename, po_file, "text/plain")}
        r = requests.post(
            f"{self.api_base}/projects/{project_id}/source-files",
            data=body,
            files=files,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT,
        )
        self.logger.debug(r.text)
        r.raise_for_status()
        sleep(self.api_sleep_seconds)
        return r.json()

    def get_project(self, project_id):
        """
        Retrieves a project by id.
        https://languagecloud.sdl.com/lc/api-docs/rest-api/project/getproject
        """
        self.logger.debug("get_project")
        if not self.is_authenticated:
            raise NotAuthenticated()

        r = requests.get(
            f"{self.api_base}/projects/{project_id}",
            params={"fields": "id,name,description,dueBy,createdAt,status"},
            headers=self.headers,
            timeout=REQUEST_TIMEOUT,
        )
        self.logger.debug(r.text)
        r.raise_for_status()
        sleep(self.api_sleep_seconds)
        return r.json()

    def complete_project(self, project_id):
        """
        Set the status of a project to "complete"
        https://languagecloud.sdl.com/lc/api-docs/rest-api/project/completeproject
        """
        self.logger.debug(f"complete_project {project_id}")
        if not self.is_authenticated:
            raise NotAuthenticated()

        r = requests.put(
            f"{self.api_base}/projects/{project_id}/complete",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT,
        )
        self.logger.debug(r.text)
        r.raise_for_status()
        sleep(self.api_sleep_seconds)

    def download_target_file(self, project_id, source_file_id):
        """
        Retrieves a targer file for the project
        https://languagecloud.sdl.com/lc/api-docs/rest-api/target-file/listtargetfiles
        https://languagecloud.sdl.com/lc/api-docs/rest-api/target-file/downloadfileversion
        """
        self.logger.debug("download_target_file")
        if not self.is_authenticated:
            raise NotAuthenticated()

        list_req = requests.get(
            f"{self.api_base}/projects/{project_id}/target-files",
            params={"fields": "sourceFile,latestVersion"},
            headers=self.headers,
            timeout=REQUEST_TIMEOUT,
        )
        self.logger.debug(list_req.text)
        list_req.raise_for_status()
        sleep(self.api_sleep_seconds)
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
            timeout=REQUEST_TIMEOUT,
        )
        self.logger.debug(download_req.text)
        download_req.raise_for_status()
        sleep(self.api_sleep_seconds)

        return download_req.text

    def get_project_templates(self, should_sleep=True):
        """
        Fetches project templates.
        https://languagecloud.sdl.com/lc/api-docs/rest-api/project-template/listprojecttemplates
        """
        self.logger.debug("get_project_templates")
        if not self.is_authenticated:
            raise NotAuthenticated()

        r = requests.get(
            f"{self.api_base}/project-templates",
            params={"fields": "id,name,location"},
            headers=self.headers,
            timeout=REQUEST_TIMEOUT,
        )
        self.logger.debug(r.text)
        r.raise_for_status()
        if should_sleep:
            sleep(self.api_sleep_seconds)
        return r.json()

    def _get(self, url):
        """
        Generic get method. This is mainly here to make ad-hoc debugging easier.
        It is not called anywhere
        """
        self.logger.debug("get")
        if not self.is_authenticated:
            raise NotAuthenticated()

        r = requests.get(
            f"{self.api_base}/{url}",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT,
        )
        self.logger.debug(r.text)
        r.raise_for_status()
        return r.json()
