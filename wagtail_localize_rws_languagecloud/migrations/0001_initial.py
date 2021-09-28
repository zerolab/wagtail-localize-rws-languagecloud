# Generated by Django 3.1.13 on 2021-09-14 09:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('wagtail_localize', '0013_translationsource_schema_version'),
    ]

    operations = [
        migrations.CreateModel(
            name='LanguageCloudProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_last_updated_at', models.DateTimeField()),
                ('lc_project_id', models.CharField(blank=True, max_length=255)),
                ('lc_source_file_id', models.CharField(blank=True, max_length=255)),
                ('project_create_attempts', models.IntegerField(default=0)),
                ('source_file_create_attempts', models.IntegerField(default=0)),
                ('lc_project_status', models.CharField(blank=True, max_length=255)),
                ('internal_status', models.CharField(default='new', max_length=255)),
                ('translation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wagtail_localize.translation')),
            ],
            options={
                'unique_together': {('translation', 'source_last_updated_at')},
            },
        ),
    ]
