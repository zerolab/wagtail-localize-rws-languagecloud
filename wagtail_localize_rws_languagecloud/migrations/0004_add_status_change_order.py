# Generated by Django 3.1.13 on 2021-12-01 10:43

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wagtail_localize_rws_languagecloud", "0003_auto_20211008_1132"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="languagecloudfile",
            options={"ordering": ["-project__source_last_updated_at"]},
        ),
        migrations.AlterModelOptions(
            name="languagecloudproject",
            options={"ordering": ["-source_last_updated_at"]},
        ),
        migrations.AlterField(
            model_name="languagecloudfile",
            name="internal_status",
            field=models.CharField(
                choices=[("new", "new"), ("imported", "imported"), ("error", "error")],
                default="new",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="languagecloudproject",
            name="internal_status",
            field=models.CharField(
                choices=[("new", "new"), ("imported", "imported"), ("error", "error")],
                default="new",
                max_length=255,
            ),
        ),
    ]
