from django.test import SimpleTestCase

from apps.ingestion.services.parser_registry import (
    build_parser_registry,
    register_parser,
    resolve_parser,
)


class ParserRegistryTests(SimpleTestCase):
    def test_registry_contains_all_currently_supported_parsers(self):
        registry = build_parser_registry()

        self.assertEqual(len(registry), 3)

        parser_names = {adapter.name for adapter in registry}

        self.assertEqual(
            parser_names,
            {"plain_text", "pypdf", "python-docx"},
        )

    def test_registry_contains_text_parser(self):
        registry = build_parser_registry()

        adapter = next(
            adapter
            for adapter in registry
            if adapter.name == "plain_text"
        )

        self.assertEqual(adapter.version, "1.0")
        self.assertEqual(
            adapter.extensions,
            frozenset({".txt", ".log"}),
        )

    def test_registry_contains_pdf_parser(self):
        registry = build_parser_registry()

        adapter = next(
            adapter
            for adapter in registry
            if adapter.name == "pypdf"
        )

        self.assertEqual(adapter.version, "1.0")
        self.assertEqual(adapter.extensions, frozenset({".pdf"}))

    def test_registry_contains_docx_parser(self):
        registry = build_parser_registry()

        adapter = next(
            adapter
            for adapter in registry
            if adapter.name == "python-docx"
        )

        self.assertEqual(adapter.version, "1.0")
        self.assertEqual(adapter.extensions, frozenset({".docx"}))

    def test_resolve_parser_for_txt(self):
        source_file = type(
            "SourceFileStub",
            (),
            {"extension": ".txt"},
        )()

        adapter = resolve_parser(source_file)

        self.assertEqual(adapter.name, "plain_text")

    def test_resolve_parser_for_pdf(self):
        source_file = type(
            "SourceFileStub",
            (),
            {"extension": ".pdf"},
        )()

        adapter = resolve_parser(source_file)

        self.assertEqual(adapter.name, "pypdf")

    def test_resolve_parser_for_docx(self):
        source_file = type(
            "SourceFileStub",
            (),
            {"extension": ".docx"},
        )()

        adapter = resolve_parser(source_file)

        self.assertEqual(adapter.name, "python-docx")

    def test_resolve_parser_rejects_unsupported_extension(self):
        source_file = type(
            "SourceFileStub",
            (),
            {"extension": ".doc"},
        )()

        with self.assertRaises(ValueError):
            resolve_parser(source_file)

    def test_register_parser_adds_adapter(self):
        registry = build_parser_registry()

        def fake_parser(source_file):
            return 0

        updated_registry = register_parser(
            registry,
            name="legacy_doc",
            version="1.0",
            extensions={".doc"},
            parser=fake_parser,
        )

        self.assertEqual(len(registry), 3)
        self.assertEqual(len(updated_registry), 4)
        self.assertEqual(
            updated_registry[-1].name,
            "legacy_doc",
        )

    def test_register_parser_normalizes_extensions(self):
        registry = build_parser_registry()

        updated_registry = register_parser(
            registry,
            name="legacy_doc",
            version="1.0",
            extensions={".DOC"},
            parser=lambda source_file: 0,
        )

        self.assertEqual(
            updated_registry[-1].extensions,
            frozenset({".doc"}),
        )