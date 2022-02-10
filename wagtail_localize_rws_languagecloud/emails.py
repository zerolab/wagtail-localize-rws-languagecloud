from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy
from wagtail.admin.mail import send_mail


User = get_user_model()


def get_full_url(url):
    if hasattr(settings, "BASE_URL") and url.startswith("/"):
        url = settings.BASE_URL + url
    return url


def send_emails(translation):
    subject, body = compose_email(translation)
    recipients = get_recipients()
    for recipient in recipients:
        send_mail(subject, body, [recipient])


def compose_email(translation):
    subject = gettext_lazy("Translated content ready for review")
    body = gettext_lazy(
        "Translated content for '%(instance)s' is ready for review at: %(edit_url)s"
        % {
            "instance": str(translation.get_target_instance()),
            "edit_url": get_full_url(translation.get_target_instance_edit_url()),
        }
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
