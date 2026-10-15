import codecs
import zipfile
from pathlib import Path

from django.conf import settings


ALLOWED_EXTENSIONS = {".log", ".txt", ".pdf", ".docx", ".doc"}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE
MAX_DOCX_UNCOMPRESSED_SIZE = int(
    getattr(settings, "MAX_DOCX_UNCOMPRESSED_SIZE", 100 * 1024 * 1024)
)
MAX_DOCX_MEMBERS = 10_000


class UploadValidationError(ValueError):
    """Raised when an uploaded file fails validation."""


def validate_extension(filename: str) -> str:
    extension = Path(filename.replace("\\", "/")).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise UploadValidationError(
            f"Unsupported file type '{extension or '[none]'}'. Allowed types: {allowed}."
        )
    return extension


def validate_file_size(file_obj) -> None:
    size = getattr(file_obj, "size", None)
    if not isinstance(size, int) or size < 0:
        raise UploadValidationError("The uploaded file size could not be verified.")
    if size > MAX_FILE_SIZE:
        raise UploadValidationError(
            f"File is too large. Maximum allowed size is {MAX_FILE_SIZE // (1024 * 1024)} MB."
        )


def detect_text_encoding(file_obj) -> str:
    """Validate a bounded text upload and return its supported encoding."""
    position = file_obj.tell()
    file_obj.seek(0)
    prefix = file_obj.read(4)
    file_obj.seek(0)

    if prefix.startswith(codecs.BOM_UTF32_LE) or prefix.startswith(codecs.BOM_UTF32_BE):
        candidates = ("utf-32",)
    elif prefix.startswith(codecs.BOM_UTF16_LE) or prefix.startswith(codecs.BOM_UTF16_BE):
        candidates = ("utf-16",)
    elif prefix.startswith(codecs.BOM_UTF8):
        candidates = ("utf-8-sig",)
    else:
        candidates = ("utf-8", "cp1252")

    try:
        for encoding in candidates:
            file_obj.seek(0)
            decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
            try:
                while chunk := file_obj.read(64 * 1024):
                    decoded = decoder.decode(chunk)
                    if "\x00" in decoded:
                        raise UploadValidationError(
                            "The uploaded file contains binary data, not plain text."
                        )
                decoder.decode(b"", final=True)
                return encoding
            except UnicodeDecodeError:
                continue

        raise UploadValidationError(
            "The uploaded text file is not valid UTF-8, UTF-16, or Windows-1252 text."
        )
    finally:
        file_obj.seek(position)


def validate_text_file(file_obj) -> str:
    return detect_text_encoding(file_obj)


def _validate_docx_archive(file_obj) -> None:
    position = file_obj.tell()
    file_obj.seek(0)
    try:
        with zipfile.ZipFile(file_obj) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_DOCX_MEMBERS:
                raise UploadValidationError("The DOCX archive contains too many items.")
            if sum(item.file_size for item in entries) > MAX_DOCX_UNCOMPRESSED_SIZE:
                raise UploadValidationError(
                    "The DOCX expands beyond the allowed document size."
                )
            names = {item.filename for item in entries}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise UploadValidationError("The uploaded file is not a valid DOCX document.")
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        if isinstance(exc, UploadValidationError):
            raise
        raise UploadValidationError("The uploaded file is not a valid DOCX document.") from exc
    finally:
        file_obj.seek(position)


def validate_file_signature(file_obj, extension: str) -> str:
    """Check format signatures and return the detected media type."""
    extension = extension.lower()
    position = file_obj.tell()
    file_obj.seek(0)
    header = file_obj.read(8)
    file_obj.seek(position)

    if extension == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise UploadValidationError("The uploaded file does not appear to be a valid PDF.")
        return "application/pdf"
    if extension == ".docx":
        _validate_docx_archive(file_obj)
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if extension == ".doc":
        if header != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise UploadValidationError(
                "The uploaded file does not appear to be a valid legacy DOC file."
            )
        return "application/msword"
    if extension in {".log", ".txt"}:
        detect_text_encoding(file_obj)
        return "text/plain"
    raise UploadValidationError("Unsupported file type.")
