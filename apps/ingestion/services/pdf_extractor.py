from django.conf import settings
from pypdf import PdfReader

from apps.ingestion.models import SourceFile, TextSegment
from apps.ingestion.services.errors import ExtractionError, OCRNeededError
from apps.ingestion.services.segment_writer import SegmentBatchWriter
from pathlib import Path


PDF_PARSER_NAME = "pypdf"
PDF_PARSER_VERSION = "1.1"


def extract_pdf_file(source_file: SourceFile) -> int:
    if source_file.extension != ".pdf":
        raise ExtractionError("This PDF parser does not support the uploaded file type.")

    source_path = Path(source_file.storage_path)
    if not source_path.exists() or not source_path.is_file():
        raise ExtractionError("The original upload is unavailable. Upload the file again.")

    try:
        reader = PdfReader(str(source_path), strict=False)
        page_count = len(reader.pages)
    except Exception as exc:
        raise ExtractionError("The PDF could not be read. Verify that it is a valid PDF.") from exc

    if page_count > settings.MAX_PDF_PAGES:
        raise ExtractionError("The PDF exceeds the configured page limit.")

    TextSegment.objects.filter(source_file=source_file).delete()
    writer = SegmentBatchWriter(source_file)
    extracted_characters = 0
    try:
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            extracted_characters += len(text)
            writer.add(
                text,
                page_number=page_number,
                parser_name=PDF_PARSER_NAME,
                parser_version=PDF_PARSER_VERSION,
            )
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError("The PDF text could not be extracted safely.") from exc

    if page_count and extracted_characters == 0:
        raise OCRNeededError(
            "This PDF contains no extractable text. It may be scanned; OCR is not enabled."
        )
    return writer.finish()
