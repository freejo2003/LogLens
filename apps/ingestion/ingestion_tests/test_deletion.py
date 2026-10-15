from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ingestion.models import SourceFile, TextSegment
from apps.ingestion.services.deletion import delete_source_file
from apps.search.models import MatchResult, SearchRun
from apps.workspaces.models import Workspace


User = get_user_model()


class SourceFileDeletionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="deletion-user",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            username="other-deletion-user",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Deletion Workspace",
            owner=self.user,
        )

        self.other_workspace = Workspace.objects.create(
            name="Other Workspace",
            owner=self.other_user,
        )

    def create_source_file(self, *, storage_path):
        return SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="application.log",
            storage_key="tests/application.log",
            storage_path=storage_path,
            extension=".log",
            detected_type="text/plain",
            byte_size=1024,
            checksum="a" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

    def test_delete_source_file_rejects_foreign_owner(self):
        source_file = self.create_source_file(
            storage_path="tests/foreign-owner.log",
        )

        with self.assertRaises(PermissionError):
            delete_source_file(
                source_file=source_file,
                owner=self.other_user,
            )

        self.assertTrue(
            SourceFile.objects.filter(pk=source_file.pk).exists()
        )

    def test_delete_source_file_removes_database_record(self):
        source_file = self.create_source_file(
            storage_path="tests/database-delete.log",
        )

        source_file_id = source_file.id

        delete_source_file(
            source_file=source_file,
            owner=self.user,
        )

        self.assertFalse(
            SourceFile.objects.filter(pk=source_file_id).exists()
        )

    def test_delete_source_file_cascades_text_segments(self):
        source_file = self.create_source_file(
            storage_path="tests/segments-delete.log",
        )

        segment = TextSegment.objects.create(
            source_file=source_file,
            sequence=1,
            text="2026-10-14 10:00:00 ERROR database failure",
            parser_name="test",
            parser_version="1.0",
        )

        segment_id = segment.id

        delete_source_file(
            source_file=source_file,
            owner=self.user,
        )

        self.assertFalse(
            TextSegment.objects.filter(pk=segment_id).exists()
        )

    def test_delete_source_file_cascades_match_results(self):
        source_file = self.create_source_file(
            storage_path="tests/matches-delete.log",
        )

        segment = TextSegment.objects.create(
            source_file=source_file,
            sequence=1,
            text="ERROR database failure",
            parser_name="test",
            parser_version="1.0",
        )

        search_run = SearchRun.objects.create(
            workspace=self.workspace,
            owner=self.user,
            source_file=source_file,
            pattern="ERROR",
            algorithm="kmp",
            source_checksum=source_file.checksum,
            total_match_count=1,
        )

        match_result = MatchResult.objects.create(
            search_run=search_run,
            source_file=source_file,
            segment=segment,
            positions=[0],
            match_count=1,
        )

        match_result_id = match_result.id

        delete_source_file(
            source_file=source_file,
            owner=self.user,
        )

        self.assertFalse(
            MatchResult.objects.filter(pk=match_result_id).exists()
        )

    def test_delete_source_file_preserves_search_history(self):
        source_file = self.create_source_file(
            storage_path="tests/search-history.log",
        )

        search_run = SearchRun.objects.create(
            workspace=self.workspace,
            owner=self.user,
            source_file=source_file,
            pattern="ERROR",
            algorithm="kmp",
            source_checksum=source_file.checksum,
            total_match_count=0,
        )

        search_run_id = search_run.id

        delete_source_file(
            source_file=source_file,
            owner=self.user,
        )

        search_run.refresh_from_db()

        self.assertEqual(search_run.id, search_run_id)
        self.assertIsNone(search_run.source_file_id)

    def test_delete_source_file_preserves_saved_search(self):
        from apps.search.models import SavedSearch

        source_file = self.create_source_file(
            storage_path="tests/saved-search.log",
        )

        saved_search = SavedSearch.objects.create(
            workspace=self.workspace,
            owner=self.user,
            source_file=source_file,
            source_checksum=source_file.checksum,
            name="Saved Error Search",
            pattern="ERROR",
            algorithm="kmp",
        )

        saved_search_id = saved_search.id

        delete_source_file(
            source_file=source_file,
            owner=self.user,
        )

        saved_search.refresh_from_db()

        self.assertEqual(saved_search.id, saved_search_id)
        self.assertIsNone(saved_search.source_file_id)

    def test_delete_source_file_removes_physical_file(self):
        storage_key = "tests/physical-delete.log"
        physical_path = Path(settings.PRIVATE_MEDIA_ROOT) / storage_key

        physical_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        physical_path.write_text(
            "test log content",
            encoding="utf-8",
        )

        source_file = self.create_source_file(
            storage_path=str(physical_path),
        )

        try:
            with self.captureOnCommitCallbacks(execute=True):
                delete_source_file(
                    source_file=source_file,
                    owner=self.user,
                )

            self.assertFalse(physical_path.exists())
        finally:
            if physical_path.exists():
                physical_path.unlink()
