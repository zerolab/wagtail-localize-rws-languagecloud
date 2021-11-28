import datetime
import logging

from django import forms
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from requests import RequestException
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.models import get_object_usage
from wagtail.core.models import Page

from wagtail_localize.models import TranslationSource
from wagtail_localize_rws_languagecloud.rws_client import ApiClient


logger = logging.getLogger(__name__)


class LanguageCloudProjectSettingsForm(WagtailAdminModelForm):
    class Meta:
        exclude = (
            "translation_source",
            "source_last_updated_at",
            "translations",
            "lc_project",
        )

    def __init__(
        self,
        data=None,
        files=None,
        instance=None,
        prefix=None,
        source_object_instance=None,
        user=None,
        **kwargs,
    ):
        super().__init__(data, files, instance=instance, prefix=prefix, **kwargs)

        self.fields["user"].initial = user
        self.fields["user"].widget = forms.HiddenInput()

        self.fields["name"].initial = self._get_default_project_name(
            source_object_instance
        )
        self.fields["description"].initial = self._get_default_project_description(
            source_object_instance
        )
        self.fields["due_date"].initial = self._get_default_due_date()

        self.fields["template_id"] = forms.ChoiceField(
            label=_("Template"),
            choices=self._get_project_template_choices(),
            initial=self._get_default_project_template_id(),
            widget=forms.Select(),
        )

    def clean_due_date(self):
        due_date = self.cleaned_data["due_date"]
        if due_date.timestamp() < datetime.datetime.utcnow().timestamp():
            raise forms.ValidationError(
                _("Due date cannot be in the past."), code="invalid"
            )

        return due_date

    def _get_default_project_name(self, source_object):
        if isinstance(source_object, TranslationSource):
            object_name = str(source_object.get_source_instance())
        else:
            object_name = str(source_object)

        prefix = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get("PROJECT_PREFIX", "")
        now = timezone.now()
        return f"{prefix}{object_name}_{now:%Y-%m-%d}"

    def _get_default_due_date(self):
        now = timezone.now()
        delta = settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get(
            "DUE_BY_DELTA", datetime.timedelta(days=7)
        )
        return now + delta

    def _get_default_project_description(self, source_object):
        description = ""

        if source_object is None:
            return description

        the_source_object = source_object
        if isinstance(source_object, TranslationSource):
            the_source_object = source_object.get_source_instance()

        if isinstance(the_source_object, Page):
            description = description + (the_source_object.full_url or "")
            return description

        pages = get_object_usage(the_source_object)
        # This is only contextual information. If a snippet appears in hundreds of
        # pages we probably don't need to spam all of them. Just take the first 5.
        urls = [(page.full_url or "") for page in pages.all()[:5]]
        description = description + "\n".join(urls)

        return description

    def _get_default_project_template_id(self):
        return settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD.get("TEMPLATE_ID")

    def _get_project_templates(self):
        client = ApiClient(logger)
        try:
            client.authenticate()
            templates = client.get_project_templates(should_sleep=False)
        except RequestException:
            templates = {}
        return templates

    def _get_project_template_choices(self):
        project_templates = self._get_project_templates()
        if project_templates.get("itemCount", 0) > 0:
            return [
                (template["id"], template["name"])
                for template in project_templates["items"]
            ]

        return [(self._get_default_project_template_id(), _("Default template"))]
