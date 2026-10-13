import re

from django.db import transaction

from apps.ingestion.models import SourceFile, TextSegment
from apps.search.models import ErrorGroup, GroupMember


TIMESTAMP_PREFIX_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+"
)

LOG_LEVEL_PATTERN = re.compile(
    r"^(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\s+",
    re.IGNORECASE,
)

KEY_VALUE_PATTERN = re.compile(
    r"\s+\b[a-zA-Z_][a-zA-Z0-9_]*="
    r"(?:\"[^\"]*\"|'[^']*'|\S+)"
)

DURATION_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?(?:ms|s|sec|secs|seconds|milliseconds)\b",
    re.IGNORECASE,
)

GROUPABLE_LOG_LEVELS = frozenset({"ERROR", "WARN"})


def extract_log_level(text: str) -> str | None:
    if not isinstance(text, str):
        raise TypeError("Log message must be a string.")

    timestamp_match = TIMESTAMP_PREFIX_PATTERN.match(text.strip())

    if not timestamp_match:
        return None

    remaining = text[timestamp_match.end():]

    level_match = LOG_LEVEL_PATTERN.match(remaining)

    if not level_match:
        return None

    return level_match.group(1).upper()


def is_groupable_log_message(text: str) -> bool:
    level = extract_log_level(text)
    return level in GROUPABLE_LOG_LEVELS


def normalize_error_message(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("Log message must be a string.")

    normalized = text.strip()

    if not normalized:
        return ""

    normalized = TIMESTAMP_PREFIX_PATTERN.sub("", normalized)
    normalized = LOG_LEVEL_PATTERN.sub("", normalized)
    normalized = KEY_VALUE_PATTERN.sub("", normalized)
    normalized = DURATION_PATTERN.sub("", normalized)

    normalized = re.sub(r"\s+", " ", normalized).strip()

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

    if not is_groupable_log_message(segment.text):
        return None

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


@transaction.atomic
def rebuild_error_groups_for_source_file(
    *,
    owner,
    source_file: SourceFile,
) -> list[GroupMember]:
    """
    Rebuild ERROR/WARN groups for a source file using bulk database
    operations.

    Normalization and classification are performed in Python first.
    Existing memberships for this source file are removed, then the
    required ErrorGroup and GroupMember records are recreated efficiently.
    """

    if source_file.owner_id != owner.id:
        raise PermissionError(
            "The source file does not belong to the current user."
        )

    workspace = source_file.workspace

    # ---------------------------------------------------------
    # 1. Remove existing memberships for this source file.
    # ---------------------------------------------------------
    existing_group_ids = list(
        GroupMember.objects
        .filter(source_file=source_file)
        .values_list("error_group_id", flat=True)
        .distinct()
    )

    GroupMember.objects.filter(
        source_file=source_file
    ).delete()

    # Delete groups that no longer have any members.
    if existing_group_ids:
        ErrorGroup.objects.filter(
            pk__in=existing_group_ids,
            members__isnull=True,
        ).delete()

    # ---------------------------------------------------------
    # 2. Read all extracted segments once.
    # ---------------------------------------------------------
    segments = list(
        TextSegment.objects
        .filter(source_file=source_file)
        .order_by("sequence")
    )

    # ---------------------------------------------------------
    # 3. Normalize groupable messages in Python.
    #
    #    Mapping:
    #       normalized message -> list of segments
    # ---------------------------------------------------------
    grouped_segments: dict[str, list[TextSegment]] = {}

    for segment in segments:
        if not is_groupable_log_message(segment.text):
            continue

        normalized_message = normalize_error_message(
            segment.text
        )

        if not normalized_message:
            continue

        grouped_segments.setdefault(
            normalized_message,
            [],
        ).append(segment)

    if not grouped_segments:
        return []

    # ---------------------------------------------------------
    # 4. Fetch existing groups for this workspace in one query.
    # ---------------------------------------------------------
    normalized_messages = list(
        grouped_segments.keys()
    )

    existing_groups = {
        group.normalized_message: group
        for group in ErrorGroup.objects.filter(
            workspace=workspace,
            normalized_message__in=normalized_messages,
        )
    }

    # ---------------------------------------------------------
    # 5. Create missing groups in bulk.
    # ---------------------------------------------------------
    missing_groups = [
        ErrorGroup(
            workspace=workspace,
            owner=owner,
            name=build_error_group_name(normalized_message),
            normalized_message=normalized_message,
        )
        for normalized_message in normalized_messages
        if normalized_message not in existing_groups
    ]

    if missing_groups:
        ErrorGroup.objects.bulk_create(
            missing_groups,
            ignore_conflicts=True,
        )

    # ---------------------------------------------------------
    # 6. Fetch the complete group set once more.
    #
    #    This also handles concurrent creation safely.
    # ---------------------------------------------------------
    error_groups = {
        group.normalized_message: group
        for group in ErrorGroup.objects.filter(
            workspace=workspace,
            normalized_message__in=normalized_messages,
        )
    }

    # ---------------------------------------------------------
    # 7. Build GroupMember objects entirely in memory.
    # ---------------------------------------------------------
    members_to_create = []

    for normalized_message, segment_list in grouped_segments.items():
        error_group = error_groups[normalized_message]

        for segment in segment_list:
            members_to_create.append(
                GroupMember(
                    error_group=error_group,
                    source_file=source_file,
                    segment=segment,
                )
            )

    # ---------------------------------------------------------
    # 8. Insert all memberships in one bulk operation.
    # ---------------------------------------------------------
    GroupMember.objects.bulk_create(
        members_to_create,
        batch_size=1000,
    )

    # ---------------------------------------------------------
    # 9. Update occurrence counts for affected groups.
    # ---------------------------------------------------------
    occurrence_counts = {
        normalized_message: len(segment_list)
        for normalized_message, segment_list
        in grouped_segments.items()
    }

    for normalized_message, count in occurrence_counts.items():
        error_group = error_groups[normalized_message]

        ErrorGroup.objects.filter(
            pk=error_group.pk
        ).update(
            occurrence_count=count
        )

        error_group.occurrence_count = count

    # ---------------------------------------------------------
    # 10. Return the newly rebuilt memberships.
    # ---------------------------------------------------------
    return list(
        GroupMember.objects
        .filter(source_file=source_file)
        .select_related(
            "error_group",
            "source_file",
            "segment",
        )
        .order_by("segment__sequence")
    )