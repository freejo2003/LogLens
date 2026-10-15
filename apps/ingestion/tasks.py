import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent
from apps.ingestion.models import SourceFile
from apps.ingestion.services.extraction import process_source_file


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.ingestion.extract_source_file",
    ignore_result=True,
    acks_late=True,
    max_retries=0,
    soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.CELERY_TASK_TIME_LIMIT,
)
def extract_source_file_task(self, source_file_id: int) -> dict[str, str]:
    try:
        with transaction.atomic():
            source_file = (
                SourceFile.objects.select_for_update()
                .select_related("owner", "workspace")
                .get(pk=source_file_id)
            )
            if source_file.extraction_status == SourceFile.ExtractionStatus.SUCCEEDED:
                return {"status": "succeeded"}
            if source_file.extraction_status == SourceFile.ExtractionStatus.PROCESSING:
                stale_before = timezone.now() - timedelta(
                    seconds=settings.CELERY_TASK_TIME_LIMIT + 15
                )
                if (
                    source_file.processing_started_at is not None
                    and source_file.processing_started_at > stale_before
                ):
                    return {"status": "processing"}
            elif source_file.extraction_status != SourceFile.ExtractionStatus.PENDING:
                return {"status": source_file.extraction_status}

            source_file.extraction_status = SourceFile.ExtractionStatus.PROCESSING
            source_file.processing_started_at = timezone.now()
            source_file.save(update_fields=["extraction_status", "processing_started_at"])
    except SourceFile.DoesNotExist:
        return {"status": "missing"}

    try:
        process_source_file(source_file)
    except Exception as exc:
        logger.error(
            "Extraction task failed for source file id=%s error_type=%s",
            source_file_id,
            type(exc).__name__,
        )
        return {"status": "failed"}

    return {"status": "succeeded"}


def enqueue_extraction(source_file_id: int) -> None:
    """Dispatch after the source row is committed; fail closed if Redis is down."""
    def dispatch():
        try:
            extract_source_file_task.delay(source_file_id)
        except Exception as exc:
            logger.error(
                "Extraction task could not be queued for source file id=%s error_type=%s",
                source_file_id,
                type(exc).__name__,
            )
            source_file = (
                SourceFile.objects.select_related("owner", "workspace")
                .filter(pk=source_file_id)
                .first()
            )
            if source_file is not None:
                SourceFile.objects.filter(pk=source_file_id).update(
                    extraction_status=SourceFile.ExtractionStatus.FAILED,
                    extraction_error="The analysis worker is unavailable. Try again shortly.",
                    processing_started_at=None,
                )
                record_event(
                    actor=source_file.owner,
                    workspace=source_file.workspace,
                    action=AuditEvent.Action.EXTRACTION_FAILED,
                    object_type="SourceFile",
                    object_id=source_file.pk,
                    details={"reason": "worker_unavailable"},
                )

    transaction.on_commit(dispatch)
