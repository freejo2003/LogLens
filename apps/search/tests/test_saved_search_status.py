from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ingestion.models import SourceFile
from apps.search.models import SavedSearch
from apps.search.services.saved_search_status import (
    CHANGED,
    CURRENT,
    MISSING,
    get_saved_search_source_status,
)
from apps.workspaces.models import Workspace


User = get_user_model()


class SavedSearchSourceStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="status-user",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Status Workspace",
            owner=self.user,
        )

        self.source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="application.log",
            storage_key="tests/status-application.log",
            storage_path="tests/status-application.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=1024,
            checksum="a" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

    def create_saved_search(self, **overrides):
        values = {
            "owner": self.user,
            "workspace": self.workspace,
            "source_file": self.source_file,
            "source_checksum": self.source_file.checksum,
            "name": "Test Search",
            "pattern": "ERROR",
            "algorithm": "kmp",
        }
        values.update(overrides)

        return SavedSearch.objects.create(**values)

    def test_current_source_is_reported_as_current(self):
        saved_search = self.create_saved_search()

        result = get_saved_search_source_status(saved_search)

        self.assertEqual(result.status, CURRENT)
        self.assertEqual(
            result.message,
            "The source file matches the saved-search snapshot.",
        )

    def test_changed_source_is_reported_as_changed(self):
        saved_search = self.create_saved_search()

        self.source_file.checksum = "b" * 64
        self.source_file.save(update_fields=["checksum"])

        saved_search.refresh_from_db()

        result = get_saved_search_source_status(saved_search)

        self.assertEqual(result.status, CHANGED)
        self.assertEqual(
            result.message,
            "The source file has changed since this search was saved.",
        )

    def test_missing_source_is_reported_as_missing(self):
        saved_search = self.create_saved_search()

        self.source_file.delete()

        saved_search.refresh_from_db()

        result = get_saved_search_source_status(saved_search)

        self.assertEqual(result.status, MISSING)
        self.assertEqual(
            result.message,
            "The saved search has no associated source file.",
        )

    def test_missing_checksum_snapshot_is_reported_as_changed(self):
        saved_search = self.create_saved_search(
            source_checksum="",
        )

        result = get_saved_search_source_status(saved_search)

        self.assertEqual(result.status, CHANGED)
        self.assertEqual(
            result.message,
            "The saved search has no source checksum snapshot.",
        )