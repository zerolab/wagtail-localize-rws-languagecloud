from django.conf import settings
from django.contrib.auth.models import User
from wagtail.admin.mail import send_mail


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
    subject = "Translated content ready for review"
    body = "Translated content for '{}' is ready for review at: {}".format(
        str(translation.get_target_instance()),
        get_full_url(translation.get_target_instance_edit_url()),
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
