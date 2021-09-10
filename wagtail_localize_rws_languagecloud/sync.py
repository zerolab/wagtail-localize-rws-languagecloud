import datetime
import logging
from django.conf import settings
from wagtail.core.models import Locale
from wagtail_localize.models import Translation
from requests.exceptions import RequestException
from .rws_client import ApiClient


def _get_existing_project(translation):
    # TODO: query DB
    # if we already have a LanguageCloud project for this translation object
    # return the LanguageCloud Project ID
    # else return None
    return None


def _get_existing_source_file(translation):
    # TODO: query DB
    # if we already have a LanguageCloud source file for this translation object
    # return the LanguageCloud Source File ID
    # else return None
    return None


def _get_project_name(translation, source_locale):
    object_name = str(translation.source.object.get_instance(source_locale))
    prefix = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get("PROJECT_PREFIX", "")
    return f"{prefix}{object_name}_{str(translation.target_locale)}"


def _get_project_due_date():
    now = datetime.datetime.now()
    delta = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
        "DUE_BY_DELTA", datetime.timedelta(days=7)
    )
    due_date = now + delta
    return due_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _get_project_description(translation):
    return "test project"


def _export(client, logger):
    source_locale = Locale.get_default()
    target_locales = Locale.objects.exclude(id=source_locale.id)
    translations = (
        Translation.objects.filter(
            source__locale=source_locale, target_locale__in=target_locales, enabled=True
        )
        .select_related("source", "target_locale")
        .order_by("target_locale__language_code")
    )

    for translation in translations:
        logger.info(
            f"Processing Translation {translation.uuid}\n"
            f"       {str(translation.source.object.get_instance(source_locale))}\n"
            f"       {source_locale} --> {str(translation.target_locale)} "
        )

        project_id = _get_existing_project(translation)

        name = _get_project_name(translation, source_locale)
        due_by = _get_project_due_date()
        description = _get_project_description(translation)

        if not project_id:
            try:
                create_project_resp = client.create_project(name, due_by, description)
                # TODO: save to DB
            except (RequestException, KeyError):
                logger.error("Failed to create project")
                # TODO: log the attempt/failure in the DB
                continue
            project_id = create_project_resp["id"]
            logger.info(f"Created project: {project_id}")
        else:
            logger.info(f"Already created project: {project_id}. Skipping..")

        source_file_id = _get_existing_source_file(translation)
        if not source_file_id:
            try:
                create_file_resp = client.create_source_file(
                    project_id,
                    str(translation.source.export_po()),
                    f"{name}.po",
                    source_locale.language_code,
                    translation.target_locale.language_code,
                )
                # TODO: save to DB
            except (RequestException, KeyError):
                logger.error("Failed to create source file")
                # TODO: log the attempt/failure in the DB
                continue
            source_file_id = create_file_resp["id"]
            logger.info(f"Created source file: {source_file_id}")
        else:
            logger.info(f"Already created source file: {source_file_id}. Skipping..")


def _import(client, logger):
    # TODO
    pass


class SyncManager:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def sync(self):
        self.logger.info("Syncing with RWS LanguageCloud...")

        """
        Constructing an ApiClient object will request an OAUth token
        which can be used for the duration of the session
        (a token expires after 24 hours).
        
        We can't do anything without auth, so there is no try/except here.
        If we throw an exception invoking ApiClient() the error is fatal.
        """
        client = ApiClient()

        _export(client, self.logger)
        _import(client, self.logger)

        self.logger.info("...Done")
