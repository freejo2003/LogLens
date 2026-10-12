from django.db import transaction

from apps.ingestion.models import SourceFile
from apps.ingestion.services.storage import delete_private_file


def delete_source_file(*, source_file: SourceFile, owner) -> None:
    """
    Delete a source file owned by the given user.

    The physical private file is removed first. The database record is
    then deleted inside a transaction. TextSegment records are removed
    through the SourceFile foreign-key cascade.
    """
    if source_file.owner_id != owner.id:
        raise PermissionError(
            "You do not have permission to delete this source file."
        )

    storage_path = source_file.storage_path

    with transaction.atomic():
        delete_private_file(storage_path)
        source_file.delete()