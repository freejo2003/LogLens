from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.ingestion.models import SourceFile
from apps.search.models import IndicatorRule, SearchRun
from apps.benchmarks.models import BenchmarkRun


@login_required
def dashboard(request):
    user = request.user

    source_files = SourceFile.objects.filter(owner=user)

    total_files = source_files.count()

    extracted_files = source_files.filter(
        extraction_status=SourceFile.ExtractionStatus.SUCCEEDED
    ).count()

    pending_files = source_files.filter(
        extraction_status=SourceFile.ExtractionStatus.PENDING
    ).count()

    failed_files = source_files.filter(
        extraction_status=SourceFile.ExtractionStatus.FAILED
    ).count()

    total_searches = SearchRun.objects.filter(owner=user).count()

    total_indicators = IndicatorRule.objects.filter(owner=user).count()

    total_benchmarks = BenchmarkRun.objects.filter(owner=user).count()

    recent_files = (
        source_files
        .select_related("workspace")
        .order_by("-uploaded_at")[:5]
    )

    recent_searches = (
        SearchRun.objects
        .filter(owner=user)
        .select_related("source_file")
        .order_by("-created_at")[:5]
    )

    context = {
        "total_files": total_files,
        "extracted_files": extracted_files,
        "pending_files": pending_files,
        "failed_files": failed_files,
        "total_searches": total_searches,
        "total_indicators": total_indicators,
        "total_benchmarks": total_benchmarks,
        "recent_files": recent_files,
        "recent_searches": recent_searches,
    }

    return render(
        request,
        "dashboard/index.html",
        context,
    )