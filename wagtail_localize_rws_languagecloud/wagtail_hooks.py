from django.urls import include, path, reverse
from django.utils.translation import gettext as _
from django.views.i18n import JavaScriptCatalog
from wagtail.admin.action_menu import ActionMenuItem
from wagtail.admin.menu import MenuItem
from wagtail.core import hooks
from wagtail.core.models.i18n import Locale

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
            "reports/languagecloud/",
            views.LanguageCloudReportView.as_view(),
            name="languagecloud_report",
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


class LanguageCloudReportMenuItem(MenuItem):
    def is_shown(self, request):
        return True


@hooks.register("register_reports_menu_item")
def register_languagecloud_report_menu_item():
    return LanguageCloudReportMenuItem(
        _("LanguageCloud"),
        reverse("wagtail_localize_rws_languagecloud:languagecloud_report"),
        icon_name="site",
        order=9001,
    )


class TranslateMenuItem(ActionMenuItem):
    label = _("Translate this page")
    name = "action-translate"
    icon_name = "site"

    def get_url(self, request, context):
        page = context["page"]
        return reverse("wagtail_localize:submit_page_translation", args=[page.pk])

    def is_shown(self, request, context):
        view = context["view"]

        if view == "edit":
            page = context["page"]
            page_perms = context["user_page_permissions"]
            if (
                page_perms.user.has_perm("wagtail_localize.submit_translation")
                and not page.is_root()
            ):
                # If there's at least one locale that we haven't translated into yet, show "Translate this page" button
                has_locale_to_translate_to = Locale.objects.exclude(
                    id__in=page.get_translations(inclusive=True)
                    .exclude(alias_of__isnull=False)
                    .values_list("locale_id", flat=True)
                ).exists()

                return has_locale_to_translate_to

        return False


@hooks.register("register_page_action_menu_item")
def register_translate_menu_item():
    return TranslateMenuItem()
