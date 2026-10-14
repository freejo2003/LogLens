from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from apps.accounts.services import (
    ADMIN_ROLE,
    ANALYST_ROLE,
    REVIEWER_ROLE,
    assign_role,
)
from apps.benchmarks.views import benchmark_workspace


User = get_user_model()


class BenchmarkPermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.admin = User.objects.create_user(
            username="benchmark_admin",
            password="test-password-123",
        )

        self.analyst = User.objects.create_user(
            username="benchmark_analyst",
            password="test-password-123",
        )

        self.reviewer = User.objects.create_user(
            username="benchmark_reviewer",
            password="test-password-123",
        )

        assign_role(self.admin, ADMIN_ROLE)
        assign_role(self.analyst, ANALYST_ROLE)
        assign_role(self.reviewer, REVIEWER_ROLE)

    def make_request(self, user, method="GET"):
        if method == "POST":
            request = self.factory.post("/benchmarks/")
        else:
            request = self.factory.get("/benchmarks/")

        request.user = user
        return request

    def test_admin_can_view_benchmark_page(self):
        request = self.make_request(self.admin)

        response = benchmark_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_analyst_can_view_benchmark_page(self):
        request = self.make_request(self.analyst)

        response = benchmark_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_can_view_benchmark_page(self):
        request = self.make_request(self.reviewer)

        response = benchmark_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_cannot_execute_benchmark(self):
        request = self.make_request(
            self.reviewer,
            method="POST",
        )

        with self.assertRaises(PermissionDenied):
            benchmark_workspace(request)