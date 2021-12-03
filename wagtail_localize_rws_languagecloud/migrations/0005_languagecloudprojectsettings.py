from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("wagtail_localize", "0015_translationcontext_field_path"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("wagtail_localize_rws_languagecloud", "0004_add_status_change_order"),
    ]

    operations = [
        migrations.CreateModel(
            name="LanguageCloudProjectSettings",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("source_last_updated_at", models.DateTimeField(editable=False)),
                ("name", models.CharField(max_length=255)),
                ("description", models.CharField(max_length=255, blank=True)),
                ("due_date", models.DateTimeField()),
                (
                    "template_id",
                    models.CharField(max_length=255, verbose_name="Project template"),
                ),
                (
                    "lc_project",
                    models.OneToOneField(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lc_settings",
                        to="wagtail_localize_rws_languagecloud.LanguageCloudProject",
                    ),
                ),
                (
                    "translation_source",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="wagtail_localize.TranslationSource",
                    ),
                ),
                (
                    "translations",
                    models.ManyToManyField(
                        editable=False, to="wagtail_localize.Translation"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("translation_source", "source_last_updated_at")},
            },
        ),
    ]
