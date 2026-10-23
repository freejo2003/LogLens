from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class LoginPageLayoutTests(TestCase):
    def test_login_page_hides_application_navigation(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="sidebar"')
        self.assertNotContains(response, 'class="topbar"')
        self.assertNotContains(response, "Reports")

    def test_sidebar_does_not_show_unimplemented_reports_index(self):
        user = get_user_model().objects.create_user(
            username="navigation-test-user",
            password="test-password",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        self.assertNotContains(response, "Reports")
