from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.accounts.services import ANALYST_ROLE, assign_role
from apps.ingestion.models import SourceFile
from apps.workspaces.models import Workspace
from apps.accounts.services import ANALYST_ROLE, assign_role

User = get_user_model()


class SourceFileDeletionViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="view-delete-user",
            password="test-password",
        )
        assign_role(self.user, ANALYST_ROLE)

        self.other_user = User.objects.create_user(
            username="view-other-user",
            password="test-password",
        )
        assign_role(self.other_user, ANALYST_ROLE)

        self.workspace = Workspace.objects.create(
            name="View Deletion Workspace",
            owner=self.user,
        )

        self.source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="view-delete.log",
            storage_key="uploads/view-delete.log",
            storage_path="uploads/view-delete.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=100,
            checksum="b" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

    def test_delete_requires_login(self):
        response = self.client.post(
            reverse(
                "ingestion:delete",
                args=[self.source_file.id],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

        self.assertTrue(
            SourceFile.objects.filter(pk=self.source_file.id).exists()
        )

    def test_delete_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "ingestion:delete",
                args=[self.source_file.id],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("ingestion:upload"),
        )

        self.assertTrue(
            SourceFile.objects.filter(pk=self.source_file.id).exists()
        )

    def test_owner_can_delete_source_file(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "ingestion:delete",
                args=[self.source_file.id],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("ingestion:upload"),
        )

        self.assertFalse(
            SourceFile.objects.filter(
                pk=self.source_file.id
            ).exists()
        )

    def test_other_user_cannot_delete_source_file(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse(
                "ingestion:delete",
                args=[self.source_file.id],
            )
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            SourceFile.objects.filter(
                pk=self.source_file.id
            ).exists()
        )