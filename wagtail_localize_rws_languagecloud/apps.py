from django.apps import AppConfig


class WagtailLocalizeRwsLanguageCloudAppConfig(AppConfig):
    label = "wagtail_localize_rws_languagecloud"
    name = "wagtail_localize_rws_languagecloud"
    verbose_name = "Wagtail Localize RWS LanguageCloud"
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        import wagtail_localize_rws_languagecloud.checks  # noqa: F401
