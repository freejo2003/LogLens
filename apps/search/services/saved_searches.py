from django.db import transaction

from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent
from apps.search.models import SavedSearch


@transaction.atomic
def create_saved_search(
    *,
    owner,
    workspace,
    source_file,
    name,
    pattern,
    algorithm,
    description="",
    case_sensitive=True,
    unicode_normalization="none",
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
            "The selected source file does not belong "
            "to the selected workspace."
        )

    if source_file.extraction_status != source_file.ExtractionStatus.SUCCEEDED:
        raise ValueError(
            "The selected source file has not been successfully extracted."
        )

    saved_search = SavedSearch.objects.create(
        owner=owner,
        workspace=workspace,
        source_file=source_file,
        source_checksum=source_file.checksum,
        name=name,
        pattern=pattern,
        algorithm=algorithm,
        case_sensitive=case_sensitive,
        unicode_normalization=unicode_normalization,
        description=description,
    )
    record_event(
        actor=owner,
        workspace=workspace,
        action=AuditEvent.Action.SAVED_SEARCH_CREATED,
        object_type="SavedSearch",
        object_id=saved_search.pk,
        details={"algorithm": algorithm},
    )
    return saved_search


def get_saved_searches_for_user(user):
    return (
        SavedSearch.objects
        .filter(
            owner=user,
            is_active=True,
        )
        .select_related(
            "workspace",
            "source_file",
        )
        .order_by("name")
    )
