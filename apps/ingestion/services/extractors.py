from pathlib import Path

from apps.ingestion.models import SourceFile, TextSegment


TEXT_PARSER_NAME = "plain_text"
TEXT_PARSER_VERSION = "1.0"


def extract_text_file(source_file: SourceFile) -> int:
    if source_file.extension not in {".txt", ".log"}:
        raise ValueError(
            f"Unsupported text extraction extension: {source_file.extension}"
        )

    source_path = Path(source_file.storage_path)

    if not source_path.exists():
        raise FileNotFoundError(
            f"Source file does not exist: {source_path}"
        )

    TextSegment.objects.filter(source_file=source_file).delete()

    segments = []

    with source_path.open("r", encoding="utf-8", errors="strict") as file_obj:
        for line_number, line in enumerate(file_obj, start=1):
            text = line.rstrip("\r\n")

            segments.append(
                TextSegment(
                    source_file=source_file,
                    sequence=line_number,
                    text=text,
                    line_number=line_number,
                    parser_name=TEXT_PARSER_NAME,
                    parser_version=TEXT_PARSER_VERSION,
                )
            )

    TextSegment.objects.bulk_create(segments)

    return len(segments)