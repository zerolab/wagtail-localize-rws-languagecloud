from django.db import models
from wagtail_localize.models import Translation, TranslationSource


class StatusModel(models.Model):
    STATUS_NEW = "new"
    STATUS_IMPORTED = "imported"
    STATUS_CHOICES = [(STATUS_NEW, STATUS_NEW), (STATUS_IMPORTED, STATUS_IMPORTED)]
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


class LanguageCloudFile(StatusModel):
    translation = models.ForeignKey(Translation, on_delete=models.CASCADE)
    project = models.ForeignKey(LanguageCloudProject, on_delete=models.CASCADE)
    lc_source_file_id = models.CharField(blank=True, max_length=255)
    create_attempts = models.IntegerField(default=0)

    class Meta:
        unique_together = [
            ("translation", "project"),
        ]

    @property
    def is_created(self):
        return self.lc_source_file_id != ""

    @property
    def is_failed(self):
        return self.lc_source_file_id == "" and self.create_attempts >= 3
