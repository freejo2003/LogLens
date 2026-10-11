from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from apps.ingestion.services.storage import (
    calculate_sha256,
    delete_private_file,
    generate_storage_key,
    save_private_file,
)


class GenerateStorageKeyTests(SimpleTestCase):
    def test_generates_expected_format(self):
        storage_key = generate_storage_key(".pdf")

        self.assertTrue(storage_key.startswith("uploads/"))
        self.assertTrue(storage_key.endswith(".pdf"))

    def test_normalizes_extension_to_lowercase(self):
        storage_key = generate_storage_key(".PDF")

        self.assertTrue(storage_key.endswith(".pdf"))

    def test_generates_unique_keys(self):
        first = generate_storage_key(".txt")
        second = generate_storage_key(".txt")

        self.assertNotEqual(first, second)


class CalculateSha256Tests(SimpleTestCase):
    def test_calculates_correct_checksum(self):
        file_obj = SimpleUploadedFile(
            "test.txt",
            b"hello loglens",
        )

        checksum = calculate_sha256(file_obj)

        self.assertEqual(len(checksum), 64)
        self.assertEqual(file_obj.tell(), 0)


@override_settings(
    PRIVATE_MEDIA_ROOT=Path(settings.BASE_DIR) / "test_private_media"
)
class PrivateFileStorageTests(SimpleTestCase):
    def setUp(self):
        self.test_root = Path(settings.PRIVATE_MEDIA_ROOT)
        self.test_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.test_root.exists():
            for path in sorted(
                self.test_root.rglob("*"),
                reverse=True,
            ):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()

            self.test_root.rmdir()

    def test_save_private_file_creates_file(self):
        file_obj = SimpleUploadedFile(
            "test.txt",
            b"test private content",
        )

        storage_key = "uploads/test-file.txt"

        storage_path = save_private_file(
            file_obj,
            storage_key,
        )

        path = Path(storage_path)

        self.assertTrue(path.exists())
        self.assertTrue(path.is_file())
        self.assertEqual(
            path.read_bytes(),
            b"test private content",
        )

    def test_delete_private_file_removes_file(self):
        file_obj = SimpleUploadedFile(
            "delete.txt",
            b"content to delete",
        )

        storage_key = "uploads/delete-me.txt"

        storage_path = save_private_file(
            file_obj,
            storage_key,
        )

        self.assertTrue(Path(storage_path).exists())

        delete_private_file(storage_path)

        self.assertFalse(Path(storage_path).exists())

    def test_delete_private_file_is_safe_for_missing_file(self):
        missing_path = (
            self.test_root
            / "uploads"
            / "does-not-exist.txt"
        )

        delete_private_file(str(missing_path))

        self.assertFalse(missing_path.exists())