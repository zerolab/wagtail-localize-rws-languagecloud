import datetime
import logging

from unittest import mock

from django.core.exceptions import SuspiciousOperation, ValidationError
from django.test import TestCase
from wagtail.core.models import Locale

from wagtail_localize.models import (
    MissingRelatedObjectError,
    Translation,
    TranslationSource,
)
from wagtail_localize.test.models import TestPage, TestSnippet

from ..importer import Importer
from .helpers import create_test_page, create_test_po


class TestImporter(TestCase):
    def setUp(self):
        self.page, self.source = create_test_page(
            title="Test page",
            slug="test-page",
            test_charfield="The test translatable field",
            test_synchronized_charfield="The test synchronized field",
            test_textfield="The other test translatable field",
        )
        self.locale = Locale.objects.create(language_code="fr")
        self.translation = Translation.objects.create(
            source=self.source,
            target_locale=self.locale,
        )

    def test_importer_page(self):
        po = create_test_po(
            [
                (
                    "test_charfield",
                    "The test translatable field",
                    "Le champ traduisible de test",
                )
            ]
        )

        file_mock = mock.Mock()
        importer = Importer(file_mock, logging.getLogger("dummy"))
        importer.import_po(self.translation, str(po))

        # Check translated page was created
        translated_page = TestPage.objects.get(locale=self.locale)
        self.assertEqual(translated_page.translation_key, self.page.translation_key)
        self.assertEqual(translated_page.test_charfield, "Le champ traduisible de test")
        self.assertEqual(
            translated_page.test_synchronized_charfield,
            "The test synchronized field",
        )

        self.assertEqual(file_mock.save.call_count, 1)

        # Perform another import updating the page
        # Much easier to do it this way than trying to construct all the models manually to match the result of the last test
        po = create_test_po(
            [
                (
                    "test_charfield",
                    "The test translatable field",
                    "Le champ testable à traduire avec un contenu mis à jour",
                )
            ]
        )

        file_mock = mock.Mock()
        importer = Importer(file_mock, logging.getLogger("dummy"))
        importer.import_po(self.translation, str(po))

        translated_page.refresh_from_db()
        self.assertEqual(translated_page.translation_key, self.page.translation_key)
        self.assertEqual(
            translated_page.test_charfield,
            "Le champ testable à traduire avec un contenu mis à jour",
        )
        self.assertEqual(
            translated_page.test_synchronized_charfield,
            "The test synchronized field",
        )

        self.assertEqual(file_mock.save.call_count, 1)

    def test_importer_snippet(self):
        snippet = TestSnippet.objects.create(field="Test snippet")
        source, created = TranslationSource.get_or_create_from_instance(snippet)
        po = create_test_po(
            [
                (
                    "field",
                    "Test snippet",
                    "Extrait de test",
                )
            ]
        )
        translation = Translation.objects.create(
            source=source,
            target_locale=self.locale,
        )

        file_mock = mock.Mock()
        importer = Importer(file_mock, logging.getLogger("dummy"))
        importer.import_po(translation, str(po))

        # Check translated snippet
        translated_snippet = TestSnippet.objects.get(locale=self.locale)
        self.assertEqual(translated_snippet.translation_key, snippet.translation_key)
        self.assertEqual(translated_snippet.field, "Extrait de test")

        self.assertEqual(file_mock.save.call_count, 1)

    def test_importer_warnings(self):
        po = create_test_po(
            [
                # Unknown string
                (
                    "test_charfield",
                    "Unknown string",
                    "Le champ traduisible de test",
                ),
                # Unknown context
                (
                    "unknown_context",
                    "The test translatable field",
                    "Le champ testable à traduire avec un contenu mis à jour",
                ),
                # String not used in context
                (
                    "test_charfield",
                    "The other test translatable field",
                    "Le champ traduisible de test",
                ),
            ]
        )

        logger = mock.MagicMock()
        importer = Importer(mock.Mock(), logger)
        importer.import_po(self.translation, str(po))

        # Check that the warnings were logged
        logger.warning.assert_any_call(
            "While translating 'Test page' into French: Unrecognised string 'Unknown string'"
        )
        logger.warning.assert_any_call(
            "While translating 'Test page' into French: Unrecognised context 'unknown_context'"
        )
        logger.warning.assert_any_call(
            "While translating 'Test page' into French: The string 'The other test translatable field' is not used in context  'test_charfield'"
        )

    @mock.patch("wagtail_localize.models.Translation.save_target")
    def test_importer_missing_related_object(self, save_target):
        save_target.side_effect = MissingRelatedObjectError("segment", self.locale)

        po = create_test_po(
            [
                (
                    "test_charfield",
                    "The test translatable field",
                    "Le champ traduisible de test",
                )
            ]
        )

        logger = mock.MagicMock()
        importer = Importer(mock.Mock(), logger)
        importer.import_po(self.translation, str(po))

        # Check a warning was logged
        logger.warning.assert_called_with(
            "Unable to translate 'Test page' into French: Missing related object"
        )

    @mock.patch("wagtail_localize.models.Translation.save_target")
    def test_importer_validation_error(self, save_target):
        save_target.side_effect = ValidationError(
            {"slug": "This slug is already in use."}
        )

        po = create_test_po(
            [
                (
                    "test_charfield",
                    "The test translatable field",
                    "Le champ traduisible de test",
                )
            ]
        )

        logger = mock.MagicMock()
        importer = Importer(mock.Mock(), logger)
        importer.import_po(self.translation, str(po))

        # Check a warning was logged
        logger.warning.assert_called_with(
            "Unable to translate 'Test page' into French: ValidationError({'slug': ['This slug is already in use.']})"
        )

    def test_importer_suspicious(self):
        file_mock = mock.Mock()
        importer = Importer(file_mock, logging.getLogger("dummy"))
        with self.assertRaises(SuspiciousOperation):
            importer.import_po(self.translation, "/etc/passwd")

    def test_importer_line_sep_char(self):
        po_string = f"""#
msgid ""
msgstr ""
"POT-Creation-Date: {datetime.datetime.utcnow()}\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"

msgid "test_charfield"
"Communicate on any channel  "
"<br/>your customers prefer"
msgstr ""
"Kommunizieren Sie über die  <br/>bevorzugten Kanäle Ihrer Kundschaft"
        """

        file_mock = mock.Mock()
        importer = Importer(file_mock, logging.getLogger("dummy"))

        # This next line crashes without the fix
        importer.import_po(self.translation, po_string)


class TestImporterRichText(TestCase):
    def setUp(self):
        self.page, self.source = create_test_page(
            title="Test page",
            slug="test-page",
            test_richtextfield='<p><a href="https://www.example.com">The <b>test</b> translatable field</a>.</p>',
        )
        self.locale = Locale.objects.create(language_code="fr")
        self.translation = Translation.objects.create(
            source=self.source,
            target_locale=self.locale,
        )

    def test_importer_rich_text(self):
        po = create_test_po(
            [
                (
                    "test_richtextfield",
                    '<a id="a1">The <b>test</b> translatable field</a>.',
                    '<a id="a1">Le champ traduisible de <b>test</b></a>.',
                )
            ]
        )

        importer = Importer(mock.Mock(), logging.getLogger("dummy"))
        importer.import_po(self.translation, str(po))

        # Check translated page was created
        translated_page = TestPage.objects.get(locale=self.locale)
        self.assertEqual(translated_page.translation_key, self.page.translation_key)

        # Check rich text field was created correctly
        self.assertHTMLEqual(
            translated_page.test_richtextfield,
            '<p><a href="https://www.example.com">Le champ traduisible de <b>test</b></a>.</p>',
        )
