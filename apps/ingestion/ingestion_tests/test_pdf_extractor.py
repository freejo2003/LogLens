from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase

from apps.ingestion.models import SourceFile
from apps.ingestion.services.pdf_extractor import extract_pdf_file
from apps.ingestion.services.errors import OCRNeededError, ExtractionError
from apps.workspaces.models import Workspace
from django.contrib.auth import get_user_model


class PdfExtractorTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="pdf-test-user",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="PDF Test Workspace",
            owner=self.user,
        )

    def test_extracts_pdf_pages_into_segments(self):
        from pypdf import PdfWriter

        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "sample.pdf"

            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)

            with pdf_path.open("wb") as file_obj:
                writer.write(file_obj)

            source_file = SourceFile.objects.create(
                workspace=self.workspace,
                owner=self.user,
                original_name="sample.pdf",
                storage_key="uploads/test-sample.pdf",
                storage_path=str(pdf_path),
                extension=".pdf",
                detected_type="application/pdf",
                byte_size=pdf_path.stat().st_size,
                checksum="test-checksum",
            )

            with self.assertRaises(OCRNeededError):
                extract_pdf_file(source_file)

    def test_rejects_non_pdf_file(self):
        source_file = SourceFile(
            workspace=self.workspace,
            owner=self.user,
            original_name="test.txt",
            storage_key="uploads/test.txt",
            storage_path="missing.txt",
            extension=".txt",
            detected_type="text/plain",
            byte_size=10,
            checksum="test-checksum",
        )

        with self.assertRaises(ValueError):
            extract_pdf_file(source_file)

    def test_raises_when_pdf_does_not_exist(self):
        source_file = SourceFile(
            workspace=self.workspace,
            owner=self.user,
            original_name="missing.pdf",
            storage_key="uploads/missing.pdf",
            storage_path="missing.pdf",
            extension=".pdf",
            detected_type="application/pdf",
            byte_size=10,
            checksum="test-checksum",
        )

        with self.assertRaises(ExtractionError):
            extract_pdf_file(source_file)
