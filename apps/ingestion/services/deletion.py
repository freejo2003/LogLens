import logging

from django.db import transaction
from django.db.models import Count

from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent
from apps.ingestion.models import SourceFile
from apps.ingestion.services.storage import delete_private_file, resolve_private_path
from apps.search.models import ErrorGroup, GroupMember


logger = logging.getLogger(__name__)


def delete_source_file(*, source_file: SourceFile, owner) -> None:
    """Remove an owner's original file and all derived source results."""
    if source_file.owner_id != owner.id:
        raise PermissionError("You do not have permission to delete this source file.")

    storage_path = source_file.storage_path
    # Validate before deleting any database rows, then purge after the commit.
    resolve_private_path(storage_path)

    source_file_id = source_file.pk
    with transaction.atomic():
        group_ids = list(
            GroupMember.objects.filter(source_file=source_file)
            .values_list("error_group_id", flat=True)
            .distinct()
        )
        record_event(
            actor=owner,
            workspace=source_file.workspace,
            action=AuditEvent.Action.FILE_DELETED,
            object_type="SourceFile",
            object_id=source_file_id,
            details={"extension": source_file.extension},
        )
        source_file.delete()

        if group_ids:
            counts = dict(
                GroupMember.objects.filter(error_group_id__in=group_ids)
                .values_list("error_group_id")
                .annotate(total=Count("pk"))
            )
            groups = list(ErrorGroup.objects.filter(pk__in=group_ids))
            empty_ids = []
            for group in groups:
                group.occurrence_count = counts.get(group.pk, 0)
                if group.occurrence_count == 0:
                    empty_ids.append(group.pk)
            ErrorGroup.objects.bulk_update(groups, ["occurrence_count"])
            if empty_ids:
                ErrorGroup.objects.filter(pk__in=empty_ids).delete()

    def purge_original():
        try:
            delete_private_file(storage_path)
        except (OSError, ValueError) as exc:
            logger.error(
                "Private upload purge failed for source file id=%s error_type=%s",
                source_file_id,
                type(exc).__name__,
            )

    transaction.on_commit(purge_original, robust=True)
