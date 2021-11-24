from django.db import models, transaction
from wagtail.core.models import Page

from wagtail_localize.models import Translation, TranslationSource


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
    def is_failed(self):
        # True if project OR any source file failed >= 3 times
        return (self.lc_project_id == "" and self.create_attempts >= 3) or (
            True in [f.is_failed for f in self.languagecloudfile_set.all()]
        )

    @property
    def translation_source_object(self):
        return self.translation_source.object.get_instance(
            self.translation_source.locale
        )

    @property
    def languagecloud_frontend_url(self):
        if self.lc_project_id == "":
            return None
        return f"https://languagecloud.sdl.com/en/cp/detail?jobId={self.lc_project_id}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for file_ in self.languagecloudfile_set.all():
            file_.save()


class LanguageCloudFile(StatusModel):
    translation = models.ForeignKey(Translation, on_delete=models.CASCADE)
    project = models.ForeignKey(LanguageCloudProject, on_delete=models.CASCADE)
    lc_source_file_id = models.CharField(blank=True, max_length=255)
    create_attempts = models.IntegerField(default=0)

    COMBINED_STATUS_PROJECT_FAILED = "PROJECT_FAILED"
    COMBINED_STATUS_TRANSLATIONS_DISABLED = "TRANSLATIONS_DISABLED"
    COMBINED_STATUS_PO_EXPORT_FAILED = "PO_EXPORT_FAILED"
    COMBINED_STATUS_NEW = "NEW"
    COMBINED_STATUS_PROJECT_ARCHIVED = "PROJECT_ARCHIVED"
    COMBINED_STATUS_TRANSLATIONS_READY = "TRANSLATIONS_READY"
    COMBINED_STATUS_TRANSLATIONS_PUBLISHED = "TRANSLATIONS_PUBLISHED"
    COMBINED_STATUS_PO_IMPORT_FAILED = "PO_IMPORT_FAILED"
    COMBINED_STATUS_PROJECT_IN_PROGRESS = "PROJECT_IN_PROGRESS"
    COMBINED_STATUS_UNKNOWN = "UNKNOWN"
    COMBINED_STATUS_CHOICES = [
        (COMBINED_STATUS_PROJECT_FAILED, "Project creation failed"),
        (COMBINED_STATUS_TRANSLATIONS_DISABLED, "Translations disabled in Wagtail"),
        (COMBINED_STATUS_PO_EXPORT_FAILED, "PO File upload failed"),
        (COMBINED_STATUS_NEW, "Request created"),
        (COMBINED_STATUS_PROJECT_ARCHIVED, "LanguageCloud project archived"),
        (COMBINED_STATUS_TRANSLATIONS_READY, "Translations ready for review"),
        (COMBINED_STATUS_TRANSLATIONS_PUBLISHED, "Translations published"),
        (COMBINED_STATUS_PO_IMPORT_FAILED, "Error importing PO file"),
        (
            COMBINED_STATUS_PROJECT_IN_PROGRESS,
            "Translations happening in LanguageCloud",
        ),
        (COMBINED_STATUS_UNKNOWN, "Unknown"),
    ]
    combined_status = models.CharField(
        blank=False,
        max_length=255,
        choices=COMBINED_STATUS_CHOICES,
        default=COMBINED_STATUS_UNKNOWN,
    )

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
        instance = self.translation.source.get_translated_instance(
            self.translation.target_locale
        )
        if not isinstance(instance, Page):
            return True
        return not instance.has_unpublished_changes

    def get_combined_status(self):
        if self.project.lc_project_id == "" and self.project.create_attempts >= 3:
            return self.COMBINED_STATUS_PROJECT_FAILED

        if not self.translation.enabled:
            return self.COMBINED_STATUS_TRANSLATIONS_DISABLED

        if self.is_failed:
            return self.COMBINED_STATUS_PO_EXPORT_FAILED

        if not self.project.is_created:
            return self.COMBINED_STATUS_NEW

        if self.project.lc_project_status == "archived":
            return self.COMBINED_STATUS_PROJECT_ARCHIVED

        if (
            self.internal_status == LanguageCloudFile.STATUS_IMPORTED
            and not self.instance_is_published
        ):
            return self.COMBINED_STATUS_TRANSLATIONS_READY

        if (
            self.internal_status == LanguageCloudFile.STATUS_IMPORTED
            and self.instance_is_published
        ):
            return self.COMBINED_STATUS_TRANSLATIONS_PUBLISHED

        if self.internal_status == LanguageCloudFile.STATUS_ERROR:
            return self.COMBINED_STATUS_PO_IMPORT_FAILED

        if self.project.is_created:
            return self.COMBINED_STATUS_PROJECT_IN_PROGRESS

        return self.COMBINED_STATUS_UNKNOWN

    @property
    def combined_status_for_display(self):
        lookup = dict(self.COMBINED_STATUS_CHOICES)
        return lookup[self.combined_status]

    def save(self, *args, **kwargs):
        self.combined_status = self.get_combined_status()
        super().save(*args, **kwargs)
