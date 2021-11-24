from django.db import migrations, models


def save_all_languagecloud_files(apps, schema_editor):
    # Set combined_status = "Unknown"
    # on every LanguageCloudFile record to start with
    # they'll all get updated the next time we run sync_rws
    LanguageCloudFile = apps.get_model(
        "wagtail_localize_rws_languagecloud", "LanguageCloudFile"
    )
    for file_ in LanguageCloudFile.objects.all():
        file_.combined_status = "UNKNOWN"
        file_.save()


class Migration(migrations.Migration):

    dependencies = [
        ("wagtail_localize_rws_languagecloud", "0005_auto_20211124_0956"),
    ]

    operations = [
        migrations.AddField(
            model_name="languagecloudfile",
            name="combined_status",
            field=models.CharField(
                choices=[
                    ("PROJECT_FAILED", "Project creation failed"),
                    ("TRANSLATIONS_DISABLED", "Translations disabled in Wagtail"),
                    ("PO_EXPORT_FAILED", "PO File upload failed"),
                    ("NEW", "Request created"),
                    ("PROJECT_ARCHIVED", "LanguageCloud project archived"),
                    ("TRANSLATIONS_READY", "Translations ready for review"),
                    ("TRANSLATIONS_PUBLISHED", "Translations published"),
                    ("PO_IMPORT_FAILED", "Error importing PO file"),
                    ("PROJECT_IN_PROGRESS", "Translations happening in LanguageCloud"),
                    ("UNKNOWN", "Unknown"),
                ],
                default="UNKNOWN",
                max_length=255,
            ),
        ),
        migrations.RunPython(save_all_languagecloud_files, migrations.RunPython.noop),
    ]
