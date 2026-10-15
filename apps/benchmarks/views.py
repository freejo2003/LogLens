from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.accounts.permissions import analyst_post_required

from apps.benchmarks.forms import BenchmarkRunForm
from apps.benchmarks.services.source_benchmark import benchmark_source_file


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
                benchmark = benchmark_source_file(
                    source_file=source_file,
                    owner=request.user,
                    pattern=pattern,
                    case_sensitive=form.cleaned_data["case_sensitive"],
                    unicode_normalization=form.cleaned_data["unicode_normalization"],
                )
            except (PermissionError, ValueError) as exc:
                form.add_error(
                    None,
                    str(exc),
                )

    else:
        form = BenchmarkRunForm(
            user=request.user,
        )

    metrics = []

    if benchmark is not None:
        metrics = list(
            benchmark.algorithm_metrics.all()
        )

    return render(
        request,
        "benchmarks/benchmark.html",
        {
            "form": form,
            "benchmark": benchmark,
            "metrics": metrics,
        },
    )
