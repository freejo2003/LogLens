from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase

from apps.ingestion.admin import SourceFileAdmin
from apps.ingestion.models import SourceFile


class SourceFileAdminTests(SimpleTestCase):
    def test_source_records_cannot_bypass_deletion_or_owner_workflows(self):
        model_admin = SourceFileAdmin(SourceFile, admin.site)
        request = RequestFactory().get("/admin/ingestion/sourcefile/")

        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
