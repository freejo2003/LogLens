from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.services import ANALYST_ROLE, REVIEWER_ROLE, assign_role
from apps.workspaces.models import Workspace
from apps.workspaces.models import WorkspaceReviewer


class WorkspaceCreationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.analyst = user_model.objects.create_user(
            username="workspace-analyst",
            password="test-password",
        )
        self.reviewer = user_model.objects.create_user(
            username="workspace-reviewer",
            password="test-password",
        )
        assign_role(self.analyst, ANALYST_ROLE)
        assign_role(self.reviewer, REVIEWER_ROLE)

    def test_analyst_can_create_owned_workspace(self):
        self.client.force_login(self.analyst)
        response = self.client.post(
            reverse("workspace-create"),
            {"name": "Production Logs", "description": "API services"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        workspace = Workspace.objects.get(name="Production Logs")
        self.assertEqual(workspace.owner_id, self.analyst.pk)

    def test_reviewer_cannot_create_workspace(self):
        self.client.force_login(self.reviewer)
        response = self.client.post(
            reverse("workspace-create"),
            {"name": "Not Allowed", "description": ""},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Workspace.objects.exists())

    def test_owner_can_share_workspace_with_reviewer(self):
        workspace = Workspace.objects.create(name="Reviewable", owner=self.analyst)
        self.client.force_login(self.analyst)
        response = self.client.post(
            reverse("workspace-share", args=[workspace.pk]),
            {"reviewer": self.reviewer.pk},
        )
        self.assertRedirects(response, reverse("workspace-share", args=[workspace.pk]))
        self.assertTrue(WorkspaceReviewer.objects.filter(workspace=workspace, reviewer=self.reviewer).exists())
