import logging

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.db.models import Count, F, Q
from requests.exceptions import RequestException

from .emails import send_emails
from .importer import Importer
from .models import (
    LanguageCloudFile,
    LanguageCloudProject,
    LanguageCloudProjectSettings,
)
from .rws_client import ApiClient, NotFound


def _get_project_templates_and_locations(client: ApiClient):
    cache_key = "RWS_PROJECT_TEMPLATES"

    cached_templates_and_locations = cache.get(cache_key)
    if cached_templates_and_locations:
        return cached_templates_and_locations

    try:
        templates_and_locations = client.get_project_templates()
    except RequestException:
        templates_and_locations = {}

    cached_templates_and_locations = {
        template["id"]: template["location"]["id"]
        for template in templates_and_locations.get("items", [])
    }
    cache.set(cache_key, cached_templates_and_locations, 60 * 5)

    return cached_templates_and_locations


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
def _create_local_project(project_settings: LanguageCloudProjectSettings):
    lc_project, _ = LanguageCloudProject.objects.get_or_create(
        translation_source=project_settings.translation_source,
        source_last_updated_at=project_settings.source_last_updated_at,
    )
    # link the project settings with the project
    project_settings.lc_project = lc_project
    project_settings.save()

    translations = project_settings.translations.all().filter(enabled=True)
    for translation in translations:
        LanguageCloudFile.objects.get_or_create(
            translation=translation,
            project=lc_project,
        )
    return lc_project


def _create_remote_project(lc_project, project_templates_and_locations, client):
    name = lc_project.lc_settings.name
    due_by = lc_project.lc_settings.formatted_due_date
    description = lc_project.lc_settings.description
    template_id = lc_project.lc_settings.template_id
    location_id = project_templates_and_locations.get(
        template_id, settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD["LOCATION_ID"]
    )
    try:
        create_project_resp = client.create_project(
            name, due_by, description, template_id, location_id
        )
        lc_project.lc_project_id = create_project_resp["id"]
        lc_project.lc_project_status = "created"
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


def _get_projects_to_export():
    return (
        LanguageCloudProject.objects.annotate(
            files=Count("languagecloudfile"),
            files_created=Count(
                "languagecloudfile", filter=~Q(languagecloudfile__lc_source_file_id="")
            ),
            files_to_be_created=Count(
                "languagecloudfile", filter=Q(languagecloudfile__lc_source_file_id="")
            ),
            files_exceeding_create_attempts=Count(
                "languagecloudfile", filter=Q(languagecloudfile__create_attempts__gte=3)
            ),
        )
        .filter(lc_settings__isnull=False)  # ensure they are tied to project settings
        .exclude(internal_status=LanguageCloudProject.STATUS_IMPORTED)  # imported
        .exclude(lc_project_status="archived")  # archived in LanguageCloud
        .exclude(  # created: project and all files created in LanguageCloud
            ~Q(lc_project_id=""),  # the project was created in LanguageCloud
            files__gt=0,  # and has at least one file for translation
            files_created=F("files"),  # and all files got created in LanguageCloud too
        )
        .exclude(
            lc_project_id="", create_attempts__gte=3
        )  # failed: project had 3 failed attempts
        .exclude(
            files_exceeding_create_attempts__gt=0
        )  # failed: or any of the files had 3 failed attempts
        .order_by("pk")
        .distinct()
        # To-Do: select-relateds: translation_source, settings
    )


def _export(client, logger):
    logger.info("Creating LanguageCloud translation projects")
    unprocessed_project_settings = LanguageCloudProjectSettings.objects.filter(
        lc_project_id__isnull=True
    ).order_by("pk")
    for project_settings in unprocessed_project_settings:
        _create_local_project(project_settings)

    logger.info("Exporting translations to LanguageCloud...")

    project_templates_and_locations = _get_project_templates_and_locations(client)
    for project in _get_projects_to_export():
        project_id = project.lc_project_id
        try:
            name = project.lc_settings.name
            if not project_id:
                try:
                    project_id = _create_remote_project(
                        project, project_templates_and_locations, client
                    )
                except (RequestException, KeyError):
                    logger.error("Failed to create project")
                    continue
                logger.info(f"Created project: {project_id}")
            else:
                logger.info(f"Already created project: {project_id}. Skipping..")

            source_instance = project.translation_source.get_source_instance()
            source_locale = project.translation_source.locale
            lc_source_files = project.languagecloudfile_set.all()
            remote_files_created = 0
            for lc_source_file in lc_source_files:
                translation = lc_source_file.translation
                if not translation.enabled:
                    remote_files_created += 1  # adds to the total count
                    logger.debug(
                        f"Skipping inactive translation {translation.uuid} for source file {lc_source_file}"
                    )
                    continue

                logger.info(  # todo update message
                    f"Processing Translation {translation.uuid}\n"
                    f"       {str(source_instance)}\n"
                    f"       {source_locale} --> {str(translation.target_locale)} "
                )
                source_file_id = lc_source_file.lc_source_file_id
                if not source_file_id:
                    try:
                        source_file_id = _create_remote_source_file(
                            lc_source_file,
                            client,
                            project_id,
                            str(project.translation_source.export_po()),
                            f"{name}_{str(translation.target_locale)}.po",
                            source_locale.language_code,
                            translation.target_locale.language_code,
                        )
                        remote_files_created += 1
                    except (RequestException, KeyError):
                        logger.error("Failed to create source file")
                        continue
                    logger.info(f"Created source file: {source_file_id}")
                else:
                    remote_files_created += 1
                    logger.info(
                        f"Already created source file: {source_file_id}. Skipping.."
                    )

            if remote_files_created == len(lc_source_files):
                try:
                    client.start_project()
                except RequestException:
                    logger.exception(f"Failed to start project {project_id}")

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:  # noqa
            logger.exception(f"Failed to process project {project_id} ({project.pk})")
            continue


def _import(client, logger):
    logger.info("Importing translations from LanguageCloud...")
    lc_projects = (
        LanguageCloudProject.objects.all()
        .exclude(internal_status=LanguageCloudProject.STATUS_IMPORTED)
        .exclude(lc_project_status="archived")
        .exclude(lc_project_id="")
        .order_by("id")
    )

    for db_project in lc_projects:
        try:
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
            db_project.lc_project_status = api_project["status"]
            db_project.save()

            if api_project["status"] not in ("inProgress", "completed"):
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
                    if settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
                        "SEND_EMAILS", False
                    ):
                        send_emails(db_source_file.translation)
                except SuspiciousOperation as e:
                    logger.exception(e)
                    db_source_file.internal_status = LanguageCloudFile.STATUS_ERROR
                    db_source_file.save()
                    continue
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as e:  # noqa
                    logger.exception(e)
                    db_source_file.internal_status = LanguageCloudFile.STATUS_ERROR
                    db_source_file.save()
                    continue

                logger.info(
                    f"Successfully imported translations for {db_source_file.translation.uuid}"
                )

            db_project.refresh_from_db()
            if db_project.all_files_imported:
                db_project.internal_status = LanguageCloudProject.STATUS_IMPORTED
                db_project.save()
                if api_project["status"] != "completed":
                    try:
                        client.complete_project(db_project.lc_project_id)
                    except (RequestException):
                        pass
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:  # noqa
            logger.exception(
                f"Failed to process translation project {db_project.lc_project_id}"
            )
            continue


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
