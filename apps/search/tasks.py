import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.search.models import SearchBatch, SearchBatchItem
from apps.search.services.search_persistence import create_search_run

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="apps.search.run_search_batch", acks_late=True, max_retries=0)
def run_search_batch_task(self, batch_id):
    batch = SearchBatch.objects.filter(pk=batch_id).first()
    if batch is None:
        return {"status": "missing"}
    SearchBatch.objects.filter(
        pk=batch_id,
        status=SearchBatch.Status.QUEUED,
    ).update(status=SearchBatch.Status.RUNNING)
    for item in batch.items.select_related("source_file", "batch__workspace").order_by("id"):
        batch.refresh_from_db(fields=["status"])
        if batch.status == SearchBatch.Status.CANCEL_REQUESTED:
            batch.items.filter(status=SearchBatchItem.Status.QUEUED).update(status=SearchBatchItem.Status.CANCELLED)
            completed = batch.items.filter(
                status__in=[
                    SearchBatchItem.Status.SUCCEEDED,
                    SearchBatchItem.Status.FAILED,
                    SearchBatchItem.Status.CANCELLED,
                ]
            ).count()
            SearchBatch.objects.filter(pk=batch.pk).update(completed_items=completed)
            break
        claimed = SearchBatchItem.objects.filter(
            pk=item.pk,
            status=SearchBatchItem.Status.QUEUED,
        ).update(status=SearchBatchItem.Status.RUNNING)
        if not claimed:
            continue
        try:
            run = create_search_run(
                workspace=batch.workspace,
                owner=batch.owner,
                source_file=item.source_file,
                pattern=item.pattern,
                algorithm=batch.algorithm,
                case_sensitive=batch.case_sensitive,
                unicode_normalization=batch.unicode_normalization,
                level_filter=batch.level_filter,
            )
            SearchBatchItem.objects.filter(pk=item.pk).update(status=SearchBatchItem.Status.SUCCEEDED, search_run=run)
        except Exception:
            logger.exception("Search batch item failed", extra={"batch_id": batch.pk, "item_id": item.pk})
            SearchBatchItem.objects.filter(pk=item.pk).update(status=SearchBatchItem.Status.FAILED)
        finally:
            completed = batch.items.filter(
                status__in=[
                    SearchBatchItem.Status.SUCCEEDED,
                    SearchBatchItem.Status.FAILED,
                    SearchBatchItem.Status.CANCELLED,
                ]
            ).count()
            SearchBatch.objects.filter(pk=batch.pk).update(completed_items=completed)
    batch.refresh_from_db()
    if batch.items.filter(
        status__in=[SearchBatchItem.Status.QUEUED, SearchBatchItem.Status.RUNNING]
    ).exists():
        return {"status": batch.status}
    terminal_status = SearchBatch.Status.CANCELLED if batch.status == SearchBatch.Status.CANCEL_REQUESTED else (
        SearchBatch.Status.FAILED
        if batch.items.filter(status=SearchBatchItem.Status.FAILED).exists()
        else SearchBatch.Status.SUCCEEDED
    )
    SearchBatch.objects.filter(pk=batch.pk).update(status=terminal_status, completed_at=timezone.now())
    return {"status": terminal_status}


def enqueue_search_batch(batch_id):
    def dispatch():
        try:
            task = run_search_batch_task.delay(batch_id)
            SearchBatch.objects.filter(pk=batch_id).update(celery_task_id=task.id)
        except Exception:
            logger.exception("Could not enqueue search batch", extra={"batch_id": batch_id})
            SearchBatch.objects.filter(pk=batch_id).update(status=SearchBatch.Status.FAILED, completed_at=timezone.now())
    transaction.on_commit(dispatch)
