from django import template

from ..models import LanguageCloudFile


register = template.Library()


@register.simple_tag(takes_context=True)
def language_cloud_statuses(context):
    page = context.get("parent_page") or context.get("page")

    if not page:
        return []

    locale_ids = page.get_translations(inclusive=True).values_list("locale", flat=True)

    locale_id_combined_status_map = {}

    for locale_id in locale_ids:
        # Find the LanguageCloudFile for each locale
        try:
            lc_file = (
                LanguageCloudFile.objects.filter(
                    translation__source__object_id=page.translation_key,
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

    return locale_id_combined_status_map.items()
