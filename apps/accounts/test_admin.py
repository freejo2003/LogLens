from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, SimpleTestCase

from apps.accounts.admin import LogLensUserAdmin


class LogLensUserAdminTests(SimpleTestCase):
    def test_roles_cannot_be_changed_through_default_admin(self):
        user = get_user_model()(pk=1)
        request = RequestFactory().get("/admin/auth/user/")
        user_admin = LogLensUserAdmin(get_user_model(), admin.site)

        self.assertIn("groups", user_admin.get_readonly_fields(request, user))
        self.assertFalse(admin.site.is_registered(Group))
