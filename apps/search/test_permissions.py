from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from apps.accounts.services import (
    ADMIN_ROLE,
    ANALYST_ROLE,
    REVIEWER_ROLE,
    assign_role,
)
from apps.search.views import (
    create_indicator,
    error_groups_workspace,
    indicators_workspace,
    save_search,
    saved_searches_workspace,
    search_workspace,
)

User = get_user_model()


class SearchPermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.admin = User.objects.create_user(
            username="search_admin",
            password="test-password-123",
        )

        self.analyst = User.objects.create_user(
            username="search_analyst",
            password="test-password-123",
        )

        self.reviewer = User.objects.create_user(
            username="search_reviewer",
            password="test-password-123",
        )

        assign_role(self.admin, ADMIN_ROLE)
        assign_role(self.analyst, ANALYST_ROLE)
        assign_role(self.reviewer, REVIEWER_ROLE)

    def make_request(self, user, method="GET"):
        if method == "POST":
            request = self.factory.post("/search/")
        else:
            request = self.factory.get("/search/")

        request.user = user
        return request

    def test_admin_can_view_search_workspace(self):
        request = self.make_request(self.admin)

        response = search_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_analyst_can_view_search_workspace(self):
        request = self.make_request(self.analyst)

        response = search_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_can_view_search_workspace(self):
        request = self.make_request(self.reviewer)

        response = search_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_cannot_execute_search(self):
        request = self.make_request(
            self.reviewer,
            method="POST",
        )

        with self.assertRaises(PermissionDenied):
            search_workspace(request)

    def test_admin_can_access_saved_searches(self):
        request = self.make_request(self.admin)

        response = saved_searches_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_analyst_can_access_saved_searches(self):
        request = self.make_request(self.analyst)

        response = saved_searches_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_can_access_saved_searches(self):
        request = self.make_request(self.reviewer)

        response = saved_searches_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_cannot_create_saved_search(self):
        request = self.make_request(
            self.reviewer,
            method="POST",
        )

        with self.assertRaises(PermissionDenied):
            save_search(request)

    def test_admin_can_access_indicators(self):
        request = self.make_request(self.admin)

        response = indicators_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_analyst_can_access_indicators(self):
        request = self.make_request(self.analyst)

        response = indicators_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_can_access_indicators(self):
        request = self.make_request(self.reviewer)

        response = indicators_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_cannot_create_indicator(self):
        request = self.make_request(
            self.reviewer,
            method="POST",
        )

        with self.assertRaises(PermissionDenied):
            create_indicator(request)

    def test_admin_can_access_error_groups(self):
        request = self.make_request(self.admin)

        response = error_groups_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_analyst_can_access_error_groups(self):
        request = self.make_request(self.analyst)

        response = error_groups_workspace(request)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_can_access_error_groups(self):
        request = self.make_request(self.reviewer)

        response = error_groups_workspace(request)

        self.assertEqual(response.status_code, 200)