from pathlib import Path

from pypdf import PdfReader

from apps.ingestion.models import SourceFile, TextSegment


PDF_PARSER_NAME = "pypdf"
PDF_PARSER_VERSION = "1.0"


def extract_pdf_file(source_file: SourceFile) -> int:
    if source_file.extension != ".pdf":
        raise ValueError(
            f"Unsupported PDF extraction extension: {source_file.extension}"
        )

    source_path = Path(source_file.storage_path)

    if not source_path.exists():
        raise FileNotFoundError(
            f"Source file does not exist: {source_path}"
        )

    TextSegment.objects.filter(source_file=source_file).delete()

    reader = PdfReader(str(source_path))
    segments = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        segments.append(
            TextSegment(
                source_file=source_file,
                sequence=page_number,
                text=text,
                page_number=page_number,
                parser_name=PDF_PARSER_NAME,
                parser_version=PDF_PARSER_VERSION,
            )
        )

    TextSegment.objects.bulk_create(segments)

    return len(segments)