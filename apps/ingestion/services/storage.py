import hashlib
import uuid
from pathlib import Path

from django.conf import settings


def generate_storage_key(extension: str) -> str:
    """Generate a private, non-user-controlled storage key."""
    unique_id = uuid.uuid4().hex
    return f"uploads/{unique_id}{extension.lower()}"


def calculate_sha256(file_obj) -> str:
    """Calculate the SHA-256 checksum of an uploaded file."""
    sha256 = hashlib.sha256()

    for chunk in file_obj.chunks():
        sha256.update(chunk)

    file_obj.seek(0)

    return sha256.hexdigest()


def save_private_file(file_obj, storage_key: str) -> str:
    """Save an uploaded file under the private media root."""
    destination = Path(settings.PRIVATE_MEDIA_ROOT) / storage_key

    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("wb") as destination_file:
        for chunk in file_obj.chunks():
            destination_file.write(chunk)

    file_obj.seek(0)

    return str(destination)