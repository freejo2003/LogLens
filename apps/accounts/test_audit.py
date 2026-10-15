from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent
from apps.accounts.services import (
    ADMIN_ROLE,
    ANALYST_ROLE,
    REVIEWER_ROLE,
    assign_role,
    get_user_role,
)
from apps.workspaces.models import Workspace


class AuditEventTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="audit-admin", password="test-password"
        )
        self.other = user_model.objects.create_user(
            username="audit-other", password="test-password"
        )
        self.reviewer = user_model.objects.create_user(
            username="audit-reviewer", password="test-password"
        )
        assign_role(self.admin, ADMIN_ROLE)
        assign_role(self.other, ANALYST_ROLE)
        assign_role(self.reviewer, REVIEWER_ROLE)
        self.workspace = Workspace.objects.create(name="Audit", owner=self.admin)
        self.other_workspace = Workspace.objects.create(name="Other", owner=self.other)

    def test_event_captures_action_and_minimal_details(self):
        event = record_event(
            actor=self.admin,
            workspace=self.workspace,
            action=AuditEvent.Action.FILE_UPLOADED,
            object_type="SourceFile",
            object_id=12,
            details={"extension": ".log", "byte_size": 128},
        )
        self.assertEqual(event.object_id, "12")
        self.assertEqual(event.details, {"extension": ".log", "byte_size": 128})

    def test_event_cannot_be_written_to_another_users_workspace(self):
        with self.assertRaises(PermissionError):
            record_event(
                actor=self.admin,
                workspace=self.other_workspace,
                action=AuditEvent.Action.FILE_DELETED,
                object_type="SourceFile",
                object_id=10,
            )

    def test_admin_can_review_audit_events_across_users(self):
        record_event(
            actor=self.admin,
            workspace=self.workspace,
            action=AuditEvent.Action.WORKSPACE_CREATED,
            object_type="Workspace",
            object_id=self.workspace.pk,
        )
        record_event(
            actor=self.other,
            workspace=self.other_workspace,
            action=AuditEvent.Action.WORKSPACE_CREATED,
            object_type="Workspace",
            object_id=self.other_workspace.pk,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:audit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Audit")
        self.assertContains(response, "Other")
        self.assertContains(response, "audit-other")

    def test_non_admin_cannot_view_audit_events(self):
        self.client.force_login(self.reviewer)
        response = self.client.get(reverse("accounts:audit"))
        self.assertEqual(response.status_code, 403)

    def test_admin_role_assignment_is_attributed_and_audited(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:roles"),
            {"user": self.other.pk, "role": REVIEWER_ROLE},
        )
        self.assertEqual(response.status_code, 302)
        self.other.refresh_from_db()
        self.assertEqual(get_user_role(self.other), REVIEWER_ROLE)
        event = AuditEvent.objects.get(action=AuditEvent.Action.ROLE_ASSIGNED)
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.object_id, str(self.other.pk))
        self.assertEqual(
            event.details,
            {"previous_role": ANALYST_ROLE, "role": REVIEWER_ROLE},
        )

    def test_non_admin_cannot_assign_roles(self):
        self.client.force_login(self.reviewer)
        response = self.client.post(
            reverse("accounts:roles"),
            {"user": self.other.pk, "role": REVIEWER_ROLE},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_remove_own_admin_access(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:roles"),
            {"user": self.admin.pk, "role": REVIEWER_ROLE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You cannot remove your own Admin access.")
        self.assertEqual(get_user_role(self.admin), ADMIN_ROLE)
