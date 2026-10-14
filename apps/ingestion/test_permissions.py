from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from apps.accounts.services import (
    ADMIN_ROLE,
    ANALYST_ROLE,
    REVIEWER_ROLE,
    assign_role,
)
from apps.ingestion.views import (
    delete_source_file_view,
    extract_source_file,
    upload_source_file,
)

User = get_user_model()


class IngestionPermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.admin = User.objects.create_user(
            username="ingestion_admin",
            password="test-password-123",
        )

        self.analyst = User.objects.create_user(
            username="ingestion_analyst",
            password="test-password-123",
        )

        self.reviewer = User.objects.create_user(
            username="ingestion_reviewer",
            password="test-password-123",
        )

        assign_role(self.admin, ADMIN_ROLE)
        assign_role(self.analyst, ANALYST_ROLE)
        assign_role(self.reviewer, REVIEWER_ROLE)

    def make_request(self, user, method="GET"):
        if method == "POST":
            request = self.factory.post("/ingestion/")
        else:
            request = self.factory.get("/ingestion/")

        request.user = user
        return request

    def test_admin_can_access_upload_view(self):
        request = self.make_request(self.admin)

        response = upload_source_file(request)

        self.assertEqual(response.status_code, 200)

    def test_analyst_can_access_upload_view(self):
        request = self.make_request(self.analyst)

        response = upload_source_file(request)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_cannot_access_upload_view(self):
        request = self.make_request(self.reviewer)

        with self.assertRaises(PermissionDenied):
            upload_source_file(request)

    def test_reviewer_cannot_extract_file(self):
        request = self.make_request(
            self.reviewer,
            method="POST",
        )

        with self.assertRaises(PermissionDenied):
            extract_source_file(request, source_file_id=999999)

    def test_reviewer_cannot_delete_file(self):
        request = self.make_request(
            self.reviewer,
            method="POST",
        )

        with self.assertRaises(PermissionDenied):
            delete_source_file_view(
                request,
                source_file_id=999999,
            )