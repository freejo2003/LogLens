from apps.search.models import SavedSearch


def create_saved_search(
    *,
    owner,
    workspace,
    source_file,
    name,
    pattern,
    algorithm,
    description="",
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

    return SavedSearch.objects.create(
        owner=owner,
        workspace=workspace,
        source_file=source_file,
        source_checksum=source_file.checksum,
        name=name,
        pattern=pattern,
        algorithm=algorithm,
        description=description,
    )


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