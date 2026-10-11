from pathlib import Path

from docx import Document

from apps.ingestion.models import SourceFile, TextSegment


DOCX_PARSER_NAME = "python-docx"
DOCX_PARSER_VERSION = "1.0"


def extract_docx_file(source_file: SourceFile) -> int:
    if source_file.extension != ".docx":
        raise ValueError(
            f"Unsupported DOCX extraction extension: {source_file.extension}"
        )

    source_path = Path(source_file.storage_path)

    if not source_path.exists():
        raise FileNotFoundError(
            f"Source file does not exist: {source_path}"
        )

    TextSegment.objects.filter(source_file=source_file).delete()

    document = Document(str(source_path))
    segments = []

    for paragraph_number, paragraph in enumerate(
        document.paragraphs, start=1
    ):
        segments.append(
            TextSegment(
                source_file=source_file,
                sequence=paragraph_number,
                text=paragraph.text,
                paragraph_number=paragraph_number,
                parser_name=DOCX_PARSER_NAME,
                parser_version=DOCX_PARSER_VERSION,
            )
        )

    TextSegment.objects.bulk_create(segments)

    return len(segments)