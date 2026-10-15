from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.benchmarks.models import BenchmarkRun
from apps.ingestion.models import SourceFile
from apps.search.models import SearchRun

from .models import Workspace
from .forms import WorkspaceForm
from apps.accounts.permissions import analyst_required
from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent


@login_required
def dashboard(request):
    user = request.user

    workspaces = Workspace.objects.filter(
        owner=user,
    )

    source_files = SourceFile.objects.filter(
        owner=user,
    )

    search_runs = SearchRun.objects.filter(
        owner=user,
    )

    benchmark_runs = BenchmarkRun.objects.filter(
        owner=user,
    )

    total_files = source_files.count()

    extracted_files = source_files.filter(
        extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
    ).count()

    pending_files = source_files.filter(
        extraction_status__in=[
            SourceFile.ExtractionStatus.PENDING,
            SourceFile.ExtractionStatus.PROCESSING,
        ],
    ).count()

    failed_files = source_files.filter(
        extraction_status=SourceFile.ExtractionStatus.FAILED,
    ).count()

    total_searches = search_runs.count()

    total_benchmarks = benchmark_runs.count()

    recent_files = source_files.select_related(
        "workspace",
    ).order_by(
        "-uploaded_at",
    )[:5]

    recent_searches = search_runs.select_related(
        "workspace",
        "source_file",
    ).order_by(
        "-created_at",
    )[:5]

    context = {
        "workspaces": workspaces,
        "total_files": total_files,
        "extracted_files": extracted_files,
        "pending_files": pending_files,
        "failed_files": failed_files,
        "total_searches": total_searches,
        "total_benchmarks": total_benchmarks,
        "recent_files": recent_files,
        "recent_searches": recent_searches,
    }

    return render(
        request,
        "dashboard/index.html",
        context,
    )


@login_required
@analyst_required
def create_workspace(request):
    if request.method == "POST":
        form = WorkspaceForm(request.POST)
        if form.is_valid():
            workspace = form.save(commit=False)
            workspace.owner = request.user
            workspace.save()
            record_event(
                actor=request.user,
                workspace=workspace,
                action=AuditEvent.Action.WORKSPACE_CREATED,
                object_type="Workspace",
                object_id=workspace.pk,
            )
            messages.success(request, "Workspace created.")
            return redirect("dashboard")
    else:
        form = WorkspaceForm()
    return render(request, "workspaces/create.html", {"form": form})
