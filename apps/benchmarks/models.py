from django.conf import settings
from django.db import models

from apps.workspaces.models import Workspace


class BenchmarkRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="benchmark_runs",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="benchmark_runs",
    )

    source_file = models.ForeignKey(
        "ingestion.SourceFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="benchmark_runs",
    )

    pattern = models.TextField()

    source_checksum = models.CharField(
        max_length=64,
        blank=True,
    )

    input_checksum = models.CharField(
        max_length=64,
        blank=True,
    )

    text_length = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    positions_consistent = models.BooleanField(
        default=False,
    )

    error_message = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["owner", "-created_at"],
            ),
            models.Index(
                fields=["workspace", "-created_at"],
            ),
            models.Index(
                fields=["source_file", "-created_at"],
            ),
        ]

    def __str__(self):
        return (
            f"Benchmark #{self.pk} — "
            f"{self.pattern!r}"
        )


class AlgorithmMetric(models.Model):
    benchmark_run = models.ForeignKey(
        BenchmarkRun,
        on_delete=models.CASCADE,
        related_name="algorithm_metrics",
    )

    algorithm = models.CharField(
        max_length=50,
    )

    algorithm_version = models.CharField(
        max_length=20,
        default="1.0",
    )

    elapsed_seconds = models.FloatField()

    match_count = models.PositiveIntegerField()

    positions = models.JSONField(
        default=list,
    )

    text_length = models.PositiveIntegerField()

    class Meta:
        ordering = ["algorithm"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "benchmark_run",
                    "algorithm",
                ],
                name="unique_benchmark_algorithm",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "benchmark_run",
                    "algorithm",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.benchmark_run_id} — "
            f"{self.algorithm}"
        )