from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ingestion.models import SourceFile
from apps.search.models import SavedSearch
from apps.search.services.saved_searches import create_saved_search
from apps.workspaces.models import Workspace


User = get_user_model()


class SavedSearchServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="saved-search-user",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Saved Search Workspace",
            owner=self.user,
        )

        self.source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="application.log",
            storage_key="tests/application.log",
            storage_path="tests/application.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=1024,
            checksum="a" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

    def test_create_saved_search_persists_source_checksum(self):
        saved_search = create_saved_search(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            name="Database Errors",
            pattern="ERROR database",
            algorithm="kmp",
            description="Database-related errors",
        )

        self.assertEqual(saved_search.source_file_id, self.source_file.id)
        self.assertEqual(
            saved_search.source_checksum,
            self.source_file.checksum,
        )

    def test_create_saved_search_persists_configuration(self):
        saved_search = create_saved_search(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            name="Upload Errors",
            pattern="upload failed",
            algorithm="rabin_karp",
            description="Upload failure search",
        )

        self.assertEqual(saved_search.owner_id, self.user.id)
        self.assertEqual(saved_search.workspace_id, self.workspace.id)
        self.assertEqual(saved_search.name, "Upload Errors")
        self.assertEqual(saved_search.pattern, "upload failed")
        self.assertEqual(saved_search.algorithm, "rabin_karp")
        self.assertEqual(
            saved_search.description,
            "Upload failure search",
        )

    def test_saved_search_captures_case_and_unicode_options(self):
        saved_search = create_saved_search(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            name="Normalized errors",
            pattern="café",
            algorithm="kmp",
            case_sensitive=False,
            unicode_normalization="NFC",
        )
        self.assertFalse(saved_search.case_sensitive)
        self.assertEqual(saved_search.unicode_normalization, "NFC")

    def test_create_saved_search_rejects_foreign_workspace(self):
        other_user = User.objects.create_user(
            username="other-user",
            password="test-password",
        )

        other_workspace = Workspace.objects.create(
            name="Other Workspace",
            owner=other_user,
        )

        with self.assertRaises(PermissionError):
            create_saved_search(
                owner=self.user,
                workspace=other_workspace,
                source_file=self.source_file,
                name="Invalid Search",
                pattern="ERROR",
                algorithm="kmp",
            )

    def test_create_saved_search_rejects_unextracted_source(self):
        self.source_file.extraction_status = (
            SourceFile.ExtractionStatus.PENDING
        )
        self.source_file.save(update_fields=["extraction_status"])

        with self.assertRaises(ValueError):
            create_saved_search(
                owner=self.user,
                workspace=self.workspace,
                source_file=self.source_file,
                name="Pending Search",
                pattern="ERROR",
                algorithm="kmp",
            )

    def test_saved_search_is_persisted_in_database(self):
        saved_search = create_saved_search(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            name="Persistent Search",
            pattern="WARN",
            algorithm="naive",
        )

        saved_search.refresh_from_db()

        self.assertEqual(saved_search.source_file_id, self.source_file.id)
        self.assertEqual(
            saved_search.source_checksum,
            self.source_file.checksum,
        )
        self.assertEqual(saved_search.pattern, "WARN")
        self.assertEqual(saved_search.algorithm, "naive")

        self.assertTrue(
            SavedSearch.objects.filter(
                pk=saved_search.pk,
            ).exists()
        )
