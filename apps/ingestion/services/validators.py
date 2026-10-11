from pathlib import Path


ALLOWED_EXTENSIONS = {
    ".log",
    ".txt",
    ".pdf",
    ".docx",
    ".doc",
}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


class UploadValidationError(ValueError):
    """Raised when an uploaded file fails validation."""


def validate_extension(filename: str) -> str:
    """Validate and return the normalized file extension."""
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise UploadValidationError(
            f"Unsupported file type '{extension or '[none]'}'. "
            f"Allowed types: {allowed}."
        )

    return extension


def validate_file_size(file_obj) -> None:
    """Validate the uploaded file size."""
    if file_obj.size > MAX_FILE_SIZE:
        raise UploadValidationError(
            f"File is too large. Maximum allowed size is "
            f"{MAX_FILE_SIZE // (1024 * 1024)} MB."
        )


def validate_file_signature(file_obj, extension: str) -> None:
    """Perform basic content/signature validation."""
    extension = extension.lower()

    current_position = file_obj.tell()
    file_obj.seek(0)

    header = file_obj.read(8)

    file_obj.seek(current_position)

    if extension == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise UploadValidationError(
                "The uploaded file does not appear to be a valid PDF."
            )

    elif extension == ".docx":
        if not header.startswith(b"PK"):
            raise UploadValidationError(
                "The uploaded file does not appear to be a valid DOCX file."
            )

    elif extension == ".doc":
        if header != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise UploadValidationError(
                "The uploaded file does not appear to be a valid legacy DOC file."
            )

    elif extension in {".log", ".txt"}:
        validate_text_file(file_obj)


def validate_text_file(file_obj) -> None:
    """Ensure a LOG/TXT file can be decoded as UTF-8 text."""
    current_position = file_obj.tell()
    file_obj.seek(0)

    try:
        while True:
            chunk = file_obj.read(64 * 1024)

            if not chunk:
                break

            if isinstance(chunk, str):
                continue

            chunk.decode("utf-8")

    except UnicodeDecodeError as exc:
        raise UploadValidationError(
            "The uploaded text file could not be decoded as UTF-8."
        ) from exc

    finally:
        file_obj.seek(current_position)