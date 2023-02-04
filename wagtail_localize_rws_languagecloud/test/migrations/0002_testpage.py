# Generated by Django 3.2.16 on 2023-01-18 23:26

from django.db import migrations, models
import django.db.models.deletion
import wagtail.core.fields


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailcore", "0066_collection_management_permissions"),
        ("wagtail_localize_rws_languagecloud_test", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TestPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "test_charfield",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=255,
                        null=True,
                        verbose_name="char field",
                    ),
                ),
                ("test_textfield", models.TextField(blank=True)),
                ("test_richtextfield", wagtail.core.fields.RichTextField(blank=True)),
                (
                    "test_synchronized_charfield",
                    models.CharField(blank=True, max_length=255),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page",),
        ),
    ]
