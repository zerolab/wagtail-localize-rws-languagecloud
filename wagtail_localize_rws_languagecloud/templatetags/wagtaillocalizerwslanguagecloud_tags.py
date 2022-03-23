import json

from django import template
from wagtail.core.models.i18n import Locale

from ..models import LanguageCloudFile


register = template.Library()


def get_translation_status(translation_key, locale_ids):
    """
    Returns a dict with the translation status of the page.
    """
    locale_id_combined_status_map = {}

    for locale_id in locale_ids:
        # Find the LanguageCloudFile for each locale
        try:
            lc_file = (
                LanguageCloudFile.objects.filter(
                    translation__source__object_id=translation_key,
                    translation__target_locale=locale_id,
                )
                .select_related("project", "translation")
                .prefetch_related("project__languagecloudfile_set")
                .latest("project__source_last_updated_at")
            )
        except LanguageCloudFile.DoesNotExist:
            continue

        if lc_file:
            locale_id_combined_status_map[locale_id] = lc_file.combined_status

    return locale_id_combined_status_map


@register.simple_tag(takes_context=True)
def language_cloud_statuses(context):
    page = context.get("parent_page") or context.get("page")

    if not page:
        return []

    locale_ids = page.get_translations(inclusive=True).values_list("locale", flat=True)

    return get_translation_status(page.translation_key, locale_ids).items()


@register.simple_tag(takes_context=True)
def hijack_wagtail_localize_edit_translation_props(context, props):
    data = json.loads(props)

    translation = context["translation"]

    locale_codes = [data["locale"]["code"]] + [
        translation["locale"]["code"] for translation in data["translations"]
    ]

    locale_code_id_map = {
        locale["language_code"]: locale["id"]
        for locale in Locale.objects.filter(language_code__in=locale_codes).values(
            "language_code", "id"
        )
    }

    statuses = get_translation_status(
        translation.source.object_id, locale_code_id_map.values()
    )

    # Override locale display names
    main_locale_id = locale_code_id_map[data["locale"]["code"]]
    if status := statuses.get(main_locale_id):
        data["locale"]["displayName"] = f"{data['locale']['displayName']} ({status})"

    for translation in data["translations"]:
        locale = translation["locale"]
        locale_id = locale_code_id_map[locale["code"]]

        if status := statuses.get(locale_id):
            locale["displayName"] = f"{locale['displayName']} ({status})"

    return json.dumps(data)
