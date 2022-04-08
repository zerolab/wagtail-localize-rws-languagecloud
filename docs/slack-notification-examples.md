# Sending Slack Notifications

This example shows how we could use the `translation_imported` signal to send a simple Slack notification for every translated page or snippet.

```python
from django.utils.translation import gettext_lazy
from wagtail_localize.models import get_edit_url
from wagtail_localize_rws_languagecloud.signals import translation_imported
import requests

def post_slack_message(webhook_url, title, locale, edit_url):
    message = gettext_lazy(
        f"'{title}' has new translations for the '{locale}' locale. See the updated page at: {edit_url}."
    )

    values = {
        "text": message,
        "username": "Wagtail",
        "icon_emoji": ":rocket:",
    }

    return requests.post(webhook_url, values)

# Let everyone know when translations come back from RWS LanguageCloud
def send_to_slack(sender, instance, source_object, translated_object, **kwargs):
    webhook_url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"

    post_slack_message(
        webhook_url,
        source_object.title,
        translated_object.locale.get_display_name(),
        "https://www.mysite.com" + get_edit_url(translated_object)
    )

# Register a receiver
translation_imported.connect(send_to_slack)
```

Because the `translation_imported` signal receives the `sender`, `instance`, `source_object` and `translated_object` it is possible to use these to create quite rich integrations.

For example, we could send notifications to a different channel (webhook) for each target language

```python
def get_webhook_for_language(language_code):
    # Each slack webhook can post to one channel, so we define one webhook per language
    WEBHOOKS = {
        "fr-fr": "https://hooks.slack.com/services/T00000001/B00000001/XXXXXXXXXXXXXXXXXXXXXXXX",
        "es-mx": "https://hooks.slack.com/services/T00000002/B00000002/XXXXXXXXXXXXXXXXXXXXXXXX",
        # ...
    }
    return WEBHOOKS[language_code]

def send_to_slack(sender, instance, source_object, translated_object, **kwargs):
    webhook_url = get_webhook_for_language(translated_object.locale.language_code)

    post_slack_message(
        webhook_url,
        source_object.title,
        translated_object.locale.get_display_name(),
        "https://www.mysite.com" + get_edit_url(translated_object)
    )
```

or we could send notifications to a different channel (webhook) based on the page's position in the content tree:

```python
from wagtail.core.models import Page

def get_webhook_for_object(source_object):
    SNIPPET_WEBHOOK = "https://hooks.slack.com/services/T00000001/B00000001/XXXXXXXXXXXXXXXXXXXXXXXX"
    LEGAL_WEBHOOK = "https://hooks.slack.com/services/T00000002/B00000002/XXXXXXXXXXXXXXXXXXXXXXXX"
    DOCS_WEBHOOK = "https://hooks.slack.com/services/T00000003/B00000003/XXXXXXXXXXXXXXXXXXXXXXXX"
    GENERAL_WEBHOOK = "https://hooks.slack.com/services/T00000004/B00000004/XXXXXXXXXXXXXXXXXXXXXXXX"

    if not isinstance(source_object, Page):
        return SNIPPET_WEBHOOK

    if Page.objects.all().get(slug='legal') in source_object.get_ancestors():
        return LEGAL_WEBHOOK

    if Page.objects.all().get(slug='documentation') in source_object.get_ancestors():
        return DOCS_WEBHOOK

    return GENERAL_WEBHOOK

def send_to_slack(sender, instance, source_object, translated_object, **kwargs):
    webhook_url = get_webhook_for_object(source_object)

    post_slack_message(
        webhook_url,
        source_object.title,
        translated_object.locale.get_display_name(),
        "https://www.mysite.com" + get_edit_url(translated_object)
    )
```
