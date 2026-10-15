from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from unittest.mock import patch

from apps.accounts.services import ANALYST_ROLE, assign_role
from apps.ingestion.models import SourceFile
from apps.workspaces.models import Workspace

User = get_user_model()


class MultipleUploadViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="multiple-upload-user",
            password="test-password",
        )
        assign_role(self.user, ANALYST_ROLE)
        self.workspace = Workspace.objects.create(name="Uploads", owner=self.user)
        self.client.force_login(self.user)

    def test_upload_post_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(reverse("ingestion:upload"), data={})
        self.assertEqual(response.status_code, 403)

    @patch("apps.ingestion.views.enqueue_extraction")
    @patch("apps.ingestion.views.save_private_file")
    def test_multiple_uploads_create_owned_pending_sources_and_queue_them(
        self, save_private_file, enqueue_extraction
    ):
        save_private_file.side_effect = [
            "C:/private/uploads/one.log",
            "C:/private/uploads/two.txt",
        ]
        files = [
            SimpleUploadedFile("one.log", b"ERROR one\n", content_type="text/plain"),
            SimpleUploadedFile("two.txt", b"WARN two\n", content_type="text/plain"),
        ]
        response = self.client.post(
            reverse("ingestion:upload"),
            {"workspace": self.workspace.pk, "files": files},
        )

        self.assertEqual(response.status_code, 302)
        sources = list(SourceFile.objects.filter(owner=self.user).order_by("original_name"))
        self.assertEqual([item.original_name for item in sources], ["one.log", "two.txt"])
        self.assertTrue(all(item.extraction_status == SourceFile.ExtractionStatus.PENDING for item in sources))
        self.assertEqual(enqueue_extraction.call_count, 2)


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

        self.assertEqual(response.status_code, 405)

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
