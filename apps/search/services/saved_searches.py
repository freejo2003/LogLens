from apps.search.models import SavedSearch


def create_saved_search(
    *,
    owner,
    workspace,
    name,
    pattern,
    algorithm,
    description="",
):
    if workspace.owner_id != owner.id:
        raise PermissionError(
            "The selected workspace does not belong to the current user."
        )

    return SavedSearch.objects.create(
        owner=owner,
        workspace=workspace,
        name=name,
        pattern=pattern,
        algorithm=algorithm,
        description=description,
    )


def get_saved_searches_for_user(user):
    return (
        SavedSearch.objects
        .filter(owner=user, is_active=True)
        .select_related("workspace")
        .order_by("name")
    )