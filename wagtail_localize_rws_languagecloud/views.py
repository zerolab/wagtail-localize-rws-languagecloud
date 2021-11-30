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


class LanguageCloudReportFilterSet(WagtailFilterSet):
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
            ("created", gettext_lazy("Created")),
            ("inProgress", gettext_lazy("In Progress")),
            ("completed", gettext_lazy("Completed")),
            ("archived", gettext_lazy("Archived")),
        ],
    )
    translation__target_locale = django_filters.ModelChoiceFilter(
        label=gettext_lazy("Locale"),
        queryset=Locale.objects.all().exclude(id=Locale.get_default().id),
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
            .select_related("translation")
            .select_related("translation__source")
        )