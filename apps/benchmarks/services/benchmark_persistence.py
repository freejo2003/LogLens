import hashlib

from django.db import transaction
from django.utils import timezone

from apps.benchmarks.models import AlgorithmMetric, BenchmarkRun
from apps.benchmarks.services.benchmark_engine import benchmark_all


ALGORITHM_VERSIONS = {
    "naive": "1.0",
    "kmp": "1.0",
    "rabin_karp": "1.0",
}


def calculate_input_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_benchmark_run(
    *,
    workspace,
    owner,
    text: str,
    pattern: str,
    source_file=None,
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

    benchmark = BenchmarkRun.objects.create(
        workspace=workspace,
        owner=owner,
        source_file=source_file,
        pattern=pattern,
        source_checksum=source_checksum,
        input_checksum=input_checksum,
        text_length=len(text),
        status=BenchmarkRun.Status.RUNNING,
    )

    try:
        result = benchmark_all(text, pattern)

        with transaction.atomic():
            benchmark.positions_consistent = result.positions_consistent
            benchmark.status = BenchmarkRun.Status.SUCCEEDED
            benchmark.completed_at = timezone.now()

            benchmark.save(
                update_fields=[
                    "positions_consistent",
                    "status",
                    "completed_at",
                ]
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
                    )
                    for metric in result.results
                ]
            )

        return benchmark

    except Exception as exc:
        benchmark.status = BenchmarkRun.Status.FAILED
        benchmark.error_message = str(exc)
        benchmark.completed_at = timezone.now()

        benchmark.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
            ]
        )

        raise