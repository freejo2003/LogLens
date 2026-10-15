import hashlib
import uuid
from pathlib import Path, PurePosixPath

from django.conf import settings


_ALLOWED_EXTENSIONS = {".log", ".txt", ".pdf", ".docx", ".doc"}


def generate_storage_key(extension: str) -> str:
    normalized_extension = extension.lower()
    if normalized_extension not in _ALLOWED_EXTENSIONS:
        raise ValueError("Cannot generate a storage key for an unsupported file type.")
    return f"uploads/{uuid.uuid4().hex}{normalized_extension}"


def calculate_sha256(file_obj) -> str:
    sha256 = hashlib.sha256()
    for chunk in file_obj.chunks():
        sha256.update(chunk)
    file_obj.seek(0)
    return sha256.hexdigest()


def resolve_private_path(path_value: str | Path) -> Path:
    root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=False)
    if resolved == root or root not in resolved.parents:
        raise ValueError("The storage path is outside private storage.")
    return resolved


def _private_key_path(storage_key: str) -> Path:
    key = PurePosixPath(storage_key)
    if (
        key.is_absolute()
        or len(key.parts) != 2
        or key.parts[0] != "uploads"
        or any(part in {"", ".", ".."} for part in key.parts)
        or "\\" in storage_key
        or Path(key.name).suffix.lower() not in _ALLOWED_EXTENSIONS
    ):
        raise ValueError("The storage key is invalid.")
    return resolve_private_path(Path(*key.parts))


def save_private_file(file_obj, storage_key: str) -> str:
    destination = _private_key_path(storage_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Resolve again after directory creation to defend against pre-existing symlinks.
    destination = resolve_private_path(destination)
    created = False
    bytes_written = 0
    try:
        with destination.open("xb") as destination_file:
            created = True
            for chunk in file_obj.chunks():
                bytes_written += len(chunk)
                if bytes_written > settings.MAX_UPLOAD_SIZE:
                    raise ValueError("The uploaded file exceeds the configured size limit.")
                destination_file.write(chunk)
    except Exception:
        if created and destination.exists():
            destination.unlink()
        raise
    finally:
        file_obj.seek(0)
    return str(destination)


def delete_private_file(storage_path: str) -> None:
    path = resolve_private_path(storage_path)
    if path.exists() and path.is_file():
        path.unlink()
