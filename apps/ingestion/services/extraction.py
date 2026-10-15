import logging

from django.db import transaction
from django.utils import timezone

from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent
from apps.ingestion.models import SourceFile
from apps.ingestion.services.parser_registry import resolve_parser
from apps.ingestion.services.errors import ExtractionError, OCRNeededError
from apps.search.services.error_groups import (
    rebuild_error_groups_for_source_file,
)

logger = logging.getLogger(__name__)


def process_source_file(source_file: SourceFile) -> int:
    source_file.extraction_status = SourceFile.ExtractionStatus.PROCESSING
    source_file.extraction_error = ""
    source_file.processing_started_at = timezone.now()
    source_file.save(
        update_fields=["extraction_status", "extraction_error", "processing_started_at"]
    )

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
            source_file.processing_started_at = None
            source_file.save(update_fields=["extraction_status", "processing_started_at"])
            record_event(
                actor=source_file.owner,
                workspace=source_file.workspace,
                action=AuditEvent.Action.EXTRACTION_COMPLETED,
                object_type="SourceFile",
                object_id=source_file.pk,
                details={"segment_count": segment_count},
            )

        return segment_count

    except Exception as exc:
        source_file.extraction_status = (
            SourceFile.ExtractionStatus.OCR_NEEDED
            if isinstance(exc, OCRNeededError)
            else SourceFile.ExtractionStatus.FAILED
        )
        source_file.extraction_error = (
            exc.public_message
            if isinstance(exc, ExtractionError)
            else "The file could not be extracted. Confirm it is a supported, valid document and try again."
        )
        source_file.processing_started_at = None
        source_file.save(
            update_fields=["extraction_status", "extraction_error", "processing_started_at"]
        )
        record_event(
            actor=source_file.owner,
            workspace=source_file.workspace,
            action=AuditEvent.Action.EXTRACTION_FAILED,
            object_type="SourceFile",
            object_id=source_file.pk,
            details={"status": source_file.extraction_status},
        )
        logger.warning(
            "Extraction failed for source file id=%s error_type=%s",
            source_file.pk,
            type(exc).__name__,
        )
        raise
