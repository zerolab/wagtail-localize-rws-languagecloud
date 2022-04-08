from django.conf import settings
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.utils.translation import gettext_lazy
from wagtail.admin.mail import send_mail


User = get_user_model()


def get_full_url(url):
    if hasattr(settings, "BASE_URL") and url.startswith("/"):
        url = settings.BASE_URL + url
    return url


# sync_rws command emails
def send_sync_rws_emails(translation):
    subject, body = compose_sync_rws_email(translation)
    recipients = get_recipients()
    for recipient in recipients:
        send_mail(subject, body, [recipient])


def compose_sync_rws_email(translation):
    subject = gettext_lazy("Translated content ready for review")
    body = gettext_lazy(
        "Translated content for '%(instance)s' is ready for review at: %(edit_url)s"
    ) % {
        "instance": str(translation.get_target_instance()),
        "edit_url": get_full_url(translation.get_target_instance_edit_url()),
    }
    return subject, body


# update_translated_pages emails
def send_update_translated_pages_emails(all_pages, updated_pages, skipped_pages):
    """Notifies users that translated pages have been synced.

    Args:
        all_pages (List[Tuple[int, str]]): List of all pages considered.
        updated_pages (List[Tuple[int, str]]): List of updated pages.
        skipped_pages (List[Tuple[int, str]]): List of pages that were not updated.
    """
    subject, body = compose_update_translated_pages_email(
        all_pages, updated_pages, skipped_pages
    )
    recipients = get_recipients()
    for recipient in recipients:
        send_mail(subject, body, [recipient])


UPDATE_TRANSLATED_PAGES_EMAIL_TEMPLATE = Template(
    """{% load i18n %}
{% blocktrans with total_count=all_pages|length updated_count=updated_pages|length skipped_count=skipped_pages|length %}
Found {{ total_count }} page(s) with stale translations, of which {{ updated_count }} were synced and {{ skipped_count }} were skipped.{% endblocktrans %}

{% trans "Pages that were synced:" %}

{% for page_pk, page_title in updated_pages %}{{ forloop.counter }}. {{ page_title }}: {% url 'wagtailadmin_pages:edit' page_pk %}{% empty %}-
{% endfor %}

{% trans "Pages that were skipped because they had pending translations on RWS LanguageCloud:" %}

{% for page_pk, page_title in skipped_pages %}{{ forloop.counter }}. {{ page_title }}: {{ base_url }}{% url 'wagtailadmin_pages:edit' page_pk %}{% empty %}-{% endfor %}
"""
)


def compose_update_translated_pages_email(all_pages, updated_pages, skipped_pages):
    subject = gettext_lazy("Translated pages have been synced")

    context = Context(
        {
            "all_pages": all_pages,
            "updated_pages": updated_pages,
            "skipped_pages": skipped_pages,
            "base_url": getattr(settings, "BASE_URL", ""),
        }
    )

    body = UPDATE_TRANSLATED_PAGES_EMAIL_TEMPLATE.render(context)

    return subject, body


def get_recipients():
    emails = []
    permissions = [
        "wagtail_localize.add_translation",
        "wagtail_localize.change_translation",
        "wagtail_localize.delete_translation",
        "wagtail_localize.submit_translation",
    ]
    for permission in permissions:
        emails += [user.email for user in User.objects.with_perm(permission)]
    return list(set(emails))
