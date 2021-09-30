from django.core.exceptions import SuspiciousOperation, ValidationError
from django.db import transaction
from wagtail.core.models import Page
from wagtail_localize.models import (
    MissingRelatedObjectError,
    StringNotUsedInContext,
    UnknownContext,
    UnknownString,
)
import polib
from .models import LanguageCloudProject


class Importer:
    def __init__(self, db_project, logger):
        self.db_project = db_project
        self.logger = logger

    @transaction.atomic
    def import_po(self, translation, target_file):
        if polib._is_file(target_file):
            raise SuspiciousOperation(f"Expected PO file as string, received {target_file}")

        warnings = translation.import_po(polib.pofile(target_file))
        for warning in warnings:
            if isinstance(warning, UnknownContext):
                self.logger.warning(
                    f"While translating '{translation.source.object_repr}' into {translation.target_locale.get_display_name()}: Unrecognised context '{warning.context}'"
                )

            elif isinstance(warning, UnknownString):
                self.logger.warning(
                    f"While translating '{translation.source.object_repr}' into {translation.target_locale.get_display_name()}: Unrecognised string '{warning.string}'"
                )

            elif isinstance(warning, StringNotUsedInContext):
                self.logger.warning(
                    f"While translating '{translation.source.object_repr}' into {translation.target_locale.get_display_name()}: The string '{warning.string}' is not used in context  '{warning.context}'"
                )

        try:
            # Don't attempt to save draft if the object isn't a page to avoid a CannotSaveDraftError
            translation.save_target(
                publish=not issubclass(
                    translation.source.specific_content_type.model_class(), Page
                )
            )

        except MissingRelatedObjectError:
            # Ignore error if there was a missing related object
            # In this case, the translations will just be updated but the page
            # wont be updated. When the related object is translated, the user
            # can manually hit the save draft/publish button to create/update
            # this page.
            self.logger.warning(
                f"Unable to translate '{translation.source.object_repr}' into {translation.target_locale.get_display_name()}: Missing related object"
            )

        except ValidationError as e:
            # Also ignore any validation errors
            self.logger.warning(
                f"Unable to translate '{translation.source.object_repr}' into {translation.target_locale.get_display_name()}: {repr(e)}"
            )

        self.db_project.internal_status = LanguageCloudProject.STATUS_IMPORTED
        self.db_project.save()
