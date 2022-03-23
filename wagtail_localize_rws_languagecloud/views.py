import django_filters

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy
from django.views.generic.base import TemplateView
from django.views.generic.detail import SingleObjectMixin
from django_filters.constants import EMPTY_VALUES
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.views.pages.utils import get_valid_next_url_from_request
from wagtail.admin.views.reports import ReportView
from wagtail.core.models import Locale

from wagtail_localize.models import TranslationSource
from wagtail_localize.views.update_translations import UpdateTranslationsView

from .models import LanguageCloudFile, LanguageCloudProject, LanguageCloudStatus


class SourceTitleFilter(django_filters.CharFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        return qs.filter(project__translation_source__object_repr__icontains=value)


class LanguageCloudProjectIDFilter(django_filters.CharFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        return qs.filter(project__lc_project_id__icontains=value)


class LanguageCloudReportFilterSet(WagtailFilterSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        We need to lazy load the queryset for this filter because our system checks
        load urls.py but run before migrations are applied.
        If we don't do this we will throw
        django.db.utils.OperationalError: no such table: wagtailcore_locale
        trying to apply migrations
        """
        self.filters[
            "translation__target_locale"
        ].queryset = Locale.objects.all().exclude(id=Locale.get_default().id)

    project__source_last_updated_at = django_filters.DateRangeFilter(
        label=gettext_lazy("Source last updated at")
    )
    project__source_title = SourceTitleFilter(label=gettext_lazy("Source title"))
    project__lc_project_id = LanguageCloudProjectIDFilter(
        label=gettext_lazy("LanguageCloud project ID")
    )
    project__lc_project_status = django_filters.ChoiceFilter(
        label=gettext_lazy("LanguageCloud project status"),
        choices=LanguageCloudStatus.choices,
    )
    translation__target_locale = django_filters.ModelChoiceFilter(
        label=gettext_lazy("Locale"),
        queryset=Locale.objects.none(),
    )


class LanguageCloudReportView(ReportView):
    template_name = "wagtail_localize_rws_languagecloud/admin/languagecloud_report.html"
    title = gettext_lazy("LanguageCloud")
    header_icon = "site"
    filterset_class = LanguageCloudReportFilterSet

    def get_queryset(self):
        return (
            LanguageCloudFile.objects.all()
            .select_related("project")
            .select_related("project__translation_source")
            .select_related("project__translation_source__object")
            .select_related("project__lc_settings")
            .select_related("project__lc_settings__user")
            .select_related("translation")
            .select_related("translation__source")
        )


default_update_translations_view = UpdateTranslationsView.as_view()


class UpdateTranslationsOverrideView(SingleObjectMixin, TemplateView):
    template_name = (
        "wagtail_localize_rws_languagecloud/admin/update_translations_override.html"
    )

    title = gettext_lazy("Update existing translations")

    def get_object(self):
        return get_object_or_404(
            TranslationSource, id=self.kwargs["translation_source_id"]
        )

    def get_title(self):
        return self.title

    def get_subtitle(self):
        return self.object.object_repr

    def dispatch(self, request, *args, translation_source_id, **kwargs):
        """
        Disallow updating translations if there are open LanguageCloud projects

        When there is a languagecloud project that is ongoing (not completed or
        archived) for the given translation source, do not allow editors to
        update the translations.

        This is to prevent conflicts between older and newer translations when
        a translation is imported from LanguageCloud.
        """

        self.object = self.get_object()

        has_open_projects = (
            LanguageCloudProject.objects.filter(
                translation_source=self.object,
            )
            .exclude(
                lc_project_status__in=[
                    LanguageCloudStatus.COMPLETED,
                    LanguageCloudStatus.ARCHIVED,
                ]
            )
            .exists()
        )

        if not has_open_projects:
            return default_update_translations_view(
                request, **kwargs, translation_source_id=translation_source_id
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["back_url"] = get_valid_next_url_from_request(self.request)
        return context
