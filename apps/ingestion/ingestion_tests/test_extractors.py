from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ingestion.models import SourceFile, TextSegment
from apps.ingestion.services.extractors import extract_text_file
from apps.workspaces.models import Workspace


class TextExtractorTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="extractor-test-user",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Extractor Test Workspace",
            owner=self.user,
        )

    def create_source_file(self, path: Path) -> SourceFile:
        return SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name=path.name,
            storage_key=f"uploads/{path.name}",
            storage_path=str(path),
            extension=path.suffix.lower(),
            detected_type="text/plain",
            byte_size=path.stat().st_size,
            checksum="test-checksum",
        )

    def test_extracts_each_line_into_a_segment(self):
        with TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "sample.txt"

            source_path.write_text(
                "first line\nsecond line\nthird line\n",
                encoding="utf-8",
            )

            source_file = self.create_source_file(source_path)

            count = extract_text_file(source_file)

            self.assertEqual(count, 3)

            segments = list(
                TextSegment.objects.filter(
                    source_file=source_file
                ).order_by("sequence")
            )

            self.assertEqual(len(segments), 3)

            self.assertEqual(segments[0].sequence, 1)
            self.assertEqual(segments[0].text, "first line")
            self.assertEqual(segments[0].line_number, 1)

            self.assertEqual(segments[1].sequence, 2)
            self.assertEqual(segments[1].text, "second line")
            self.assertEqual(segments[1].line_number, 2)

            self.assertEqual(segments[2].sequence, 3)
            self.assertEqual(segments[2].text, "third line")
            self.assertEqual(segments[2].line_number, 3)

            self.assertTrue(
                all(
                    segment.parser_name == "plain_text"
                    for segment in segments
                )
            )

    def test_extracts_log_files(self):
        with TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "application.log"

            source_path.write_text(
                "INFO Application started\n"
                "ERROR Database connection failed\n",
                encoding="utf-8",
            )

            source_file = self.create_source_file(source_path)

            count = extract_text_file(source_file)

            self.assertEqual(count, 2)

            segments = list(
                TextSegment.objects.filter(
                    source_file=source_file
                ).order_by("sequence")
            )

            self.assertEqual(segments[0].text, "INFO Application started")
            self.assertEqual(
                segments[1].text,
                "ERROR Database connection failed",
            )

    def test_rejects_unsupported_extension(self):
        source_file = SourceFile(
            workspace=self.workspace,
            owner=self.user,
            original_name="sample.pdf",
            storage_key="uploads/sample.pdf",
            storage_path="sample.pdf",
            extension=".pdf",
            detected_type="application/pdf",
            byte_size=10,
            checksum="test-checksum",
        )

        with self.assertRaises(ValueError):
            extract_text_file(source_file)