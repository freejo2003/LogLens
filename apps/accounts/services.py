from django.contrib.auth.models import Group


ADMIN_ROLE = "Admin"
ANALYST_ROLE = "Analyst"
REVIEWER_ROLE = "Reviewer"

LOG_LENS_ROLES = (
    ADMIN_ROLE,
    ANALYST_ROLE,
    REVIEWER_ROLE,
)


def get_or_create_role_groups():
    """
    Create the Django Groups used by LogLens and return them
    as a dictionary keyed by role name.
    """
    roles = {}

    for role_name in LOG_LENS_ROLES:
        group, _ = Group.objects.get_or_create(name=role_name)
        roles[role_name] = group

    return roles


def assign_role(user, role_name):
    """
    Assign exactly one LogLens role to a user.

    Django's built-in superuser status remains independent of
    application roles.
    """
    if role_name not in LOG_LENS_ROLES:
        raise ValueError(f"Unknown LogLens role: {role_name}")

    roles = get_or_create_role_groups()

    user.groups.remove(*roles.values())
    user.groups.add(roles[role_name])

    return roles[role_name]


def get_user_role(user):
    """
    Return the user's LogLens role.

    Superusers are treated as Admins. Otherwise, return the
    first assigned LogLens role, or None if no role is assigned.
    """
    if user.is_superuser:
        return ADMIN_ROLE

    role_names = set(
        user.groups.filter(name__in=LOG_LENS_ROLES)
        .values_list("name", flat=True)
    )

    for role_name in LOG_LENS_ROLES:
        if role_name in role_names:
            return role_name

    return None


def has_role(user, role_name):
    """
    Check whether the user has the requested LogLens role.
    """
    return get_user_role(user) == role_name


def is_admin(user):
    return get_user_role(user) == ADMIN_ROLE


def is_analyst(user):
    return get_user_role(user) == ANALYST_ROLE


def is_reviewer(user):
    return get_user_role(user) == REVIEWER_ROLE
