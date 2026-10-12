from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ingestion.models import SourceFile, TextSegment
from apps.ingestion.services.extraction import process_source_file
from apps.workspaces.models import Workspace


class SourceFileExtractionTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="extraction-test-user",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Extraction Test Workspace",
            owner=self.user,
        )

    def test_successful_extraction_updates_status(self):
        with TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "sample.txt"
            source_path.write_text(
                "first line\nsecond line\n",
                encoding="utf-8",
            )

            source_file = SourceFile.objects.create(
                workspace=self.workspace,
                owner=self.user,
                original_name="sample.txt",
                storage_key="uploads/extraction-sample.txt",
                storage_path=str(source_path),
                extension=".txt",
                detected_type="text/plain",
                byte_size=source_path.stat().st_size,
                checksum="test-checksum",
            )

            segment_count = process_source_file(source_file)

            source_file.refresh_from_db()

            self.assertEqual(segment_count, 2)
            self.assertEqual(
                source_file.extraction_status,
                SourceFile.ExtractionStatus.SUCCEEDED,
            )
            self.assertEqual(
                TextSegment.objects.filter(source_file=source_file).count(),
                2,
            )

    def test_failed_extraction_updates_status(self):
        source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="missing.txt",
            storage_key="uploads/missing.txt",
            storage_path="missing.txt",
            extension=".txt",
            detected_type="text/plain",
            byte_size=10,
            checksum="test-checksum",
        )

        with self.assertRaises(FileNotFoundError):
            process_source_file(source_file)

        source_file.refresh_from_db()

        self.assertEqual(
            source_file.extraction_status,
            SourceFile.ExtractionStatus.FAILED,
        )

    def test_successful_extraction_replaces_existing_segments(self):
        with TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "sample.txt"
            source_path.write_text(
                "updated content\n",
                encoding="utf-8",
            )

            source_file = SourceFile.objects.create(
                workspace=self.workspace,
                owner=self.user,
                original_name="sample.txt",
                storage_key="uploads/replacement-sample.txt",
                storage_path=str(source_path),
                extension=".txt",
                detected_type="text/plain",
                byte_size=source_path.stat().st_size,
                checksum="test-checksum",
            )

            TextSegment.objects.create(
                source_file=source_file,
                sequence=1,
                text="old content",
                line_number=1,
                parser_name="plain_text",
                parser_version="0.9",
            )

            segment_count = process_source_file(source_file)

            self.assertEqual(segment_count, 1)

            segments = list(
                TextSegment.objects.filter(
                    source_file=source_file
                ).order_by("sequence")
            )

            self.assertEqual(len(segments), 1)
            self.assertEqual(segments[0].text, "updated content")
            self.assertEqual(segments[0].parser_version, "1.0")

    def test_loglens_test_application_file_extracts_26_segments(self):
        project_root = Path(__file__).resolve().parents[3]
        source_path = project_root / "LogLens_Test_Application.log"

        self.assertTrue(
            source_path.exists(),
            f"Expected test dataset was not found: {source_path}",
        )

        source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="LogLens_Test_Application.log",
            storage_key="uploads/test-application.log",
            storage_path=str(source_path),
            extension=".log",
            detected_type="text/plain",
            byte_size=source_path.stat().st_size,
            checksum="test-checksum",
        )

        segment_count = process_source_file(source_file)

        source_file.refresh_from_db()

        self.assertEqual(segment_count, 26)
        self.assertEqual(
            source_file.extraction_status,
            SourceFile.ExtractionStatus.SUCCEEDED,
        )

        segments = list(
            TextSegment.objects.filter(
                source_file=source_file
            ).order_by("sequence")
        )

        self.assertEqual(len(segments), 26)
        self.assertEqual(
            [segment.sequence for segment in segments],
            list(range(1, 27)),
        )
        self.assertEqual(
            [segment.line_number for segment in segments],
            list(range(1, 27)),
        )

        self.assertEqual(
            segments[0].text,
            "2026-10-12 09:00:01 INFO Application started successfully",
        )

        self.assertEqual(
            segments[-1].text,
            "2026-10-12 09:18:30 INFO Application health check passed",
        )