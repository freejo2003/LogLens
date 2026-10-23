from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.services import ANALYST_ROLE, REVIEWER_ROLE, assign_role
from apps.ingestion.models import SourceFile
from apps.search.models import SavedSearch, SearchBatch, SearchBatchItem, SearchRun
from apps.search.tasks import run_search_batch_task
from apps.workspaces.models import Workspace, WorkspaceReviewer


class ProductGapWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="batch-owner", password="pass")
        self.reviewer = User.objects.create_user(username="batch-reviewer", password="pass")
        assign_role(self.owner, ANALYST_ROLE)
        assign_role(self.reviewer, REVIEWER_ROLE)
        self.workspace = Workspace.objects.create(name="Shared project", owner=self.owner)
        self.files = [
            SourceFile.objects.create(
                workspace=self.workspace, owner=self.owner, original_name=f"source-{index}.log",
                storage_key=f"private/source-{index}", storage_path=f"private/source-{index}",
                extension=".log", detected_type="text/plain", byte_size=10,
                checksum=str(index) * 64, extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
            ) for index in (1, 2)
        ]

    @patch("apps.search.views.enqueue_search_batch")
    def test_search_creates_batch_for_each_file_pattern_pair(self, enqueue):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("search:run"), {
            "workspace": self.workspace.pk,
            "source_files": [file.pk for file in self.files],
            "pattern": "ERROR\nWARN",
            "algorithm": "kmp",
            "case_sensitive": "on",
            "unicode_normalization": "none",
            "level_filter": "ERROR",
        })
        batch = SearchBatch.objects.get(owner=self.owner)
        self.assertRedirects(response, reverse("search:batch-detail", args=[batch.pk]), fetch_redirect_response=False)
        self.assertEqual(batch.total_items, 4)
        self.assertEqual(batch.items.count(), 4)
        self.assertEqual(batch.level_filter, "ERROR")
        enqueue.assert_called_once_with(batch.pk)

    def test_batch_owner_can_request_cooperative_cancellation(self):
        batch = SearchBatch.objects.create(workspace=self.workspace, owner=self.owner, algorithm="kmp", total_items=1)
        self.client.force_login(self.owner)
        response = self.client.post(reverse("search:batch-cancel", args=[batch.pk]))
        self.assertRedirects(response, reverse("search:batch-detail", args=[batch.pk]), fetch_redirect_response=False)
        batch.refresh_from_db()
        self.assertEqual(batch.status, SearchBatch.Status.CANCEL_REQUESTED)

    def test_worker_completes_pair_and_updates_batch_progress(self):
        batch = SearchBatch.objects.create(workspace=self.workspace, owner=self.owner, algorithm="kmp", total_items=1)
        item = SearchBatchItem.objects.create(batch=batch, source_file=self.files[0], pattern="ERROR")
        from apps.ingestion.models import TextSegment
        TextSegment.objects.create(source_file=self.files[0], sequence=1, text="ERROR", line_number=1,
                                   parser_name="plain_text", parser_version="1.0")
        result = run_search_batch_task.apply(args=[batch.pk]).get()
        batch.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(result["status"], SearchBatch.Status.SUCCEEDED)
        self.assertEqual(batch.completed_items, 1)
        self.assertEqual(item.status, SearchBatchItem.Status.SUCCEEDED)
        self.assertIsNotNone(item.search_run_id)

    def test_worker_honors_cancellation_before_starting_items(self):
        batch = SearchBatch.objects.create(workspace=self.workspace, owner=self.owner, algorithm="kmp",
                                           status=SearchBatch.Status.CANCEL_REQUESTED, total_items=1)
        item = SearchBatchItem.objects.create(batch=batch, source_file=self.files[0], pattern="ERROR")
        result = run_search_batch_task.apply(args=[batch.pk]).get()
        batch.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(result["status"], SearchBatch.Status.CANCELLED)
        self.assertEqual(batch.status, SearchBatch.Status.CANCELLED)
        self.assertEqual(item.status, SearchBatchItem.Status.CANCELLED)

    def test_reviewer_share_grants_read_only_search_history_access(self):
        run = SearchRun.objects.create(workspace=self.workspace, owner=self.owner, source_file=self.files[0], pattern="ERROR", algorithm="kmp")
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(reverse("search:history-detail", args=[run.pk])).status_code, 404)
        WorkspaceReviewer.objects.create(workspace=self.workspace, reviewer=self.reviewer)
        self.assertEqual(self.client.get(reverse("search:history-detail", args=[run.pk])).status_code, 200)
        self.assertEqual(self.client.post(reverse("search:run")).status_code, 403)

    def test_saved_search_comparison_is_scoped_to_selected_owner_searches(self):
        saved_a = SavedSearch.objects.create(workspace=self.workspace, owner=self.owner, source_file=self.files[0], name="Errors", pattern="ERROR", algorithm="kmp")
        saved_b = SavedSearch.objects.create(workspace=self.workspace, owner=self.owner, source_file=self.files[1], name="Warnings", pattern="WARN", algorithm="naive")
        run_a = SearchRun.objects.create(workspace=self.workspace, owner=self.owner, source_file=self.files[0], saved_search=saved_a, pattern="ERROR", algorithm="kmp", total_match_count=3)
        SearchRun.objects.create(workspace=self.workspace, owner=self.owner, source_file=self.files[1], saved_search=saved_b, pattern="WARN", algorithm="naive", total_match_count=8)
        self.client.force_login(self.owner)
        response = self.client.post(reverse("search:saved-compare"), {"saved_search_ids": [saved_a.pk, saved_b.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Errors")
        self.assertContains(response, "Warnings")
        self.assertContains(response, "3")
        self.assertEqual(run_a.saved_search_id, saved_a.pk)
