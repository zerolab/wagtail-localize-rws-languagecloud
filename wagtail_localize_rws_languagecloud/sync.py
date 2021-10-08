import datetime
import logging

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from requests.exceptions import RequestException
from wagtail.admin.models import get_object_usage
from wagtail.core.models import Locale, Page
from wagtail_localize.models import Translation

from .importer import Importer
from .models import LanguageCloudFile, LanguageCloudProject
from .rws_client import ApiClient, NotFound


def _get_project_name(translation_source, source_locale):
    object_name = str(translation_source.object.get_instance(source_locale))
    prefix = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get("PROJECT_PREFIX", "")
    now = datetime.datetime.utcnow()
    return f"{prefix}{object_name}_{now:%Y-%m-%d}"


def _get_project_due_date():
    now = datetime.datetime.utcnow()
    delta = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
        "DUE_BY_DELTA", datetime.timedelta(days=7)
    )
    due_date = now + delta
    return due_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _get_project_description(translation_source, source_locale):
    description = ""

    # TODO: Add user who initiated the translation
    # Once we add a form to the page
    # we can capture the logged in user with the form fields

    instance = translation_source.object.get_instance(source_locale)
    if isinstance(instance, Page):
        description = description + (instance.full_url or "")
        return description

    pages = get_object_usage(instance)
    # This is only contextual information. If a snippet appears in hundreds of
    # pages we probably don't need to spam all of them. Just take the first 5.
    urls = [(page.full_url or "") for page in pages.all()[:5]]
    description = description + "\n".join(urls)

    return description


def _should_export(logger, lc_project):
    if lc_project.internal_status == LanguageCloudProject.STATUS_IMPORTED:
        logger.info(
            "Already imported translations for "
            f"{lc_project.translation_source.object_repr}. Skipping.."
        )
        return False

    if lc_project.is_created:
        logger.info(
            f"Already created project {lc_project.lc_project_id} and "
            f"all source files. Skipping.."
        )
        return False

    if lc_project.is_failed:
        logger.info(
            "Too many failed attempts for "
            f"{lc_project.translation_source.object_repr}. Skipping.."
        )
        return False

    return True


@transaction.atomic
def _create_local_project(translation):
    lc_project, _ = LanguageCloudProject.objects.get_or_create(
        translation_source=translation.source,
        source_last_updated_at=translation.source.last_updated_at,
    )
    translations = translation.source.translations.all().filter(enabled=True)
    for translation in translations:
        LanguageCloudFile.objects.get_or_create(
            translation=translation,
            project=lc_project,
        )
    return lc_project


def _create_remote_project(lc_project, client, name, due_by, description):
    try:
        create_project_resp = client.create_project(name, due_by, description)
        lc_project.lc_project_id = create_project_resp["id"]
        lc_project.create_attempts = lc_project.create_attempts + 1
        lc_project.save()
        return create_project_resp["id"]
    except (RequestException, KeyError):
        lc_project.create_attempts = lc_project.create_attempts + 1
        lc_project.save()
        raise


def _create_remote_source_file(
    lc_source_file, client, project_id, po_file, filename, source_locale, target_locale
):
    try:
        create_file_resp = client.create_source_file(
            project_id, po_file, filename, source_locale, target_locale
        )
        lc_source_file.lc_source_file_id = create_file_resp["id"]
        lc_source_file.create_attempts = lc_source_file.create_attempts + 1
        lc_source_file.save()
        return create_file_resp["id"]
    except (RequestException, KeyError):
        lc_source_file.create_attempts = lc_source_file.create_attempts + 1
        lc_source_file.save()
        raise


def _export(client, logger):
    logger.info("Exporting translations to LanguageCloud...")
    source_locale = Locale.get_default()
    target_locales = Locale.objects.exclude(id=source_locale.id)
    translations = (
        Translation.objects.filter(
            source__locale=source_locale, target_locale__in=target_locales, enabled=True
        )
        .select_related("source", "target_locale")
        .order_by("source__id", "target_locale__language_code", "id")
    )

    for translation in translations:
        logger.info(
            f"Processing Translation {translation.uuid}\n"
            f"       {str(translation.source.object.get_instance(source_locale))}\n"
            f"       {source_locale} --> {str(translation.target_locale)} "
        )
        lc_project = _create_local_project(translation)

        if not _should_export(logger, lc_project):
            continue

        project_id = lc_project.lc_project_id

        name = _get_project_name(translation.source, source_locale)
        due_by = _get_project_due_date()
        description = _get_project_description(translation.source, source_locale)

        if not project_id:
            try:
                project_id = _create_remote_project(
                    lc_project, client, name, due_by, description
                )
            except (RequestException, KeyError):
                logger.error("Failed to create project")
                continue
            logger.info(f"Created project: {project_id}")
        else:
            logger.info(f"Already created project: {project_id}. Skipping..")

        lc_source_file = LanguageCloudFile.objects.get(
            translation=translation,
            project=lc_project,
        )
        source_file_id = lc_source_file.lc_source_file_id
        if not source_file_id:
            try:
                source_file_id = _create_remote_source_file(
                    lc_source_file,
                    client,
                    project_id,
                    str(translation.source.export_po()),
                    f"{name}_{str(translation.target_locale)}.po",
                    source_locale.language_code,
                    translation.target_locale.language_code,
                )
            except (RequestException, KeyError):
                logger.error("Failed to create source file")
                continue
            logger.info(f"Created source file: {source_file_id}")
        else:
            logger.info(f"Already created source file: {source_file_id}. Skipping..")


def _import(client, logger):
    logger.info("Importing translations from LanguageCloud...")
    lc_projects = (
        LanguageCloudProject.objects.all()
        .exclude(internal_status=LanguageCloudProject.STATUS_IMPORTED)
        .exclude(lc_project_id="")
        .order_by("id")
    )

    for db_project in lc_projects:
        source_locale = db_project.translation_source.locale
        logger.info(
            f"Processing TranslationSource {str(db_project.translation_source.object.get_instance(source_locale))}"
        )

        try:
            api_project = client.get_project(db_project.lc_project_id)
        except RequestException:
            logger.error(
                f"Failed to fetch status for project {db_project.lc_project_id}"
            )
            continue

        if api_project["status"] != "completed":
            logger.info(
                f"LanguageCloud Project Status: \"{api_project['status']}\". Skipping.."
            )
            continue

        lc_source_files = (
            db_project.languagecloudfile_set.all()
            .exclude(internal_status=LanguageCloudFile.STATUS_IMPORTED)
            .exclude(lc_source_file_id="")
            .order_by("id")
        )

        for db_source_file in lc_source_files:
            target_locale = db_source_file.translation.target_locale
            logger.info(
                f"Processing Translation {db_source_file.translation.uuid}\n"
                f"       {str(source_locale)} --> {str(target_locale)} "
            )

            try:
                target_file = client.download_target_file(
                    db_project.lc_project_id,
                    db_source_file.lc_source_file_id,
                )
            except (RequestException, KeyError, NotFound):
                logger.error(
                    f"Failed to download target file for source file {db_source_file.lc_source_file_id}"
                )
                continue

            logger.info("Importing translations from target file")
            importer = Importer(db_source_file, logger)
            try:
                importer.import_po(db_source_file.translation, target_file)
            except SuspiciousOperation as e:
                logger.error(str(e))
                continue
            logger.info(
                f"Successfully imported translations for {db_source_file.translation.uuid}"
            )

        db_project.refresh_from_db()
        if db_project.all_files_imported:
            db_project.internal_status = LanguageCloudProject.STATUS_IMPORTED
            db_project.save()


class SyncManager:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def sync(self):
        self.logger.info("Syncing with RWS LanguageCloud...")

        """
        Calling authenticate() will request an OAUth token
        which can be used for the duration of the session
        (a token expires after 24 hours).

        We can't do anything without auth, so there is no try/except here.
        If we throw an exception invoking ApiClient() the error is fatal.
        """
        client = ApiClient(self.logger)
        client.authenticate()

        _import(client, self.logger)
        _export(client, self.logger)

        self.logger.info("...Done")

    def trigger(self):
        """
        Called when user presses the "Sync" button in the admin

        This should enqueue a background task to run the sync() function
        """
        self.sync()

    def is_queued(self):
        """
        Returns True if the background task is queued
        """
        return False

    def is_running(self):
        """
        Returns True if the background task is currently running
        """
        return False
