import logging

from django.core.management.base import BaseCommand

from ...sync import SyncManager


class Command(BaseCommand):
    def handle(self, **options):
        log_level = logging.INFO
        if options["verbosity"] > 1:
            log_level = logging.DEBUG

        logger = logging.getLogger(__name__)

        # Enable logging to console
        console = logging.StreamHandler()
        console.setLevel(log_level)
        console.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        logger.addHandler(console)
        logger.setLevel(log_level)

        SyncManager(logger=logger).sync()
