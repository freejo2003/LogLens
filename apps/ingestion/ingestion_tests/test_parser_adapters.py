from django.test import SimpleTestCase

from apps.ingestion.services.parser_adapters import (
    ParserAdapter,
    build_default_parser_adapters,
    get_parser_adapter,
)


class ParserAdapterTests(SimpleTestCase):
    def test_supports_matching_extension(self):
        adapter = ParserAdapter(
            name="plain_text",
            version="1.0",
            extensions=frozenset({".txt", ".log"}),
            parser=lambda source_file: 1,
        )

        self.assertTrue(adapter.supports(".txt"))
        self.assertTrue(adapter.supports(".TXT"))

    def test_rejects_unsupported_extension(self):
        adapter = ParserAdapter(
            name="plain_text",
            version="1.0",
            extensions=frozenset({".txt", ".log"}),
            parser=lambda source_file: 1,
        )

        self.assertFalse(adapter.supports(".pdf"))

    def test_get_parser_adapter_returns_matching_adapter(self):
        text_parser = lambda source_file: 1

        adapters = build_default_parser_adapters(text_parser)

        adapter = get_parser_adapter(".txt", adapters)

        self.assertEqual(adapter.name, "plain_text")
        self.assertEqual(adapter.version, "1.0")
        self.assertIn(".txt", adapter.extensions)
        self.assertIn(".log", adapter.extensions)

    def test_get_parser_adapter_is_case_insensitive(self):
        adapters = build_default_parser_adapters(lambda source_file: 1)

        adapter = get_parser_adapter(".LOG", adapters)

        self.assertEqual(adapter.name, "plain_text")

    def test_get_parser_adapter_rejects_unknown_extension(self):
        adapters = build_default_parser_adapters(lambda source_file: 1)

        with self.assertRaises(ValueError):
            get_parser_adapter(".pdf", adapters)