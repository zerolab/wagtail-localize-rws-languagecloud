import django_filters

from django.utils.translation import gettext_lazy
from django_filters.constants import EMPTY_VALUES
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.views.reports import ReportView
from wagtail.core.models import Locale

from .models import LanguageCloudFile


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


class LanguageCloudProjectReportFilterSet(WagtailFilterSet):
    project__source_last_updated_at = django_filters.DateRangeFilter(
        label=gettext_lazy("Source last updated at")
    )
    project__source_title = SourceTitleFilter(label=gettext_lazy("Source title"))
    project__lc_project_id = LanguageCloudProjectIDFilter(
        label=gettext_lazy("LanguageCloud project ID")
    )
    project__lc_project_status = django_filters.ChoiceFilter(
        label=gettext_lazy("LanguageCloud project status"),
        choices=[
            ("created", "created"),
            ("inProgress", "inProgress"),
            ("completed", "completed"),
            ("archived", "archived"),
        ],
    )
    translation__target_locale = django_filters.ModelChoiceFilter(
        label=gettext_lazy("Locale"),
        queryset=Locale.objects.all(),
    )


class LanguageCloudProjectReportView(ReportView):
    template_name = (
        "wagtail_localize_rws_languagecloud/admin/languagecloud_projects_report.html"
    )
    title = gettext_lazy("LanguageCloud Projects")
    header_icon = "site"
    filterset_class = LanguageCloudProjectReportFilterSet

    def get_queryset(self):
        return (
            LanguageCloudFile.objects.all()
            .prefetch_related("project")
            .prefetch_related("project__translation_source")
            .prefetch_related("project__translation_source__object")
            .prefetch_related("translation")
            .prefetch_related("translation__source")
        )
