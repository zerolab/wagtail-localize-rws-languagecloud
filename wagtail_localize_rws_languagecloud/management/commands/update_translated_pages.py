import logging

from django.core.management.base import BaseCommand
from django.db.models.expressions import F, OuterRef, Subquery
from django.db.models.query_utils import Q
from wagtail.core.models import Page

from wagtail_localize.models import TranslationSource
from wagtail_localize_rws_languagecloud.forms import LanguageCloudProjectSettingsForm
from wagtail_localize_rws_languagecloud.models import (
    LanguageCloudProjectSettings,
    LanguageCloudStatus,
)


class Command(BaseCommand):
    help = "Update translations of recently published pages and send them to RWS LanguageCloud"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Don't actually send the pages to RWS LanguageCloud",
        )

    def handle(self, *args, **options):
        # Set up logging
        log_level = logging.INFO
        if options["verbosity"] > 1:
            log_level = logging.DEBUG

        logger = logging.getLogger(__name__)

        console = logging.StreamHandler()
        console.setLevel(log_level)
        console.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        logger.addHandler(console)
        logger.setLevel(log_level)

        logger.info("Updating translations of recently published pages...")

        # Get all pages that have been published _after_ the translation source was synced.
        pages = Page.objects.filter(
            translation_key=OuterRef("object_id"), locale_id=OuterRef("locale_id")
        )
        sources = TranslationSource.objects.annotate(
            last_published_at=Subquery(pages.values("last_published_at")[:1]),
            page_title=Subquery(pages.values("title")[:1]),
        ).filter(
            # Only sources for live pages
            Q(
                object_id__in=Page.objects.live().values_list(
                    "translation_key", flat=True
                )
            ),
            # Only pages that have been published after the last sync
            Q(last_updated_at__lt=F("last_published_at")),
            # Only pages without ongoing translation projects,
            Q(languagecloudproject__isnull=True)
            | Q(
                languagecloudproject__lc_project_status__in=[
                    LanguageCloudStatus.COMPLETED,
                    LanguageCloudStatus.ARCHIVED,
                ]
            ),
        )

        logger.info(f"Found {len(sources)} page(s) to update.")

        for source in sources:
            if options["dry_run"]:
                logger.info(f"Would update translations for page: {source.page_title}")
                continue

            logger.info(f"Updating translations for page: {source.page_title}")

            # Sync content to translated pages
            source.update_from_db()

            enabled_translations = source.translations.filter(enabled=True)

            # Prep for sending to RWS LanguageCloud
            LanguageCloudProjectSettings.get_or_create_from_source_and_translation_data(
                translation_source=source,
                translations=enabled_translations,
                name=LanguageCloudProjectSettingsForm.default_project_name_prefix,
                description="Wagtail\n"
                + LanguageCloudProjectSettingsForm._get_default_project_description(
                    None, source
                ),
                due_date=LanguageCloudProjectSettingsForm.default_due_date,
                template_id=LanguageCloudProjectSettingsForm.default_project_template_id,
            )

        logger.info("...Done")
