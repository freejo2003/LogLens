import re

from django.db import transaction

from apps.ingestion.models import SourceFile, TextSegment
from apps.search.models import ErrorGroup, GroupMember


# Common timestamp prefix used by the LogLens test corpus.
TIMESTAMP_PREFIX_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+"
)

# Log severity prefix.
LOG_LEVEL_PATTERN = re.compile(
    r"^(?:DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\s+",
    re.IGNORECASE,
)

# Key/value metadata at the end of a message.
KEY_VALUE_PATTERN = re.compile(
    r"\s+\b[a-zA-Z_][a-zA-Z0-9_]*="
    r"(?:\"[^\"]*\"|'[^']*'|\S+)"
)

# Standalone duration values such as "3200ms".
DURATION_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?(?:ms|s|sec|secs|seconds|milliseconds)\b",
    re.IGNORECASE,
)


def normalize_error_message(text: str) -> str:
    """
    Normalize a log message into a deterministic error template.

    Current rules:

    1. Validate that the input is a string.
    2. Strip leading/trailing whitespace.
    3. Remove the standard timestamp prefix.
    4. Remove the log severity prefix.
    5. Remove trailing key/value metadata such as:
       - user=alice
       - user=bob
       - endpoint=/api/orders
       - path=/reports/daily.csv
       - reason=connection timeout
       - duration=3200ms
    6. Remove standalone duration values.
    7. Collapse repeated whitespace.
    8. Case-fold the result.

    The normalization intentionally does NOT remove all numbers.
    Meaningful values such as HTTP status codes remain part of the
    normalized template.
    """
    if not isinstance(text, str):
        raise TypeError("Error message must be a string.")

    normalized = text.strip()

    if not normalized:
        return ""

    # Remove timestamp from the beginning.
    normalized = TIMESTAMP_PREFIX_PATTERN.sub("", normalized)

    # Remove severity level from the beginning.
    normalized = LOG_LEVEL_PATTERN.sub("", normalized)

    # Remove key/value metadata.
    normalized = KEY_VALUE_PATTERN.sub("", normalized)

    # Remove standalone duration values.
    normalized = DURATION_PATTERN.sub("", normalized)

    # Collapse whitespace introduced by the removals.
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Make grouping case-insensitive and deterministic.
    return normalized.casefold()


def build_error_group_name(normalized_message: str) -> str:
    if not normalized_message:
        return "Unnamed Error"

    return normalized_message[:255]


@transaction.atomic
def create_or_get_error_group(
    *,
    owner,
    workspace,
    normalized_message: str,
) -> ErrorGroup:
    if workspace.owner_id != owner.id:
        raise PermissionError(
            "The selected workspace does not belong to the current user."
        )

    if not normalized_message:
        raise ValueError(
            "Cannot create an error group from an empty message."
        )

    group, _ = ErrorGroup.objects.get_or_create(
        workspace=workspace,
        normalized_message=normalized_message,
        defaults={
            "owner": owner,
            "name": build_error_group_name(normalized_message),
        },
    )

    return group


@transaction.atomic
def add_segment_to_error_group(
    *,
    owner,
    error_group: ErrorGroup,
    source_file: SourceFile,
    segment: TextSegment,
) -> GroupMember:
    if error_group.owner_id != owner.id:
        raise PermissionError(
            "The error group does not belong to the current user."
        )

    if source_file.owner_id != owner.id:
        raise PermissionError(
            "The source file does not belong to the current user."
        )

    if segment.source_file_id != source_file.id:
        raise ValueError(
            "The selected segment does not belong to the source file."
        )

    if source_file.workspace_id != error_group.workspace_id:
        raise ValueError(
            "The source file and error group belong to different workspaces."
        )

    member, created = GroupMember.objects.get_or_create(
        error_group=error_group,
        source_file=source_file,
        segment=segment,
    )

    if created:
        ErrorGroup.objects.filter(pk=error_group.pk).update(
            occurrence_count=error_group.members.count()
        )

        error_group.refresh_from_db(
            fields=["occurrence_count"]
        )

    return member


def group_segment(
    *,
    owner,
    workspace,
    source_file: SourceFile,
    segment: TextSegment,
) -> GroupMember | None:
    if source_file.owner_id != owner.id:
        raise PermissionError(
            "The source file does not belong to the current user."
        )

    if source_file.workspace_id != workspace.id:
        raise ValueError(
            "The source file does not belong to the selected workspace."
        )

    normalized_message = normalize_error_message(segment.text)

    if not normalized_message:
        return None

    error_group = create_or_get_error_group(
        owner=owner,
        workspace=workspace,
        normalized_message=normalized_message,
    )

    return add_segment_to_error_group(
        owner=owner,
        error_group=error_group,
        source_file=source_file,
        segment=segment,
    )


def group_source_file(
    *,
    owner,
    source_file: SourceFile,
) -> list[GroupMember]:
    if source_file.owner_id != owner.id:
        raise PermissionError(
            "The source file does not belong to the current user."
        )

    segments = (
        TextSegment.objects
        .filter(source_file=source_file)
        .order_by("sequence")
    )

    members = []

    for segment in segments:
        member = group_segment(
            owner=owner,
            workspace=source_file.workspace,
            source_file=source_file,
            segment=segment,
        )

        if member is not None:
            members.append(member)

    return members