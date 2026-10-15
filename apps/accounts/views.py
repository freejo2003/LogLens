from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.audit import record_event
from apps.accounts.forms import RoleAssignmentForm
from apps.accounts.models import AuditEvent
from apps.accounts.permissions import admin_required
from apps.accounts.services import ADMIN_ROLE, LOG_LENS_ROLES, assign_role, get_user_role


class LogLensLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


@require_POST
def logout_view(request):
    logout(request)
    return redirect(reverse("accounts:login"))


@login_required
@admin_required
def audit_events(request):
    events = AuditEvent.objects.select_related("actor", "workspace")[:200]
    return render(request, "accounts/audit_events.html", {"audit_events": events})


@login_required
@admin_required
@require_http_methods(["GET", "POST"])
def manage_roles(request):
    if request.method == "POST":
        form = RoleAssignmentForm(request.POST)
        if form.is_valid():
            target = form.cleaned_data["user"]
            role = form.cleaned_data["role"]
            previous_role = get_user_role(target)
            if target.pk == request.user.pk and role != ADMIN_ROLE:
                form.add_error("role", "You cannot remove your own Admin access.")
            elif previous_role == role:
                messages.info(request, "The account already has that role.")
                return redirect("accounts:roles")
            else:
                with transaction.atomic():
                    assign_role(target, role)
                    record_event(
                        actor=request.user,
                        action=AuditEvent.Action.ROLE_ASSIGNED,
                        object_type="User",
                        object_id=target.pk,
                        details={"previous_role": previous_role or "", "role": role},
                    )
                messages.success(request, f"Assigned the {role} role to {target.get_username()}.")
                return redirect("accounts:roles")
    else:
        form = RoleAssignmentForm()

    user_roles = []
    for user in get_user_model().objects.prefetch_related("groups").order_by("username"):
        role_names = {group.name for group in user.groups.all()}
        role = "Admin" if user.is_superuser else next(
            (name for name in LOG_LENS_ROLES if name in role_names),
            "Unassigned",
        )
        user_roles.append({"user": user, "role": role})
    return render(
        request,
        "accounts/manage_roles.html",
        {"form": form, "user_roles": user_roles},
    )
