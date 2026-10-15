from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.ingestion.forms import SourceFileUploadForm
from apps.ingestion.services.validators import MAX_FILE_SIZE
from apps.workspaces.models import Workspace


class SourceFileUploadFormTests(TestCase):
    def setUp(self):
        self.user = self._create_user()

        self.workspace = Workspace.objects.create(
            name="Upload Form Workspace",
            owner=self.user,
        )

    def _create_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        return User.objects.create_user(
            username="upload-form-user",
            password="test-password",
        )

    def _form(self, uploaded_file):
        return SourceFileUploadForm(
            data={
                "workspace": self.workspace.id,
            },
            files={
                "files": uploaded_file,
            },
            user=self.user,
        )

    def test_valid_log_file_is_accepted(self):
        uploaded_file = SimpleUploadedFile(
            "application.log",
            b"INFO Application started\n",
            content_type="text/plain",
        )

        form = self._form(uploaded_file)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["files"]), 1)
        self.assertEqual(form.cleaned_data["files"][0].loglens_encoding, "utf-8")

    def test_multiple_valid_files_are_accepted_in_one_upload(self):
        files = [
            SimpleUploadedFile("first.log", b"INFO one\n", content_type="text/plain"),
            SimpleUploadedFile("second.txt", b"INFO two\n", content_type="text/plain"),
        ]
        form = SourceFileUploadForm(
            data={"workspace": self.workspace.id},
            files={"files": files},
            user=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["files"]), 2)

    def test_unsupported_extension_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "malware.exe",
            b"MZ fake executable content",
            content_type="application/octet-stream",
        )

        form = self._form(uploaded_file)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["files"], [])
        self.assertEqual(len(form.upload_errors), 1)

    def test_oversized_file_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "large.log",
            b"x",
            content_type="text/plain",
        )

        uploaded_file.size = MAX_FILE_SIZE + 1

        form = self._form(uploaded_file)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.upload_errors), 1)

    def test_invalid_pdf_signature_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "document.pdf",
            b"this is not a PDF",
            content_type="application/pdf",
        )

        form = self._form(uploaded_file)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.upload_errors), 1)

    def test_invalid_docx_signature_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "document.docx",
            b"this is not a DOCX file",
            content_type=(
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
        )

        form = self._form(uploaded_file)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.upload_errors), 1)

    def test_invalid_legacy_doc_signature_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "document.doc",
            b"this is not a legacy DOC file",
            content_type="application/msword",
        )

        form = self._form(uploaded_file)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.upload_errors), 1)

    def test_invalid_utf8_text_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "application.txt",
            b"\x00\x01\xff\xfe",
            content_type="text/plain",
        )

        form = self._form(uploaded_file)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.upload_errors), 1)

    def test_windows_1252_text_is_accepted_and_recorded(self):
        uploaded_file = SimpleUploadedFile(
            "legacy.log",
            "caf\u00e9 failure\n".encode("cp1252"),
            content_type="text/plain",
        )
        form = self._form(uploaded_file)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["files"][0].loglens_encoding, "cp1252")

    @override_settings(MAX_UPLOAD_BATCH_SIZE=10)
    def test_total_batch_size_limit_is_enforced(self):
        uploads = [
            SimpleUploadedFile("one.log", b"123456", content_type="text/plain"),
            SimpleUploadedFile("two.log", b"abcdef", content_type="text/plain"),
        ]
        form = SourceFileUploadForm(
            data={"workspace": self.workspace.id},
            files={"files": uploads},
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["files"]), 1)
        self.assertEqual(len(form.upload_errors), 1)
