from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.ingestion.models import SourceFile
from apps.ingestion.tasks import extract_source_file_task
from apps.workspaces.models import Workspace


class ExtractionTaskTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="task-owner",
            password="test-password",
        )
        self.workspace = Workspace.objects.create(
            name="Task Workspace",
            owner=self.user,
        )
        self.source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="worker.log",
            storage_key="uploads/task-worker.log",
            storage_path="private_media/uploads/task-worker.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=5,
            checksum="a" * 64,
        )

    def test_pending_source_is_claimed_before_extraction(self):
        def complete(source_file):
            self.assertEqual(
                source_file.extraction_status,
                SourceFile.ExtractionStatus.PROCESSING,
            )
            self.assertIsNotNone(source_file.processing_started_at)
            source_file.extraction_status = SourceFile.ExtractionStatus.SUCCEEDED
            source_file.processing_started_at = None
            source_file.save(update_fields=["extraction_status", "processing_started_at"])

        with patch("apps.ingestion.tasks.process_source_file", side_effect=complete) as process:
            result = extract_source_file_task.run(self.source_file.pk)

        self.assertEqual(result, {"status": "succeeded"})
        process.assert_called_once()

    def test_duplicate_task_does_not_process_an_active_source_twice(self):
        self.source_file.extraction_status = SourceFile.ExtractionStatus.PROCESSING
        self.source_file.processing_started_at = timezone.now()
        self.source_file.save(update_fields=["extraction_status", "processing_started_at"])

        with patch("apps.ingestion.tasks.process_source_file") as process:
            result = extract_source_file_task.run(self.source_file.pk)

        self.assertEqual(result, {"status": "processing"})
        process.assert_not_called()

    def test_stale_processing_source_can_be_recovered_after_worker_loss(self):
        self.source_file.extraction_status = SourceFile.ExtractionStatus.PROCESSING
        self.source_file.processing_started_at = timezone.now() - timedelta(seconds=400)
        self.source_file.save(update_fields=["extraction_status", "processing_started_at"])

        def complete(source_file):
            source_file.extraction_status = SourceFile.ExtractionStatus.SUCCEEDED
            source_file.processing_started_at = None
            source_file.save(update_fields=["extraction_status", "processing_started_at"])

        with patch("apps.ingestion.tasks.process_source_file", side_effect=complete) as process:
            result = extract_source_file_task.run(self.source_file.pk)

        self.assertEqual(result, {"status": "succeeded"})
        process.assert_called_once()
