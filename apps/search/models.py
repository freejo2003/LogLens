from django.conf import settings
from django.db import models

from apps.workspaces.models import Workspace


class SearchRun(models.Model):
    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

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
    source_file = models.ForeignKey(
        "ingestion.SourceFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_runs",
    )
    pattern = models.TextField()
    algorithm = models.CharField(max_length=50)
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