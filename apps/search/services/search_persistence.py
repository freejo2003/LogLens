import logging

from django.db import transaction
from django.utils import timezone

from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent
from apps.search.models import MatchResult, SearchRun
from apps.search.services.search_service import search_source_file


logger = logging.getLogger(__name__)


def create_search_run(
    *,
    workspace,
    owner,
    source_file,
    pattern,
    algorithm,
    indicator_rule=None,
    case_sensitive=True,
    unicode_normalization="none",
    level_filter="",
    saved_search=None,
):
    if workspace.owner_id != owner.id:
        raise PermissionError(
            "The selected workspace does not belong to the current user."
        )

    if source_file.owner_id != owner.id:
        raise PermissionError(
            "The selected source file does not belong to the current user."
        )

    if source_file.workspace_id != workspace.id:
        raise PermissionError(
            "The selected source file does not belong to the selected workspace."
        )

    indicator_name_snapshot = ""
    if indicator_rule is not None:
        if indicator_rule.owner_id != owner.id:
            raise PermissionError("The selected indicator does not belong to the current user.")
        if indicator_rule.workspace_id != workspace.id:
            raise PermissionError("The selected indicator does not belong to the selected workspace.")
        if not indicator_rule.is_active:
            raise ValueError("The selected indicator is inactive.")
        pattern = indicator_rule.pattern
        indicator_name_snapshot = indicator_rule.name

    search_run = SearchRun.objects.create(
        workspace=workspace,
        owner=owner,
        saved_search=saved_search,
        source_file=source_file,
        indicator_rule=indicator_rule,
        indicator_name_snapshot=indicator_name_snapshot,
        pattern=pattern,
        algorithm=algorithm,
        case_sensitive=case_sensitive,
        unicode_normalization=unicode_normalization,
        level_filter=level_filter,
        source_checksum=source_file.checksum,
        status=SearchRun.Status.SUCCEEDED,
    )

    try:
        results = search_source_file(
            source_file,
            pattern=pattern,
            algorithm=algorithm,
            case_sensitive=case_sensitive,
            unicode_normalization=unicode_normalization,
            level_filter=level_filter,
        )

        with transaction.atomic():
            match_results = []

            for result in results:
                match_results.append(
                    MatchResult(
                        search_run=search_run,
                        source_file=source_file,
                        segment_id=result.segment_id,
                        positions=list(result.positions),
                        match_count=result.match_count,
                    )
                )

            MatchResult.objects.bulk_create(match_results)

            total_match_count = sum(
                result.match_count for result in results
            )

            search_run.total_match_count = total_match_count
            search_run.completed_at = timezone.now()
            search_run.save(
                update_fields=[
                    "total_match_count",
                    "completed_at",
                ]
            )
            record_event(
                actor=owner,
                workspace=workspace,
                action=AuditEvent.Action.SEARCH_COMPLETED,
                object_type="SearchRun",
                object_id=search_run.pk,
                details={
                    "algorithm": algorithm,
                    "match_count": total_match_count,
                    "case_sensitive": case_sensitive,
                    "unicode_normalization": unicode_normalization,
                    "indicator_rule_id": indicator_rule.pk if indicator_rule else None,
                },
            )

        return search_run

    except Exception as exc:
        search_run.status = SearchRun.Status.FAILED
        search_run.error_message = "The search could not be completed. Try again or contact an administrator."
        search_run.completed_at = timezone.now()
        search_run.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
            ]
        )
        record_event(
            actor=owner,
            workspace=workspace,
            action=AuditEvent.Action.SEARCH_FAILED,
            object_type="SearchRun",
            object_id=search_run.pk,
            details={"algorithm": algorithm},
        )
        logger.error(
            "Search run failed for run id=%s source_file_id=%s error_type=%s",
            search_run.pk,
            source_file.pk,
            type(exc).__name__,
        )
        raise
