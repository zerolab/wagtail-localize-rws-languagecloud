from django.apps import apps
from django.conf import settings
from django.core.checks import Error, register


@register()
def languagecloud_settings_check(app_configs, **kwargs):
    errors = []

    if (
        app_configs is not None
        and apps.get_app_config("wagtail_localize_rws_languagecloud") not in app_configs
    ):
        return errors

    try:
        getattr(settings, "WAGTAILLOCALIZE_RWS_LANGUAGECLOUD")
    except AttributeError:
        errors.append(
            Error(
                "Required setting WAGTAILLOCALIZE_RWS_LANGUAGECLOUD not found",
                id="wagtail_localize_rws_languagecloud.E001",
                obj="wagtail_localize_rws_languagecloud",
            )
        )
        return errors

    required_settings = [
        "CLIENT_ID",
        "CLIENT_SECRET",
        "ACCOUNT_ID",
        "TEMPLATE_ID",
        "LOCATION_ID"
    ]
    for setting in required_settings:
        if setting not in settings.WAGTAILLOCALIZE_RWS_LANGUAGECLOUD:
            errors.append(
                Error(
                    f"Required setting WAGTAILLOCALIZE_RWS_LANGUAGECLOUD['{setting}'] not found",
                    id="wagtail_localize_rws_languagecloud.E002",
                    obj="wagtail_localize_rws_languagecloud",
                )
            )

    return errors
