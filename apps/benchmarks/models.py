from django.conf import settings
from django.db import models

from apps.workspaces.models import Workspace
from apps.search.services.normalization import UNICODE_NORMALIZATION_CHOICES


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
    case_sensitive = models.BooleanField(default=True)
    unicode_normalization = models.CharField(
        max_length=4,
        choices=UNICODE_NORMALIZATION_CHOICES,
        default="none",
    )
    python_version = models.CharField(max_length=20, blank=True)
    platform_name = models.CharField(max_length=255, blank=True)

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

    progress_percent = models.PositiveSmallIntegerField(default=0)
    progress_message = models.CharField(max_length=255, blank=True)
    progress_lines_processed = models.PositiveIntegerField(default=0)
    progress_total_lines = models.PositiveIntegerField(default=0)

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

    # Representative total timing.
    #
    # This remains the compatibility field used by the existing
    # benchmark/reporting code.
    elapsed_seconds = models.FloatField()

    # Phase-aware representative timings.
    #
    # preprocessing_seconds:
    # Time required to prepare algorithm-specific state.
    #
    # search_seconds:
    # Time required to search the text using the prepared state.
    #
    # total_seconds:
    # Time for the complete preprocessing + search operation.
    preprocessing_seconds = models.FloatField(
        default=0.0,
    )

    search_seconds = models.FloatField(
        default=0.0,
    )

    total_seconds = models.FloatField(
        default=0.0,
    )

    # Repeated-trial methodology metadata.
    warmup_runs = models.PositiveIntegerField(
        default=0,
    )

    trial_count = models.PositiveIntegerField(
        default=1,
    )

    # Statistical timing summary for total execution.
    median_seconds = models.FloatField(
        default=0.0,
    )

    minimum_seconds = models.FloatField(
        default=0.0,
    )

    maximum_seconds = models.FloatField(
        default=0.0,
    )

    # Raw total timings retained for reproducibility.
    trial_times_seconds = models.JSONField(
        default=list,
    )

    # Raw phase timings retained for reproducibility.
    preprocessing_trial_times_seconds = models.JSONField(
        default=list,
    )

    search_trial_times_seconds = models.JSONField(
        default=list,
    )

    total_trial_times_seconds = models.JSONField(
        default=list,
    )

    # Statistical summary for preprocessing.
    preprocessing_median_seconds = models.FloatField(
        default=0.0,
    )

    preprocessing_minimum_seconds = models.FloatField(
        default=0.0,
    )

    preprocessing_maximum_seconds = models.FloatField(
        default=0.0,
    )

    # Statistical summary for search.
    search_median_seconds = models.FloatField(
        default=0.0,
    )

    search_minimum_seconds = models.FloatField(
        default=0.0,
    )

    search_maximum_seconds = models.FloatField(
        default=0.0,
    )

    # Statistical summary for total execution.
    total_median_seconds = models.FloatField(
        default=0.0,
    )

    total_minimum_seconds = models.FloatField(
        default=0.0,
    )

    total_maximum_seconds = models.FloatField(
        default=0.0,
    )

    # Rabin–Karp diagnostic metrics.
    #
    # These remain zero for Naive and KMP.
    #
    # verification_count:
    # Number of hash matches that required character-by-character
    # verification.
    #
    # collision_count:
    # Number of hash matches that failed character-by-character
    # verification because of a hash collision.
    verification_count = models.PositiveIntegerField(
        default=0,
    )

    collision_count = models.PositiveIntegerField(
        default=0,
    )

    match_count = models.PositiveIntegerField()

    positions = models.JSONField(
        default=list,
    )

    text_length = models.PositiveIntegerField()
    peak_memory_bytes = models.PositiveBigIntegerField(null=True, blank=True)

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
