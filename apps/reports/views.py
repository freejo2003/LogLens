from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

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