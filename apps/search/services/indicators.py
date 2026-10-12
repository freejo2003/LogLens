from apps.search.models import IndicatorRule


def create_indicator_rule(
    *,
    owner,
    workspace,
    name,
    pattern,
    description="",
    is_active=True,
):
    if workspace.owner_id != owner.id:
        raise PermissionError(
            "The selected workspace does not belong to the current user."
        )

    return IndicatorRule.objects.create(
        owner=owner,
        workspace=workspace,
        name=name,
        pattern=pattern,
        description=description,
        is_active=is_active,
    )


def get_indicator_rules_for_user(user):
    return (
        IndicatorRule.objects
        .filter(owner=user)
        .select_related("workspace")
        .order_by("name")
    )