from django.db import models
from wagtail_localize.models import Translation


class LanguageCloudProject(models.Model):
    STATUS_NEW = "new"
    STATUS_IMPORTED = "imported"
    STATUS_CHOICES = [(STATUS_NEW, STATUS_NEW), (STATUS_IMPORTED, STATUS_IMPORTED)]

    translation = models.ForeignKey(Translation, on_delete=models.CASCADE)
    source_last_updated_at = models.DateTimeField()
    lc_project_id = models.CharField(blank=True, max_length=255)
    lc_source_file_id = models.CharField(blank=True, max_length=255)
    project_create_attempts = models.IntegerField(default=0)
    source_file_create_attempts = models.IntegerField(default=0)
    """
    Expected values are
    created, inProgress, completed, archived
    or empty string
    """
    lc_project_status = models.CharField(blank=True, max_length=255)
    internal_status = models.CharField(
        blank=False,
        max_length=255,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )

    class Meta:
        unique_together = [
            ("translation", "source_last_updated_at"),
        ]

    @property
    def project_failed(self):
        return self.lc_project_id == "" and self.project_create_attempts >= 3

    @property
    def file_failed(self):
        return self.lc_source_file_id == "" and self.source_file_create_attempts >= 3
