from apps.accounts.models import AuditEvent


def record_event(*, actor, action, object_type, object_id="", workspace=None, details=None):
    """Write a compact, data-minimized event for a completed user action."""
    if workspace is not None and actor is not None and workspace.owner_id != actor.pk:
        raise PermissionError("Audit events may only be recorded for the actor's workspace.")
    return AuditEvent.objects.create(
        actor=actor,
        workspace=workspace,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else "",
        details=details or {},
    )
