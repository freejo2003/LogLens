from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from apps.accounts.permissions import (
    admin_required,
    analyst_required,
    reviewer_required,
)
from apps.accounts.services import (
    ADMIN_ROLE,
    ANALYST_ROLE,
    REVIEWER_ROLE,
    assign_role,
)

User = get_user_model()


def protected_view(request):
    return "allowed"


class PermissionDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.admin = User.objects.create_user(
            username="permission_admin",
            password="test-password-123",
        )

        self.analyst = User.objects.create_user(
            username="permission_analyst",
            password="test-password-123",
        )

        self.reviewer = User.objects.create_user(
            username="permission_reviewer",
            password="test-password-123",
        )

        self.no_role = User.objects.create_user(
            username="permission_no_role",
            password="test-password-123",
        )

        assign_role(self.admin, ADMIN_ROLE)
        assign_role(self.analyst, ANALYST_ROLE)
        assign_role(self.reviewer, REVIEWER_ROLE)

        self.admin_view = admin_required(protected_view)
        self.analyst_view = analyst_required(protected_view)
        self.reviewer_view = reviewer_required(protected_view)

    def make_request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_admin_can_access_admin_view(self):
        request = self.make_request(self.admin)

        self.assertEqual(
            self.admin_view(request),
            "allowed",
        )

    def test_analyst_cannot_access_admin_view(self):
        request = self.make_request(self.analyst)

        with self.assertRaises(PermissionDenied):
            self.admin_view(request)

    def test_reviewer_cannot_access_admin_view(self):
        request = self.make_request(self.reviewer)

        with self.assertRaises(PermissionDenied):
            self.admin_view(request)

    def test_no_role_cannot_access_admin_view(self):
        request = self.make_request(self.no_role)

        with self.assertRaises(PermissionDenied):
            self.admin_view(request)

    def test_admin_can_access_analyst_view(self):
        request = self.make_request(self.admin)

        self.assertEqual(
            self.analyst_view(request),
            "allowed",
        )

    def test_analyst_can_access_analyst_view(self):
        request = self.make_request(self.analyst)

        self.assertEqual(
            self.analyst_view(request),
            "allowed",
        )

    def test_reviewer_cannot_access_analyst_view(self):
        request = self.make_request(self.reviewer)

        with self.assertRaises(PermissionDenied):
            self.analyst_view(request)

    def test_admin_can_access_reviewer_view(self):
        request = self.make_request(self.admin)

        self.assertEqual(
            self.reviewer_view(request),
            "allowed",
        )

    def test_analyst_can_access_reviewer_view(self):
        request = self.make_request(self.analyst)

        self.assertEqual(
            self.reviewer_view(request),
            "allowed",
        )

    def test_reviewer_can_access_reviewer_view(self):
        request = self.make_request(self.reviewer)

        self.assertEqual(
            self.reviewer_view(request),
            "allowed",
        )
        