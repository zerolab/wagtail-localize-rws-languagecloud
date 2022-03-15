from django.conf import settings
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy
from wagtail.core.models import Page

from wagtail_localize.components import register_translation_component
from wagtail_localize.models import Translation, TranslationSource
from wagtail_localize_rws_languagecloud.forms import LanguageCloudProjectSettingsForm


class StatusModel(models.Model):
    STATUS_NEW = "new"
    STATUS_IMPORTED = "imported"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_NEW, STATUS_NEW),
        (STATUS_IMPORTED, STATUS_IMPORTED),
        (STATUS_ERROR, STATUS_ERROR),
    ]
    internal_status = models.CharField(
        blank=False,
        max_length=255,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )

    class Meta:
        abstract = True


class LanguageCloudStatus(models.TextChoices):
    CREATED = "created", gettext_lazy("Created")
    IN_PROGRESS = "inProgress", gettext_lazy("In Progress")
    COMPLETED = "completed", gettext_lazy("Completed")
    ARCHIVED = "archived", gettext_lazy("Archived")


class LanguageCloudProject(StatusModel):
    translation_source = models.ForeignKey(TranslationSource, on_delete=models.CASCADE)
    source_last_updated_at = models.DateTimeField()
    lc_project_id = models.CharField(blank=True, max_length=255)
    create_attempts = models.IntegerField(default=0)
    """
    Expected values are
    created, inProgress, completed, archived
    or empty string
    """
    lc_project_status = models.CharField(blank=True, max_length=255)

    class Meta:
        unique_together = [
            ("translation_source", "source_last_updated_at"),
        ]
        ordering = ["-source_last_updated_at"]

    @property
    def all_files_imported(self):
        children_imported = [
            f.internal_status == LanguageCloudFile.STATUS_IMPORTED
            for f in self.languagecloudfile_set.all()
        ]
        return len(children_imported) > 0 and False not in children_imported

    @property
    def is_created(self):
        # True if project AND all source files created in LanguageCloud
        children_created = [f.is_created for f in self.languagecloudfile_set.all()]
        return (
            self.lc_project_id != ""
            and len(children_created) > 0
            and False not in children_created
        )

    @property
    def translation_source_object(self):
        return self.translation_source.get_source_instance()

    @property
    def languagecloud_frontend_url(self):
        if self.lc_project_id == "":
            return None
        return f"https://languagecloud.sdl.com/en/cp/detail?jobId={self.lc_project_id}"

    @property
    def lc_project_status_label(self):
        if self.lc_project_status in LanguageCloudStatus:
            return LanguageCloudStatus(self.lc_project_status).label

        return self.lc_project_status


class LanguageCloudFile(StatusModel):
    translation = models.ForeignKey(Translation, on_delete=models.CASCADE)
    project = models.ForeignKey(LanguageCloudProject, on_delete=models.CASCADE)
    lc_source_file_id = models.CharField(blank=True, max_length=255)
    create_attempts = models.IntegerField(default=0)

    class Meta:
        unique_together = [
            ("translation", "project"),
        ]
        ordering = ["-project__source_last_updated_at"]

    @property
    def is_created(self):
        return self.lc_source_file_id != ""

    @property
    def is_failed(self):
        return self.lc_source_file_id == "" and self.create_attempts >= 3

    @property
    def instance_is_published(self):
        instance = self.translation.get_target_instance()
        if not isinstance(instance, Page):
            return True
        return not instance.has_unpublished_changes

    @property
    def combined_status(self):
        if self.project.lc_project_id == "" and self.project.create_attempts >= 3:
            return gettext_lazy("Project creation failed")

        if not self.translation.enabled:
            return gettext_lazy("Translations disabled in Wagtail")

        if self.is_failed:
            return gettext_lazy("PO File upload failed")

        if not self.project.is_created:
            return gettext_lazy("Request created")

        if self.project.lc_project_status == LanguageCloudStatus.ARCHIVED:
            return gettext_lazy("LanguageCloud project archived")

        if (
            self.internal_status == LanguageCloudFile.STATUS_IMPORTED
            and not self.instance_is_published
        ):
            return gettext_lazy("Translations ready for review")

        if (
            self.internal_status == LanguageCloudFile.STATUS_IMPORTED
            and self.instance_is_published
        ):
            return gettext_lazy("Translations published")

        if self.internal_status == LanguageCloudFile.STATUS_ERROR:
            return gettext_lazy("Error importing PO file")

        if self.project.is_created:
            return gettext_lazy("Translations happening in LanguageCloud")

        return gettext_lazy("Unknown")


@register_translation_component(
    heading=gettext_lazy("Send translation to RWS Language Cloud"),
    help_text=gettext_lazy(
        "You can modify RWS Language Cloud default project details such name, due date or project option"
    ),
    enable_text=gettext_lazy("Send to RWS Cloud"),
    disable_text=gettext_lazy("Do not send to RWS Cloud"),
)
class LanguageCloudProjectSettings(models.Model):
    base_form_class = LanguageCloudProjectSettingsForm

    translation_source = models.ForeignKey(
        TranslationSource, on_delete=models.CASCADE, editable=False
    )
    source_last_updated_at = models.DateTimeField(editable=False)
    translations = models.ManyToManyField(Translation, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="+",
    )

    # will be set on cron
    lc_project = models.OneToOneField(
        LanguageCloudProject,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        editable=False,
        related_name="lc_settings",
    )

    # the editable fields
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    due_date = models.DateTimeField()
    template_id = models.CharField(
        max_length=255, verbose_name=gettext_lazy("Project template")
    )

    class Meta:
        unique_together = [
            ("translation_source", "source_last_updated_at"),
        ]

    def __str__(self):
        return f"LanguageCloudProjectSettings ({self.pk}): {self.name}"

    @classmethod
    def get_or_create_from_source_and_translation_data(
        cls, translation_source, translations, **kwargs
    ):
        name_prefix = kwargs.get("name", "")
        glue = "" if name_prefix.endswith("_") else "_"
        kwargs["name"] = (
            name_prefix + glue + str(translation_source.get_source_instance())
        )
        project_settings, created = LanguageCloudProjectSettings.objects.get_or_create(
            translation_source=translation_source,
            source_last_updated_at=translation_source.last_updated_at,
            **kwargs,
        )

        if created:
            project_settings.translations.add(*translations)

        return project_settings, created

    @property
    def formatted_due_date(self):
        return self.due_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    @cached_property
    def source_language_code(self):
        return self.translation_source.locale.language_code

    @cached_property
    def target_language_codes(self):
        return [
            translation.target_locale.language_code
            for translation in self.translations.all().select_related("target_locale")
        ]
