# Generated by Django 3.1.13 on 2021-11-18 10:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wagtail_localize_rws_languagecloud", "0003_auto_20211008_1132"),
    ]

    operations = [
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
