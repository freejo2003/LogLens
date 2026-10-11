from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from apps.ingestion.models import SourceFile


@dataclass(frozen=True)
class ParserAdapter:
    name: str
    version: str
    extensions: frozenset[str]
    parser: Callable[[SourceFile], int]

    def supports(self, extension: str) -> bool:
        return extension.lower() in self.extensions


def get_parser_adapter(
    extension: str,
    adapters: list[ParserAdapter],
) -> ParserAdapter:
    normalized_extension = extension.lower()

    for adapter in adapters:
        if adapter.supports(normalized_extension):
            return adapter

    raise ValueError(
        f"No parser adapter is registered for extension: "
        f"{normalized_extension}"
    )


def build_default_parser_adapters(
    text_parser: Callable[[SourceFile], int],
) -> list[ParserAdapter]:
    return [
        ParserAdapter(
            name="plain_text",
            version="1.0",
            extensions=frozenset({".txt", ".log"}),
            parser=text_parser,
        ),
    ]