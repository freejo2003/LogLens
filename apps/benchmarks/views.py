from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.permissions import analyst_post_required

from apps.benchmarks.forms import BenchmarkRunForm
from apps.benchmarks.models import BenchmarkRun
from apps.benchmarks.services.benchmark_jobs import BenchmarkBusyError
from apps.benchmarks.services.source_benchmark import queue_source_benchmark


@login_required
@analyst_post_required
def benchmark_workspace(request):
    benchmark = None

    if request.method == "POST":
        form = BenchmarkRunForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            workspace = form.cleaned_data["workspace"]
            source_file = form.cleaned_data["source_file"]
            pattern = form.cleaned_data["pattern"]

            try:
                benchmark = queue_source_benchmark(
                    source_file=source_file,
                    owner=request.user,
                    pattern=pattern,
                    case_sensitive=form.cleaned_data["case_sensitive"],
                    unicode_normalization=form.cleaned_data["unicode_normalization"],
                )
                return redirect(f"{reverse('benchmarks:run')}?run={benchmark.pk}")
            except BenchmarkBusyError as exc:
                form.add_error(None, str(exc))
            except (PermissionError, ValueError) as exc:
                form.add_error(
                    None,
                    str(exc),
                )

    else:
        form = BenchmarkRunForm(
            user=request.user,
        )
        run_id = request.GET.get("run")
        if run_id:
            benchmark = get_object_or_404(
                BenchmarkRun.objects.filter(owner=request.user),
                pk=run_id,
            )

    metrics = []

    if benchmark is not None:
        metrics = list(
            benchmark.algorithm_metrics.all()
        )

    fastest_search_seconds = max(
        (metric.search_median_seconds for metric in metrics),
        default=0,
    )
    comparison_rows = []
    for rank, metric in enumerate(
        sorted(metrics, key=lambda item: item.search_median_seconds),
        start=1,
    ):
        comparison_rows.append(
            {
                "rank": rank,
                "algorithm": metric.algorithm,
                "display_name": {
                    "naive": "Naive",
                    "kmp": "KMP",
                    "rabin_karp": "Rabin–Karp",
                }.get(metric.algorithm, metric.algorithm),
                "search_median_seconds": metric.search_median_seconds,
                "bar_percent": (
                    metric.search_median_seconds / fastest_search_seconds * 100
                    if fastest_search_seconds > 0
                    else 0
                ),
                "bar_color": {
                    "naive": "bg-warning",
                    "kmp": "bg-success",
                    "rabin_karp": "bg-info",
                }.get(metric.algorithm, "bg-primary"),
            }
        )

    return render(
        request,
        "benchmarks/benchmark.html",
        {
            "form": form,
            "benchmark": benchmark,
            "metrics": metrics,
            "comparison_rows": comparison_rows,
        },
    )


@login_required
def benchmark_progress(request, benchmark_id):
    benchmark = get_object_or_404(
        BenchmarkRun.objects.filter(owner=request.user),
        pk=benchmark_id,
    )
    return JsonResponse(
        {
            "id": benchmark.pk,
            "status": benchmark.status,
            "percent": benchmark.progress_percent,
            "message": benchmark.progress_message,
            "lines_processed": benchmark.progress_lines_processed,
            "total_lines": benchmark.progress_total_lines,
            "error": benchmark.error_message,
        }
    )
