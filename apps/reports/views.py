from django.contrib.auth.decorators import login_required
import csv
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse

from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent
from apps.accounts.permissions import reviewer_required

from apps.benchmarks.models import BenchmarkRun
from apps.reports.services import build_benchmark_analysis


@login_required
@reviewer_required
def benchmark_analysis(request, benchmark_id):
    benchmark = get_object_or_404(
        BenchmarkRun.objects.prefetch_related(
            "algorithm_metrics",
        ),
        pk=benchmark_id,
        owner=request.user,
    )

    analysis = None
    error_message = None

    try:
        analysis = build_benchmark_analysis(
            benchmark,
        )
    except ValueError as exc:
        error_message = str(exc)

    return render(
        request,
        "reports/benchmark_analysis.html",
        {
            "benchmark": benchmark,
            "analysis": analysis,
            "error_message": error_message,
        },
    )


@login_required
@reviewer_required
def export_benchmark_json(request, benchmark_id):
    benchmark = get_object_or_404(
        BenchmarkRun.objects.prefetch_related("algorithm_metrics"),
        pk=benchmark_id,
        owner=request.user,
    )
    record_event(
        actor=request.user,
        workspace=benchmark.workspace,
        action=AuditEvent.Action.EXPORT_CREATED,
        object_type="BenchmarkRun",
        object_id=benchmark.pk,
        details={"format": "json"},
    )
    payload = {
        "benchmark": {
            "id": benchmark.pk,
            "pattern": benchmark.pattern,
            "case_sensitive": benchmark.case_sensitive,
            "unicode_normalization": benchmark.unicode_normalization,
            "source_checksum": benchmark.source_checksum,
            "input_checksum": benchmark.input_checksum,
            "text_length": benchmark.text_length,
            "status": benchmark.status,
            "positions_consistent": benchmark.positions_consistent,
            "created_at": benchmark.created_at.isoformat(),
            "completed_at": benchmark.completed_at.isoformat() if benchmark.completed_at else None,
            "python_version": benchmark.python_version,
            "platform": benchmark.platform_name,
        },
        "algorithms": list(
            benchmark.algorithm_metrics.values(
                "algorithm", "algorithm_version", "warmup_runs", "trial_count",
                "preprocessing_trial_times_seconds", "search_trial_times_seconds",
                "total_trial_times_seconds", "preprocessing_median_seconds",
                "search_median_seconds", "total_median_seconds",
                "total_minimum_seconds", "total_maximum_seconds",
                "verification_count", "collision_count", "match_count", "positions",
                "peak_memory_bytes",
            )
        ),
    }
    response = JsonResponse(payload, json_dumps_params={"ensure_ascii": False})
    response["Content-Disposition"] = f'attachment; filename="loglens-benchmark-{benchmark.pk}.json"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@reviewer_required
def export_benchmark_csv(request, benchmark_id):
    benchmark = get_object_or_404(
        BenchmarkRun.objects.prefetch_related("algorithm_metrics"),
        pk=benchmark_id,
        owner=request.user,
    )
    record_event(
        actor=request.user,
        workspace=benchmark.workspace,
        action=AuditEvent.Action.EXPORT_CREATED,
        object_type="BenchmarkRun",
        object_id=benchmark.pk,
        details={"format": "csv"},
    )
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="loglens-benchmark-{benchmark.pk}.csv"'
    response["X-Content-Type-Options"] = "nosniff"
    writer = csv.writer(response)
    writer.writerow(
        ["benchmark_id", "pattern", "case_sensitive", "unicode_normalization", "python_version", "platform", "algorithm", "version", "warmups", "trials", "preprocessing_median_seconds", "search_median_seconds", "total_median_seconds", "total_minimum_seconds", "total_maximum_seconds", "peak_memory_bytes", "matches", "positions_consistent", "verification_count", "collision_count"]
    )
    for metric in benchmark.algorithm_metrics.all():
        pattern = benchmark.pattern
        if pattern.lstrip()[:1] in {"=", "+", "-", "@"}:
            pattern = "'" + pattern
        writer.writerow(
            [
                benchmark.pk, pattern, benchmark.case_sensitive,
                benchmark.unicode_normalization, benchmark.python_version,
                benchmark.platform_name, metric.algorithm,
                metric.algorithm_version, metric.warmup_runs,
                metric.trial_count, metric.preprocessing_median_seconds,
                metric.search_median_seconds, metric.total_median_seconds,
                metric.total_minimum_seconds, metric.total_maximum_seconds,
                metric.peak_memory_bytes, metric.match_count, benchmark.positions_consistent,
                metric.verification_count, metric.collision_count,
            ]
        )
    return response
