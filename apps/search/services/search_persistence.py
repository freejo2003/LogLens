from django.db import transaction
from django.utils import timezone

from apps.search.models import MatchResult, SearchRun
from apps.search.services.search_service import search_source_file


def create_search_run(
    *,
    workspace,
    owner,
    source_file,
    pattern,
    algorithm,
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

    search_run = SearchRun.objects.create(
        workspace=workspace,
        owner=owner,
        source_file=source_file,
        pattern=pattern,
        algorithm=algorithm,
        source_checksum=source_file.checksum,
        status=SearchRun.Status.SUCCEEDED,
    )

    try:
        results = search_source_file(
            source_file,
            pattern=pattern,
            algorithm=algorithm,
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

        return search_run

    except Exception as exc:
        search_run.status = SearchRun.Status.FAILED
        search_run.error_message = str(exc)
        search_run.completed_at = timezone.now()
        search_run.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
            ]
        )
        raise