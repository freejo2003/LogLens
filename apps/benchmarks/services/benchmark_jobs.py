"""Process-local runner for short, progress-reporting benchmark batches."""

import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from django.db import close_old_connections
from django.utils import timezone

from apps.benchmarks.models import BenchmarkRun
from apps.benchmarks.services.benchmark_persistence import (
    create_benchmark_run,
    create_pending_benchmark_run,
)


logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="loglens-benchmark")
_state_lock = Lock()
_active = False


class BenchmarkBusyError(ValueError):
    """Raised when this web instance is already running a benchmark."""


def _reset_active(_future=None):
    global _active
    with _state_lock:
        _active = False


def _execute_benchmark(benchmark_id: int, text: str) -> None:
    close_old_connections()
    try:
        benchmark = BenchmarkRun.objects.select_related(
            "workspace", "owner", "source_file"
        ).get(pk=benchmark_id)

        def report_progress(progress: dict) -> None:
            algorithm = {
                "naive": "Naive",
                "kmp": "KMP",
                "rabin_karp": "Rabin–Karp",
            }.get(progress["algorithm"], progress["algorithm"])
            lines = progress["lines_processed"]
            total_lines = progress["total_lines"]
            BenchmarkRun.objects.filter(
                pk=benchmark_id,
                status=BenchmarkRun.Status.RUNNING,
            ).update(
                progress_percent=progress["percent"],
                progress_message=(
                    f"{algorithm}, {progress['phase']}: "
                    f"{lines:,} of {total_lines:,} logs processed."
                ),
                progress_lines_processed=lines,
                progress_total_lines=total_lines,
            )

        create_benchmark_run(
            workspace=benchmark.workspace,
            owner=benchmark.owner,
            text=text,
            pattern=benchmark.pattern,
            source_file=benchmark.source_file,
            case_sensitive=benchmark.case_sensitive,
            unicode_normalization=benchmark.unicode_normalization,
            benchmark=benchmark,
            progress_callback=report_progress,
        )
    except Exception:
        BenchmarkRun.objects.filter(
            pk=benchmark_id,
            status__in=[
                BenchmarkRun.Status.PENDING,
                BenchmarkRun.Status.RUNNING,
            ],
        ).update(
            status=BenchmarkRun.Status.FAILED,
            progress_message="Benchmark failed. Please retry.",
            error_message=(
                "The benchmark could not be completed. Try again or contact an administrator."
            ),
            completed_at=timezone.now(),
        )
        logger.exception("Background benchmark failed for run id=%s", benchmark_id)
    finally:
        close_old_connections()


def submit_source_benchmark(
    *,
    source_file,
    owner,
    pattern: str,
    text: str,
    case_sensitive: bool = True,
    unicode_normalization: str = "none",
) -> BenchmarkRun:
    """Create a pending run and execute it outside the HTTP request."""
    global _active
    with _state_lock:
        if _active:
            raise BenchmarkBusyError(
                "A benchmark is already running on this service. Wait for it to finish, then try again."
            )
        _active = True

    try:
        benchmark = create_pending_benchmark_run(
            workspace=source_file.workspace,
            owner=owner,
            text=text,
            pattern=pattern,
            source_file=source_file,
            case_sensitive=case_sensitive,
            unicode_normalization=unicode_normalization,
        )
        future = _executor.submit(_execute_benchmark, benchmark.pk, text)
        future.add_done_callback(_reset_active)
        return benchmark
    except Exception:
        _reset_active()
        raise
