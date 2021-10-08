import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wagtail_localize", "0013_translationsource_schema_version"),
        ("wagtail_localize_rws_languagecloud", "0002_auto_20210914_1406"),
    ]

    operations = [
        migrations.RunSQL(
            "DELETE FROM wagtail_localize_rws_languagecloud_languagecloudproject;"
        ),
        migrations.RenameField(
            model_name="languagecloudproject",
            old_name="project_create_attempts",
            new_name="create_attempts",
        ),
        migrations.AddField(
            model_name="languagecloudproject",
            name="translation_source",
            field=models.ForeignKey(
                null=False,
                on_delete=django.db.models.deletion.CASCADE,
                to="wagtail_localize.translationsource",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="languagecloudproject",
            unique_together={("translation_source", "source_last_updated_at")},
        ),
        migrations.RemoveField(
            model_name="languagecloudproject",
            name="lc_source_file_id",
        ),
        migrations.RemoveField(
            model_name="languagecloudproject",
            name="source_file_create_attempts",
        ),
        migrations.RemoveField(
            model_name="languagecloudproject",
            name="translation",
        ),
        migrations.CreateModel(
            name="LanguageCloudFile",
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
                (
                    "internal_status",
                    models.CharField(
                        choices=[("new", "new"), ("imported", "imported")],
                        default="new",
                        max_length=255,
                    ),
                ),
                ("lc_source_file_id", models.CharField(blank=True, max_length=255)),
                ("create_attempts", models.IntegerField(default=0)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="wagtail_localize_rws_languagecloud.languagecloudproject",
                    ),
                ),
                (
                    "translation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="wagtail_localize.translation",
                    ),
                ),
            ],
            options={
                "unique_together": {("translation", "project")},
            },
        ),
    ]
