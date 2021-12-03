import datetime
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from wagtail.admin.models import get_object_usage
from wagtail.core.models import Page

from wagtail_localize_rws_languagecloud.models import (
    LanguageCloudProject,
    LanguageCloudProjectSettings,
)


class Command(BaseCommand):
    def handle(self, **options):
        log_level = logging.INFO
        if options["verbosity"] > 1:
            log_level = logging.DEBUG

        self.logger = logging.getLogger(__name__)

        # Enable logging to console
        console = logging.StreamHandler()
        console.setLevel(log_level)
        console.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        self.logger.addHandler(console)
        self.logger.setLevel(log_level)

        self.add_project_settings_from_projects()

    def _get_project_name(self, project):
        object_name = str(project.translation_source.get_source_instance())
        prefix = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get("PROJECT_PREFIX", "")
        return f"{prefix}{object_name}_{project.source_last_updated_at:%Y-%m-%d}"

    def _get_project_description(self, project):
        description = ""
        instance = project.translation_source.get_source_instance()
        if isinstance(instance, Page):
            description = description + (instance.full_url or "")
            return description

        pages = get_object_usage(instance)
        # This is only contextual information. If a snippet appears in hundreds of
        # pages we probably don't need to spam all of them. Just take the first 5.
        urls = [(page.full_url or "") for page in pages.all()[:5]]
        description = description + "\n".join(urls)

        return description

    def _get_project_due_date(self, project):
        delta = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
            "DUE_BY_DELTA", datetime.timedelta(days=7)
        )
        due_date = project.source_last_updated_at + delta
        return due_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def add_project_settings_from_projects(self):
        default_template_id = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
            "TEMPLATE_ID"
        )

        for project in LanguageCloudProject.objects.filter(lc_settings__isnull=True):
            self.logger.log(
                self.logger.level,
                f"Processing {project} for {project.translation_source.get_source_instance()}",
            )
            LanguageCloudProjectSettings.get_or_create_from_source_and_translation_data(
                project.translation_source,
                project.translation_source.translations.all(),
                name=self._get_project_name(project),
                description=self._get_project_description(project),
                due_date=self._get_project_due_date(project),
                template_id=default_template_id,
                lc_project=project,
            )
