from django.db import models
from wagtail.core.models import TranslatableMixin
from wagtail.snippets.models import register_snippet


@register_snippet
class ExampleSnippet(TranslatableMixin):
    """
    Example snippet model for testing purposes.
    """

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
