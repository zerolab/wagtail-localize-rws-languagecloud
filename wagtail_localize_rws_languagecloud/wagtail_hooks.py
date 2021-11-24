from django.urls import include, path, reverse
from django.utils.translation import gettext as _
from django.views.i18n import JavaScriptCatalog
from wagtail.admin.menu import MenuItem
from wagtail.core import hooks

from wagtail_localize_rws_languagecloud import views


@hooks.register("register_admin_urls")
def register_admin_urls():
    urls = [
        path(
            "jsi18n/",
            JavaScriptCatalog.as_view(packages=["wagtail_localize_rws_languagecloud"]),
            name="javascript_catalog",
        ),
        path(
            "reports/languagecloud_projects/",
            views.LanguageCloudProjectReportView.as_view(),
            name="languagecloud_projects_report",
        ),
    ]

    return [
        path(
            "localize_rws_languagecloud/",
            include(
                (urls, "wagtail_localize_rws_languagecloud"),
                namespace="wagtail_localize_rws_languagecloud",
            ),
        )
    ]


class LanguageCloudProjectsReportMenuItem(MenuItem):
    def is_shown(self, request):
        return True


@hooks.register("register_reports_menu_item")
def register_ab_testing_report_menu_item():
    return LanguageCloudProjectsReportMenuItem(
        _("LanguageCloud Projects"),
        reverse("wagtail_localize_rws_languagecloud:languagecloud_projects_report"),
        icon_name="site",
        order=9001,
    )
