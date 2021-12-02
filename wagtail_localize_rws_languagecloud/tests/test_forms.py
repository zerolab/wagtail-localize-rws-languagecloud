import datetime
import logging

from unittest import mock

import pytz

from django import forms
from django.test import TestCase, override_settings
from freezegun import freeze_time
from wagtail.admin.edit_handlers import get_form_for_model
from wagtail.tests.utils import WagtailTestUtils

from wagtail_localize_rws_languagecloud.forms import LanguageCloudProjectSettingsForm
from wagtail_localize_rws_languagecloud.models import LanguageCloudProjectSettings

from .helpers import create_test_page


@override_settings(WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={"TEMPLATE_ID": "c0ffee"})
@freeze_time("2018-02-02 12:00:01")
class TestProjectSettingsForm(TestCase, WagtailTestUtils):
    def setUp(self):
        self.test_page, source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="Some test translatable content",
        )

        self.form_class = get_form_for_model(
            LanguageCloudProjectSettings,
            LanguageCloudProjectSettingsForm,
        )
        self.form = self._get_form(source_object_instance=self.test_page)

        self.logger = logging.getLogger(__name__)
        logging.disable()  # supress log output under test

    @mock.patch(
        "wagtail_localize_rws_languagecloud.forms.LanguageCloudProjectSettingsForm._get_project_templates",
        new=mock.MagicMock(
            return_value={
                "items": [{"id": "123456", "name": "Project X"}],
                "itemCount": 1,
            }
        ),
    )
    def _get_form(self, data=None, source_object_instance=None):
        if data:
            return self.form_class(data, source_object_instance=source_object_instance)
        return self.form_class(source_object_instance=source_object_instance)

    def test_get_project_name_without_custom_prefix(self):
        self.assertEqual(
            self.form.default_project_name_prefix,
            "2018-02-02_",
        )

    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={"PROJECT_PREFIX": "Website_"},
    )
    def test_get_project_name_with_custom_prefix(self):
        self.assertEqual(
            self.form.default_project_name_prefix,
            "Website_2018-02-02_",
        )

    def test_get_project_due_date_without_custom_delta(self):
        self.assertEqual(
            self.form.default_due_date,
            datetime.datetime(2018, 2, 9, 12, 0, 1, tzinfo=pytz.utc),
        )

    @override_settings(
        WAGTAILLOCALIZE_RWS_LANGUAGECLOUD={"DUE_BY_DELTA": datetime.timedelta(days=14)},
    )
    def test_get_project_due_date_with_custom_delta(self):
        self.assertEqual(
            self.form.default_due_date,
            datetime.datetime(2018, 2, 16, 12, 0, 1, tzinfo=pytz.utc),
        )

    def test_get_default_project_description(self):
        self.assertEqual(
            self.form._get_default_project_description(self.test_page),
            self.test_page.full_url,
        )

    def test_default_project_description_has_the_user_name_when_passed(self):
        user = self.create_test_user()
        self.assertIn(
            "test@email.com",
            self.form._get_default_project_description(self.test_page, user=user),
        )
        user.first_name = "John"
        user.last_name = "Doe"
        user.save()
        self.assertIn(
            "John Doe",
            self.form._get_default_project_description(self.test_page, user=user),
        )

    def test_get_default_project_template(self):
        self.assertEqual(self.form.default_project_template_id, "c0ffee")

    def test_user_field_is_hidden(self):
        self.assertIsInstance(self.form.fields["user"].widget, forms.HiddenInput)

    def test_template_id_choices(self):
        self.assertEqual(len(self.form.fields["template_id"].choices), 1)
        self.assertListEqual(
            self.form.fields["template_id"].choices, [("123456", "Project X")]
        )

    def test_due_date_in_the_past_raises_validation_error(self):
        data = {
            "name": "The project",
            "template_id": "123456",
            "due_date": datetime.datetime(2018, 2, 1, 12, 0, 1, tzinfo=pytz.utc),
        }
        form = self._get_form(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("due_date", form.errors)
        self.assertIn("Due date cannot be in the past.", form.errors["due_date"])
