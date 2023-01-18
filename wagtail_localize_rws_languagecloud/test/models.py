from django.db import models
from django.utils.translation import gettext_lazy
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.core.models import TranslatableMixin
from wagtail.snippets.models import register_snippet

from wagtail_localize.fields import SynchronizedField, TranslatableField


try:
    from wagtail.core.fields import RichTextField
    from wagtail.core.models import Page
except ImportError:
    from wagtail.fields import RichTextField
    from wagtail.models import Page


@register_snippet
class ExampleSnippet(TranslatableMixin):
    """
    Example snippet model for testing purposes.
    """

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class TestPage(Page):
    test_charfield = models.CharField(
        gettext_lazy("char field"), max_length=255, blank=True, null=True, default=""
    )
    test_textfield = models.TextField(blank=True)
    test_richtextfield = RichTextField(blank=True)
    test_synchronized_charfield = models.CharField(max_length=255, blank=True)

    translatable_fields = [
        TranslatableField("test_charfield"),
        TranslatableField("test_textfield"),
        TranslatableField("test_richtextfield"),
        SynchronizedField("test_synchronized_charfield"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("test_charfield"),
        FieldPanel("test_textfield"),
        FieldPanel("test_richtextfield"),
        FieldPanel("test_synchronized_charfield"),
    ]
