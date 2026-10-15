from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_check_queries_database(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    @patch("config.views.connection.cursor", side_effect=OperationalError("private database detail"))
    def test_health_check_returns_generic_failure_without_leaking_errors(self, _cursor):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.content, b"unavailable")
        self.assertNotIn(b"private database detail", response.content)

    def test_health_check_is_get_only(self):
        response = self.client.post(reverse("health"))
        self.assertEqual(response.status_code, 405)
