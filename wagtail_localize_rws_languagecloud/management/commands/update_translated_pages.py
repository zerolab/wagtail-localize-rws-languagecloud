import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.expressions import F, OuterRef, Subquery
from wagtail.core.models import Page

from wagtail_localize.models import TranslationSource
from wagtail_localize_rws_languagecloud.emails import (
    send_update_translated_pages_emails,
)
from wagtail_localize_rws_languagecloud.forms import (
    get_default_due_date,
    get_default_project_description,
    get_default_project_name_prefix,
    get_default_project_template_id,
)
from wagtail_localize_rws_languagecloud.models import (
    LanguageCloudProjectSettings,
    LanguageCloudStatus,
)


class Command(BaseCommand):
    help = "Update translations of pages with stale translated content and send them to RWS LanguageCloud"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Don't actually sync or send the pages to RWS LanguageCloud",
        )

    @transaction.atomic
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

        logger.info("Updating translations of pages with stale translated content...")

        # Get all pages that have been published _after_ the translation source was synced.
        pages = Page.objects.filter(
            translation_key=OuterRef("object_id"), locale_id=OuterRef("locale_id")
        )
        all_sources = TranslationSource.objects.annotate(
            last_published_at=Subquery(pages.values("last_published_at")[:1]),
            page_pk=Subquery(pages.values("id")[:1]),
            page_title=Subquery(pages.values("title")[:1]),
        ).filter(
            # Only sources for live pages
            object_id__in=Page.objects.live().values_list("translation_key", flat=True),
            # Only pages that have been published after the last sync
            last_updated_at__lt=F("last_published_at"),
        )

        sources_to_update = all_sources.exclude(
            # Only pages without ongoing translation projects,
            languagecloudproject__lc_project_status__in=[
                LanguageCloudStatus.CREATED,
                LanguageCloudStatus.IN_PROGRESS,
            ]
        )

        total_count = len(all_sources)
        to_update_count = len(sources_to_update)

        logger.info(
            f"Found {total_count} page(s) with stale translated content.\n"
            f"       {to_update_count} will be synced.\n"
            f"       {total_count - to_update_count} will be skipped."
        )

        all_pages = {(source.page_pk, source.page_title) for source in all_sources}

        updated_pages = set()

        for index, source in enumerate(sources_to_update):
            updated_pages.add((source.page_pk, source.page_title))

            counter = f"[{index + 1}/{to_update_count}]"

            if options["dry_run"]:
                logger.info(
                    f'{counter} Would update translations for page: {source.page_pk} - "{source.page_title}"'
                )
                continue

            logger.info(
                f'{counter} Updating translations for page: {source.page_pk} - "{source.page_title}"'
            )

            # Sync content to translated pages
            source.update_from_db()

            enabled_translations = source.translations.filter(enabled=True)

            # Prep for sending to RWS LanguageCloud
            LanguageCloudProjectSettings.get_or_create_from_source_and_translation_data(
                translation_source=source,
                translations=enabled_translations,
                name=get_default_project_name_prefix(),
                # Prefix with "Wagtail" because we don't have a user to
                # pass into get_default_project_description.
                description="Wagtail\n" + get_default_project_description(source),
                due_date=get_default_due_date(),
                template_id=get_default_project_template_id(),
            )

        skipped_pages = all_pages - updated_pages

        for page_pk, page_title in skipped_pages:
            logger.debug(f'Skipped page: {page_pk} - "{page_title}"')

        if (
            settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get("SEND_EMAILS", False)
            and not options["dry_run"]
        ):
            logger.info("Sending summary emails")
            send_update_translated_pages_emails(
                list(all_pages), list(updated_pages), list(skipped_pages)
            )

        logger.info("...Done")
