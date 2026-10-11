from collections.abc import Callable

from apps.ingestion.models import SourceFile
from apps.ingestion.services.docx_extractor import extract_docx_file
from apps.ingestion.services.extractors import extract_text_file
from apps.ingestion.services.parser_adapters import (
    ParserAdapter,
    get_parser_adapter,
)
from apps.ingestion.services.pdf_extractor import extract_pdf_file


def build_parser_registry() -> list[ParserAdapter]:
    """
    Build the parser registry for all currently supported formats.
    """
    return [
        ParserAdapter(
            name="plain_text",
            version="1.0",
            extensions=frozenset({".txt", ".log"}),
            parser=extract_text_file,
        ),
        ParserAdapter(
            name="pypdf",
            version="1.0",
            extensions=frozenset({".pdf"}),
            parser=extract_pdf_file,
        ),
        ParserAdapter(
            name="python-docx",
            version="1.0",
            extensions=frozenset({".docx"}),
            parser=extract_docx_file,
        ),
    ]


def resolve_parser(source_file: SourceFile) -> ParserAdapter:
    """
    Resolve the parser adapter responsible for a source file.
    """
    return get_parser_adapter(
        source_file.extension,
        build_parser_registry(),
    )


def register_parser(
    registry: list[ParserAdapter],
    *,
    name: str,
    version: str,
    extensions: set[str] | frozenset[str],
    parser: Callable[[SourceFile], int],
) -> list[ParserAdapter]:
    """
    Add a parser adapter to an existing registry.

    A new list is returned so the original registry is not modified.
    """
    updated_registry = list(registry)

    updated_registry.append(
        ParserAdapter(
            name=name,
            version=version,
            extensions=frozenset(
                extension.lower() for extension in extensions
            ),
            parser=parser,
        )
    )

    return updated_registry