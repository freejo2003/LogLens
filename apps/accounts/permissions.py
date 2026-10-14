from functools import wraps

from django.core.exceptions import PermissionDenied

from apps.accounts.services import (
    ADMIN_ROLE,
    ANALYST_ROLE,
    REVIEWER_ROLE,
    get_user_role,
)


def role_required(*allowed_roles):
    """
    Restrict a view to users with one of the specified LogLens roles.

    Superusers are treated as Admin by get_user_role().
    """

    if not allowed_roles:
        raise ValueError("At least one allowed role must be specified.")

    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied

            user_role = get_user_role(request.user)

            if user_role not in allowed_roles:
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def admin_required(view_func):
    """Allow only Admin users."""
    return role_required(ADMIN_ROLE)(view_func)


def analyst_required(view_func):
    """Allow Admin and Analyst users."""
    return role_required(
        ADMIN_ROLE,
        ANALYST_ROLE,
    )(view_func)


def reviewer_required(view_func):
    """Allow Admin, Analyst, and Reviewer users."""
    return role_required(
        ADMIN_ROLE,
        ANALYST_ROLE,
        REVIEWER_ROLE,
    )(view_func)


def analyst_post_required(view_func):
    """
    Allow read-only GET access to everyone with a LogLens role,
    but restrict POST requests to Admin and Analyst users.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.method == "POST":
            return analyst_required(view_func)(
                request,
                *args,
                **kwargs,
            )

        return reviewer_required(view_func)(
            request,
            *args,
            **kwargs,
        )

    return wrapped_view