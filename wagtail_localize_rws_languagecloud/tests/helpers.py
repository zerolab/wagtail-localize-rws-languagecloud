import datetime

import polib

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from wagtail.core.models import Page

from wagtail_localize.models import TranslationSource
from wagtail_localize.test.models import TestPage
from wagtail_localize_rws_languagecloud.models import LanguageCloudProjectSettings
from wagtail_localize_rws_languagecloud.test.models import ExampleSnippet


User = get_user_model()


def create_test_page(**kwargs):
    parent = kwargs.pop("parent", None) or Page.objects.get(slug="home")
    page = parent.add_child(instance=TestPage(**kwargs))
    revision = page.save_revision()
    revision.publish()
    source, created = TranslationSource.get_or_create_from_instance(page)
    return page, source


def create_test_po(entries):
    po = polib.POFile(wrapwidth=200)
    po.metadata = {
        "POT-Creation-Date": str(datetime.datetime.utcnow()),
        "MIME-Version": "1.0",
        "Content-Type": "text/html; charset=utf-8",
    }

    for entry in entries:
        po.append(polib.POEntry(msgctxt=entry[0], msgid=entry[1], msgstr=entry[2]))

    return po


def create_test_project_settings(translation_source, translations, **settings_data):
    default_project_data = {
        "name": "my project",
        "description": "test project",
        "due_date": timezone.now() + datetime.timedelta(days=1),
        "template_id": "123",
    }
    data = {**default_project_data, **settings_data}
    return LanguageCloudProjectSettings.get_or_create_from_source_and_translation_data(
        translation_source, translations, **data
    )


def create_editor_user(username="testeditor"):
    user = User.objects.create(
        username=username,
        first_name="Test",
        last_name="Editor",
    )

    user.groups.add(Group.objects.get(name="Editors"))

    # Add snippet permissions
    user.user_permissions.add(
        *Permission.objects.filter(
            codename__in=[
                "add_examplesnippet",
                "change_examplesnippet",
                "delete_examplesnippet",
            ]
        )
    )

    return user


def create_snippet(name="test snippet"):
    snippet = ExampleSnippet.objects.create(name=name)
    source, created = TranslationSource.get_or_create_from_instance(snippet)
    return snippet, source
