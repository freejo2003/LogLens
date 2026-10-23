from django.conf import settings
from django.db import models

from apps.workspaces.models import Workspace
from apps.search.services.normalization import UNICODE_NORMALIZATION_CHOICES


class IndicatorRule(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="indicator_rules",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="indicator_rules",
    )
    name = models.CharField(max_length=200)
    pattern = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_indicator_rule_workspace_name",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["workspace", "is_active"]),
        ]

    def __str__(self):
        return self.name


class SavedSearch(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="saved_searches",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_searches",
    )
    source_file = models.ForeignKey(
        "ingestion.SourceFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="saved_searches",
    )
    source_checksum = models.CharField(
        max_length=64,
        blank=True,
    )
    name = models.CharField(max_length=200)
    pattern = models.TextField()
    algorithm = models.CharField(max_length=50)
    case_sensitive = models.BooleanField(default=True)
    unicode_normalization = models.CharField(
        max_length=4,
        choices=UNICODE_NORMALIZATION_CHOICES,
        default="none",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_saved_search_owner_name",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
            models.Index(fields=["workspace", "is_active"]),
        ]

    def __str__(self):
        return self.name


class SearchRun(models.Model):
    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="search_runs",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_runs",
    )
    saved_search = models.ForeignKey("search.SavedSearch", null=True, blank=True, on_delete=models.SET_NULL, related_name="runs")
    source_file = models.ForeignKey(
        "ingestion.SourceFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_runs",
    )
    indicator_rule = models.ForeignKey(
        IndicatorRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_runs",
    )
    indicator_name_snapshot = models.CharField(max_length=200, blank=True)
    pattern = models.TextField()
    algorithm = models.CharField(max_length=50)
    case_sensitive = models.BooleanField(default=True)
    unicode_normalization = models.CharField(
        max_length=4,
        choices=UNICODE_NORMALIZATION_CHOICES,
        default="none",
    )
    level_filter = models.CharField(max_length=10, blank=True)
    source_checksum = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUCCEEDED,
    )
    total_match_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["workspace", "-created_at"]),
            models.Index(fields=["source_file", "-created_at"]),
        ]

    def __str__(self):
        return f"Search #{self.pk} — {self.pattern!r} — {self.algorithm}"

    @property
    def duration_seconds(self):
        if self.completed_at is None:
            return None
        return max(0.0, (self.completed_at - self.created_at).total_seconds())


class SearchBatch(models.Model):
    """Asynchronous, cancellable matrix of files and literal patterns."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCEL_REQUESTED = "cancel_requested", "Cancellation requested"
        CANCELLED = "cancelled", "Cancelled"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="search_batches")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_batches")
    algorithm = models.CharField(max_length=50)
    case_sensitive = models.BooleanField(default=True)
    unicode_normalization = models.CharField(max_length=4, choices=UNICODE_NORMALIZATION_CHOICES, default="none")
    level_filter = models.CharField(max_length=10, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.QUEUED)
    total_items = models.PositiveIntegerField(default=0)
    completed_items = models.PositiveIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class SearchBatchItem(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    batch = models.ForeignKey(SearchBatch, on_delete=models.CASCADE, related_name="items")
    source_file = models.ForeignKey("ingestion.SourceFile", on_delete=models.CASCADE, related_name="search_batch_items")
    pattern = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    search_run = models.ForeignKey(SearchRun, null=True, blank=True, on_delete=models.SET_NULL, related_name="batch_items")

    class Meta:
        ordering = ["source_file__original_name", "id"]
        constraints = [models.UniqueConstraint(fields=["batch", "source_file", "pattern"], name="unique_batch_file_pattern")]


class MatchResult(models.Model):
    search_run = models.ForeignKey(
        SearchRun,
        on_delete=models.CASCADE,
        related_name="match_results",
    )
    source_file = models.ForeignKey(
        "ingestion.SourceFile",
        on_delete=models.CASCADE,
        related_name="match_results",
    )
    segment = models.ForeignKey(
        "ingestion.TextSegment",
        on_delete=models.CASCADE,
        related_name="match_results",
    )
    positions = models.JSONField(default=list)
    match_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["segment__sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["search_run", "segment"],
                name="unique_search_run_segment",
            ),
        ]
        indexes = [
            models.Index(fields=["search_run", "segment"]),
            models.Index(fields=["source_file", "segment"]),
        ]

    def __str__(self):
        return (
            f"Search #{self.search_run_id} — "
            f"{self.source_file.original_name} — "
            f"segment {self.segment.sequence}"
        )


class ErrorGroup(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="error_groups",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="error_groups",
    )
    name = models.CharField(max_length=255)
    normalized_message = models.TextField()
    occurrence_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurrence_count", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "normalized_message"],
                name="unique_error_group_workspace_message",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "-occurrence_count"]),
            models.Index(fields=["workspace", "-occurrence_count"]),
        ]

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    error_group = models.ForeignKey(
        ErrorGroup,
        on_delete=models.CASCADE,
        related_name="members",
    )
    source_file = models.ForeignKey(
        "ingestion.SourceFile",
        on_delete=models.CASCADE,
        related_name="error_group_members",
    )
    segment = models.ForeignKey(
        "ingestion.TextSegment",
        on_delete=models.CASCADE,
        related_name="error_group_members",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["source_file", "segment__sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["error_group", "segment"],
                name="unique_error_group_segment",
            ),
        ]
        indexes = [
            models.Index(fields=["error_group", "segment"]),
            models.Index(fields=["source_file", "segment"]),
        ]

    def __str__(self):
        return (
            f"{self.error_group.name} — "
            f"{self.source_file.original_name} — "
            f"segment {self.segment.sequence}"
        )
