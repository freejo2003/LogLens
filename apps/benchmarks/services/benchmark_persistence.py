import hashlib
import logging
import platform

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent
from apps.benchmarks.models import AlgorithmMetric, BenchmarkRun
from apps.benchmarks.services.benchmark_engine import benchmark_all


ALGORITHM_VERSIONS = {
    "naive": "1.0",
    "kmp": "1.0",
    "rabin_karp": "1.0",
}

logger = logging.getLogger(__name__)


def calculate_input_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_pending_benchmark_run(
    *,
    workspace,
    owner,
    text: str,
    pattern: str,
    source_file=None,
    case_sensitive: bool = True,
    unicode_normalization: str = "none",
) -> BenchmarkRun:
    if workspace.owner_id != owner.id:
        raise PermissionError("The selected workspace does not belong to the current user.")
    if source_file is not None and source_file.owner_id != owner.id:
        raise PermissionError("The source file does not belong to the current user.")

    line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return BenchmarkRun.objects.create(
        workspace=workspace,
        owner=owner,
        source_file=source_file,
        pattern=pattern,
        case_sensitive=case_sensitive,
        unicode_normalization=unicode_normalization,
        python_version=platform.python_version(),
        platform_name=platform.platform(),
        source_checksum=source_file.checksum if source_file is not None else "",
        input_checksum=calculate_input_checksum(text),
        text_length=len(text),
        status=BenchmarkRun.Status.PENDING,
        progress_total_lines=line_count,
        progress_message="Queued for benchmarking.",
    )


def create_benchmark_run(
    *,
    workspace,
    owner,
    text: str,
    pattern: str,
    source_file=None,
    case_sensitive: bool = True,
    unicode_normalization: str = "none",
    benchmark: BenchmarkRun | None = None,
    progress_callback=None,
) -> BenchmarkRun:
    if workspace.owner_id != owner.id:
        raise PermissionError(
            "The selected workspace does not belong to the current user."
        )

    input_checksum = calculate_input_checksum(text)

    source_checksum = ""

    if source_file is not None:
        if source_file.owner_id != owner.id:
            raise PermissionError(
                "The source file does not belong to the current user."
            )

        source_checksum = source_file.checksum

    if benchmark is None:
        benchmark = BenchmarkRun.objects.create(
            workspace=workspace,
            owner=owner,
            source_file=source_file,
            pattern=pattern,
            case_sensitive=case_sensitive,
            unicode_normalization=unicode_normalization,
            python_version=platform.python_version(),
            platform_name=platform.platform(),
            source_checksum=source_checksum,
            input_checksum=input_checksum,
            text_length=len(text),
            status=BenchmarkRun.Status.RUNNING,
        )
    else:
        benchmark.status = BenchmarkRun.Status.RUNNING
        benchmark.progress_message = "Starting benchmark."
        benchmark.save(update_fields=["status", "progress_message"])

    try:
        result = benchmark_all(
            text,
            pattern,
            max_matches=settings.MAX_SEARCH_MATCHES,
            case_sensitive=case_sensitive,
            unicode_normalization=unicode_normalization,
            progress_callback=progress_callback,
        )

        with transaction.atomic():
            benchmark.positions_consistent = result.positions_consistent
            benchmark.status = BenchmarkRun.Status.SUCCEEDED
            benchmark.progress_percent = 100
            benchmark.progress_message = "Benchmark complete."
            benchmark.progress_lines_processed = benchmark.progress_total_lines
            benchmark.completed_at = timezone.now()

            benchmark.save(
                update_fields=[
                    "positions_consistent",
                    "status",
                    "progress_percent",
                    "progress_message",
                    "progress_lines_processed",
                    "completed_at",
                ]
            )
            record_event(
                actor=owner,
                workspace=workspace,
                action=AuditEvent.Action.BENCHMARK_COMPLETED,
                object_type="BenchmarkRun",
                object_id=benchmark.pk,
                details={
                    "positions_consistent": result.positions_consistent,
                    "algorithm_count": len(result.results),
                },
            )

            AlgorithmMetric.objects.bulk_create(
                [
                    AlgorithmMetric(
                        benchmark_run=benchmark,
                        algorithm=metric.algorithm,
                        algorithm_version=ALGORITHM_VERSIONS[
                            metric.algorithm
                        ],

                        # Backward-compatible representative timing.
                        elapsed_seconds=metric.elapsed_seconds,

                        # Phase-aware timing.
                        preprocessing_seconds=(
                            metric.preprocessing_seconds
                        ),
                        search_seconds=metric.search_seconds,
                        total_seconds=metric.total_seconds,

                        # Repeated-trial methodology.
                        warmup_runs=metric.warmup_runs,
                        trial_count=metric.trial_count,

                        # Existing total timing statistics.
                        median_seconds=metric.median_seconds,
                        minimum_seconds=metric.minimum_seconds,
                        maximum_seconds=metric.maximum_seconds,

                        # Existing total raw trial timings.
                        trial_times_seconds=list(
                            metric.trial_times_seconds
                        ),

                        # Phase-specific raw trial timings.
                        preprocessing_trial_times_seconds=list(
                            metric.preprocessing_trial_times_seconds
                        ),
                        search_trial_times_seconds=list(
                            metric.search_trial_times_seconds
                        ),
                        total_trial_times_seconds=list(
                            metric.total_trial_times_seconds
                        ),

                        # Preprocessing statistics.
                        preprocessing_median_seconds=(
                            metric.preprocessing_median_seconds
                        ),
                        preprocessing_minimum_seconds=(
                            metric.preprocessing_minimum_seconds
                        ),
                        preprocessing_maximum_seconds=(
                            metric.preprocessing_maximum_seconds
                        ),

                        # Search statistics.
                        search_median_seconds=(
                            metric.search_median_seconds
                        ),
                        search_minimum_seconds=(
                            metric.search_minimum_seconds
                        ),
                        search_maximum_seconds=(
                            metric.search_maximum_seconds
                        ),

                        # Total statistics.
                        total_median_seconds=(
                            metric.total_median_seconds
                        ),
                        total_minimum_seconds=(
                            metric.total_minimum_seconds
                        ),
                        total_maximum_seconds=(
                            metric.total_maximum_seconds
                        ),

                        # Rabin–Karp diagnostics.
                        #
                        # These are zero for Naive and KMP.
                        # For Rabin–Karp they contain the measured
                        # verification and collision counts.
                        verification_count=(
                            metric.verification_count
                        ),
                        collision_count=(
                            metric.collision_count
                        ),

                        # Correctness/result data.
                        match_count=metric.match_count,
                        positions=list(metric.positions),
                        text_length=metric.text_length,
                        peak_memory_bytes=metric.peak_memory_bytes,
                    )
                    for metric in result.results
                ]
            )

        return benchmark

    except Exception as exc:
        benchmark.status = BenchmarkRun.Status.FAILED
        benchmark.progress_message = "Benchmark failed."
        benchmark.error_message = "The benchmark could not be completed. Try again or contact an administrator."
        benchmark.completed_at = timezone.now()

        benchmark.save(
            update_fields=[
                "status",
                "error_message",
                "progress_message",
                "completed_at",
            ]
        )
        record_event(
            actor=owner,
            workspace=workspace,
            action=AuditEvent.Action.BENCHMARK_FAILED,
            object_type="BenchmarkRun",
            object_id=benchmark.pk,
        )
        logger.error(
            "Benchmark run failed for run id=%s owner_id=%s error_type=%s",
            benchmark.pk,
            owner.pk,
            type(exc).__name__,
        )

        raise
