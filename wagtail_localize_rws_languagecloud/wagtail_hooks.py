from django.urls import include, path, reverse
from django.utils.translation import gettext as _
from django.views.i18n import JavaScriptCatalog
from wagtail.admin.action_menu import ActionMenuItem
from wagtail.admin.menu import MenuItem
from wagtail.core import hooks
from wagtail.core.models import Locale, TranslatableMixin

from wagtail_localize.models import TranslationSource
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


class TranslatePageMenuItem(ActionMenuItem):
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
            if (
                request.user.has_perm("wagtail_localize.submit_translation")
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
def register_translate_page_menu_item():
    return TranslatePageMenuItem()


class SyncPageTranslationsMenuItem(ActionMenuItem):
    label = _("Sync translated pages")
    name = "action-sync-translations"
    icon_name = "repeat"

    def get_url(self, request, context):
        page = context["page"]
        source = TranslationSource.objects.get_for_instance_or_none(page)
        return reverse("wagtail_localize:update_translations", args=[source.id])

    def is_shown(self, request, context):
        view = context["view"]

        if view == "edit":
            page = context["page"]

            if (
                request.user.has_perm("wagtail_localize.submit_translation")
                and not page.is_root()
            ):
                # If the page is the source for translations, show "Sync translated pages" button
                source = TranslationSource.objects.get_for_instance_or_none(page)
                return (
                    source is not None
                    and source.translations.filter(enabled=True).exists()
                )

        return False


@hooks.register("register_page_action_menu_item")
def register_sync_translation_page_menu_item():
    return SyncPageTranslationsMenuItem()


class TranslateSnippetMenuItem(ActionMenuItem):
    label = _("Translate this snippet")
    name = "action-translate"
    icon_name = "site"

    def get_url(self, request, context):
        model = context["model"]
        snippet = context["instance"]
        return reverse(
            "wagtail_localize:submit_snippet_translation",
            args=[model._meta.app_label, model._meta.model_name, snippet.pk],
        )

    def is_shown(self, request, context):
        model = context["model"]
        view = context["view"]

        if view == "edit":
            if issubclass(model, TranslatableMixin) and request.user.has_perm(
                "wagtail_localize.submit_translation"
            ):
                snippet = context["instance"]

                # If there's at least one locale that we haven't translated into yet, show "Translate" button
                has_locale_to_translate_to = Locale.objects.exclude(
                    id__in=snippet.get_translations(inclusive=True).values_list(
                        "locale_id", flat=True
                    )
                ).exists()

                return has_locale_to_translate_to

        return False


@hooks.register("register_snippet_action_menu_item")
def register_translate_snippet_menu_item(*args):
    return TranslateSnippetMenuItem()


class SyncSnippetTranslationsMenuItem(ActionMenuItem):
    label = _("Sync translated snippets")
    name = "action-sync-translations"
    icon_name = "repeat"

    def get_url(self, request, context):
        instance = context["instance"]
        source = TranslationSource.objects.get_for_instance_or_none(instance)
        return reverse("wagtail_localize:update_translations", args=[source.id])

    def is_shown(self, request, context):
        model = context["model"]
        view = context["view"]

        if view == "edit":
            if issubclass(model, TranslatableMixin) and request.user.has_perm(
                "wagtail_localize.submit_translation"
            ):
                snippet = context["instance"]

                # If the snippet is the source for translations, show "Sync
                # translated snippets" button
                source = TranslationSource.objects.get_for_instance_or_none(snippet)
                return (
                    source is not None
                    and source.translations.filter(enabled=True).exists()
                )

        return False


@hooks.register("register_snippet_action_menu_item")
def register_sync_translation_snippet_menu_item(*args):
    return SyncSnippetTranslationsMenuItem()
