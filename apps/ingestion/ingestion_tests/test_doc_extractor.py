import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ingestion.models import SourceFile, TextSegment
from apps.ingestion.services.doc_extractor import extract_doc_file
from apps.ingestion.services.errors import ExtractionError
from apps.workspaces.models import Workspace


class LegacyDocExtractionTests(TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        source_path = Path(self.temp_directory.name) / "legacy.doc"
        source_path.write_bytes(b"test legacy document")
        user = get_user_model().objects.create_user(
            username="legacy-doc-owner",
            password="test-password",
        )
        workspace = Workspace.objects.create(name="Legacy DOC", owner=user)
        self.source_file = SourceFile.objects.create(
            workspace=workspace,
            owner=user,
            original_name="legacy.doc",
            storage_key="uploads/legacy-test.doc",
            storage_path=str(source_path),
            extension=".doc",
            detected_type="application/msword",
            byte_size=source_path.stat().st_size,
            checksum="b" * 64,
        )

    def tearDown(self):
        self.temp_directory.cleanup()

    @patch("apps.ingestion.services.doc_extractor.shutil.which", return_value="libreoffice")
    @patch("apps.ingestion.services.doc_extractor.subprocess.run")
    def test_doc_conversion_writes_located_segments_in_private_temp_storage(
        self, run_process, _which
    ):
        temporary_paths = []

        def convert(command, **kwargs):
            output_directory = Path(command[command.index("--outdir") + 1])
            temporary_paths.append(output_directory.parent)
            (output_directory / "legacy.txt").write_bytes(b"first line\nsecond line\n")
            self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(kwargs["timeout"], 60)
            self.assertNotIn("shell", kwargs)
            return subprocess.CompletedProcess(command, 0)

        run_process.side_effect = convert
        count = extract_doc_file(self.source_file)

        self.assertEqual(count, 2)
        segments = list(TextSegment.objects.filter(source_file=self.source_file))
        self.assertEqual([item.line_number for item in segments], [1, 2])
        self.assertEqual([item.text for item in segments], ["first line", "second line"])
        self.assertEqual(segments[0].parser_name, "libreoffice")
        self.assertFalse(temporary_paths[0].exists())

    @patch("apps.ingestion.services.doc_extractor.shutil.which", return_value="libreoffice")
    @patch("apps.ingestion.services.doc_extractor.subprocess.run")
    def test_doc_conversion_timeout_returns_a_safe_error(self, run_process, _which):
        run_process.side_effect = subprocess.TimeoutExpired("libreoffice", 60)
        with self.assertRaisesRegex(ExtractionError, "time limit"):
            extract_doc_file(self.source_file)

    @patch("apps.ingestion.services.doc_extractor.shutil.which", return_value=None)
    def test_missing_libreoffice_returns_a_safe_error(self, _which):
        with self.assertRaisesRegex(ExtractionError, "requires LibreOffice"):
            extract_doc_file(self.source_file)

    @patch("apps.ingestion.services.doc_extractor.shutil.which", return_value="libreoffice")
    @patch("apps.ingestion.services.doc_extractor.subprocess.run")
    def test_failed_conversion_does_not_create_segments(self, run_process, _which):
        run_process.return_value = subprocess.CompletedProcess("libreoffice", 1)
        with self.assertRaisesRegex(ExtractionError, "could not be converted"):
            extract_doc_file(self.source_file)
        self.assertFalse(TextSegment.objects.filter(source_file=self.source_file).exists())
