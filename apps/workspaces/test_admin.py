from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase

from apps.workspaces.admin import WorkspaceAdmin
from apps.workspaces.models import Workspace


class WorkspaceAdminTests(SimpleTestCase):
    def test_workspaces_cannot_bypass_owner_scoped_lifecycle(self):
        model_admin = WorkspaceAdmin(Workspace, admin.site)
        request = RequestFactory().get("/admin/workspaces/workspace/")

        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
