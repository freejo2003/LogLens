from django.db import transaction

from apps.ingestion.models import SourceFile
from apps.ingestion.services.parser_registry import resolve_parser
from apps.search.services.error_groups import (
    rebuild_error_groups_for_source_file,
)


def process_source_file(source_file: SourceFile) -> int:
    source_file.extraction_status = SourceFile.ExtractionStatus.PROCESSING
    source_file.save(update_fields=["extraction_status"])

    try:
        parser = resolve_parser(source_file)

        with transaction.atomic():
            segment_count = parser.parser(source_file)

            # Rebuild recurring ERROR/WARN groups from the
            # newly extracted segments.
            rebuild_error_groups_for_source_file(
                owner=source_file.owner,
                source_file=source_file,
            )

            source_file.extraction_status = (
                SourceFile.ExtractionStatus.SUCCEEDED
            )
            source_file.save(update_fields=["extraction_status"])

        return segment_count

    except Exception:
        source_file.extraction_status = SourceFile.ExtractionStatus.FAILED
        source_file.save(update_fields=["extraction_status"])
        raise