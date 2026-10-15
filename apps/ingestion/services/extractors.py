from pathlib import Path

from apps.ingestion.models import SourceFile, TextSegment
from apps.ingestion.services.errors import ExtractionError
from apps.ingestion.services.segment_writer import SegmentBatchWriter, iter_decoded_lines


TEXT_PARSER_NAME = "plain_text"
TEXT_PARSER_VERSION = "1.1"


def extract_text_file(source_file: SourceFile) -> int:
    if source_file.extension not in {".txt", ".log"}:
        raise ExtractionError("This text parser does not support the uploaded file type.")

    source_path = Path(source_file.storage_path)
    if not source_path.exists() or not source_path.is_file():
        raise ExtractionError("The original upload is unavailable. Upload the file again.")

    TextSegment.objects.filter(source_file=source_file).delete()
    writer = SegmentBatchWriter(source_file)
    encoding = source_file.text_encoding or "utf-8"
    try:
        with source_path.open("rb") as file_obj:
            for line_number, line in enumerate(
                iter_decoded_lines(file_obj, encoding), start=1
            ):
                writer.add(
                    line,
                    line_number=line_number,
                    parser_name=TEXT_PARSER_NAME,
                    parser_version=TEXT_PARSER_VERSION,
                )
    except UnicodeError as exc:
        raise ExtractionError("The text file could not be decoded with its recorded encoding.") from exc
    return writer.finish()
