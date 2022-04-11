from django.conf import settings
from django.contrib.auth import get_user_model
from django.template import loader
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


def compose_update_translated_pages_email(all_pages, updated_pages, skipped_pages):
    subject = gettext_lazy("Translated pages have been synced")

    context = {
        "all_pages": all_pages,
        "updated_pages": updated_pages,
        "skipped_pages": skipped_pages,
        "base_url": getattr(settings, "BASE_URL", ""),
    }

    body = loader.render_to_string(
        "wagtail_localize_rws_languagecloud/emails/update_translated_pages.txt",
        context,
    )

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
