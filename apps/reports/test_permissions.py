from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory, TestCase

from apps.accounts.services import (
    ADMIN_ROLE,
    ANALYST_ROLE,
    REVIEWER_ROLE,
    assign_role,
)
from apps.reports.views import benchmark_analysis


User = get_user_model()


class ReportsPermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.admin = User.objects.create_user(
            username="reports_admin",
            password="test-password-123",
        )

        self.analyst = User.objects.create_user(
            username="reports_analyst",
            password="test-password-123",
        )

        self.reviewer = User.objects.create_user(
            username="reports_reviewer",
            password="test-password-123",
        )

        self.no_role = User.objects.create_user(
            username="reports_no_role",
            password="test-password-123",
        )

        assign_role(self.admin, ADMIN_ROLE)
        assign_role(self.analyst, ANALYST_ROLE)
        assign_role(self.reviewer, REVIEWER_ROLE)

    def make_request(self, user):
        request = self.factory.get("/reports/")
        request.user = user
        return request

    def test_admin_can_reach_report_view(self):
        request = self.make_request(self.admin)

        with self.assertRaises(Http404):
            benchmark_analysis(
                request,
                benchmark_id=999999,
            )

    def test_analyst_can_reach_report_view(self):
        request = self.make_request(self.analyst)

        with self.assertRaises(Http404):
            benchmark_analysis(
                request,
                benchmark_id=999999,
            )

    def test_reviewer_can_reach_report_view(self):
        request = self.make_request(self.reviewer)

        with self.assertRaises(Http404):
            benchmark_analysis(
                request,
                benchmark_id=999999,
            )

    def test_user_without_role_is_denied(self):
        request = self.make_request(self.no_role)

        with self.assertRaises(PermissionDenied):
            benchmark_analysis(
                request,
                benchmark_id=999999,
            )