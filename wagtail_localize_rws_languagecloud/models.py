from django.db import models
from django.utils.translation import gettext_lazy
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
        return self.translation_source.get_source_instance()

    @property
    def languagecloud_frontend_url(self):
        if self.lc_project_id == "":
            return None
        return f"https://languagecloud.sdl.com/en/cp/detail?jobId={self.lc_project_id}"


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

        if self.project.lc_project_status == "archived":
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
