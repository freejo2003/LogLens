from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.test import SimpleTestCase

from apps.ingestion.services.validators import (
    MAX_FILE_SIZE,
    UploadValidationError,
    validate_extension,
    validate_file_signature,
    validate_file_size,
)


class ValidateExtensionTests(SimpleTestCase):
    def test_allowed_extensions_are_accepted(self):
        for filename in [
            "application.log",
            "application.txt",
            "document.pdf",
            "document.docx",
            "document.doc",
        ]:
            with self.subTest(filename=filename):
                extension = validate_extension(filename)
                self.assertIn(extension, {".log", ".txt", ".pdf", ".docx", ".doc"})

    def test_extension_is_normalized_to_lowercase(self):
        self.assertEqual(validate_extension("REPORT.PDF"), ".pdf")

    def test_unsupported_extension_is_rejected(self):
        with self.assertRaises(UploadValidationError):
            validate_extension("malware.exe")

    def test_missing_extension_is_rejected(self):
        with self.assertRaises(UploadValidationError):
            validate_extension("README")


class ValidateFileSizeTests(SimpleTestCase):
    def test_file_within_limit_is_accepted(self):
        file_obj = BytesIO(b"small file")
        file_obj.size = len(file_obj.getvalue())

        validate_file_size(file_obj)

    def test_file_over_limit_is_rejected(self):
        file_obj = BytesIO(b"small file")
        file_obj.size = MAX_FILE_SIZE + 1

        with self.assertRaises(UploadValidationError):
            validate_file_size(file_obj)


class ValidateFileSignatureTests(SimpleTestCase):
    def test_valid_pdf_is_accepted(self):
        file_obj = BytesIO(b"%PDF-1.7\nsample pdf content")

        validate_file_signature(file_obj, ".pdf")

    def test_invalid_pdf_is_rejected(self):
        file_obj = BytesIO(b"not a pdf file")

        with self.assertRaises(UploadValidationError):
            validate_file_signature(file_obj, ".pdf")

    def test_valid_docx_is_accepted(self):
        file_obj = BytesIO()
        with ZipFile(file_obj, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        file_obj.seek(0)

        validate_file_signature(file_obj, ".docx")

    def test_invalid_docx_is_rejected(self):
        file_obj = BytesIO(b"not a docx file")

        with self.assertRaises(UploadValidationError):
            validate_file_signature(file_obj, ".docx")

    def test_valid_legacy_doc_is_accepted(self):
        file_obj = BytesIO(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1sample doc")

        validate_file_signature(file_obj, ".doc")

    def test_invalid_legacy_doc_is_rejected(self):
        file_obj = BytesIO(b"not a doc file")

        with self.assertRaises(UploadValidationError):
            validate_file_signature(file_obj, ".doc")

    def test_valid_utf8_text_is_accepted(self):
        file_obj = BytesIO("Log entry: user login successful".encode("utf-8"))

        validate_file_signature(file_obj, ".log")

    def test_invalid_utf8_text_is_rejected(self):
        file_obj = BytesIO(b"\x00\x01\xff\xfe")

        with self.assertRaises(UploadValidationError):
            validate_file_signature(file_obj, ".txt")
