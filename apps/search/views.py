from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent
from apps.accounts.permissions import (
    analyst_post_required,
    analyst_required,
    reviewer_required,
)

from apps.search.forms import (
    IndicatorRuleForm,
    SavedSearchForm,
    SearchRunForm,
)
from apps.search.models import ErrorGroup, IndicatorRule, SavedSearch, SearchRun
from apps.search.services.indicators import (
    create_indicator_rule,
    get_indicator_rules_for_user,
    update_indicator_rule,
)
from apps.search.services.saved_search_status import (
    get_saved_search_source_status,
)
from apps.search.services.saved_searches import (
    create_saved_search,
    get_saved_searches_for_user,
)
from apps.search.services.normalization import normalize_search_text
from apps.search.services.search_persistence import create_search_run


def _prepare_search_result_page(page, search_run):
    normalized_pattern = normalize_search_text(
        search_run.pattern,
        case_sensitive=search_run.case_sensitive,
        unicode_normalization=search_run.unicode_normalization,
    )
    for result in page:
        normalized_text = normalize_search_text(
            result.segment.text,
            case_sensitive=search_run.case_sensitive,
            unicode_normalization=search_run.unicode_normalization,
        )
        if result.positions:
            first = result.positions[0]
            start = max(0, first - 80)
            end = min(len(normalized_text), first + len(normalized_pattern) + 120)
            result.context_snippet = (
                ("…" if start else "")
                + normalized_text[start:end]
                + ("…" if end < len(normalized_text) else "")
            )
        else:
            result.context_snippet = normalized_text[:200]
        result.display_positions = result.positions[:100]
        result.positions_truncated = len(result.positions) > 100
    return page


@login_required
@analyst_post_required
def search_workspace(request):
    search_run = None

    if request.method == "POST":
        from django.core.exceptions import PermissionDenied

        from apps.accounts.services import is_reviewer

        if is_reviewer(request.user):
            raise PermissionDenied

        form = SearchRunForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            workspace = form.cleaned_data["workspace"]
            source_file = form.cleaned_data["source_file"]
            pattern = form.cleaned_data["pattern"]
            indicator_rule = form.cleaned_data["indicator_rule"]
            algorithm = form.cleaned_data["algorithm"]
            case_sensitive = form.cleaned_data["case_sensitive"]
            unicode_normalization = form.cleaned_data["unicode_normalization"]

            try:
                search_run = create_search_run(
                    workspace=workspace,
                    owner=request.user,
                    source_file=source_file,
                    pattern=pattern,
                    algorithm=algorithm,
                    indicator_rule=indicator_rule,
                    case_sensitive=case_sensitive,
                    unicode_normalization=unicode_normalization,
                )
                return redirect("search:history-detail", run_id=search_run.pk)

            except (PermissionError, ValueError) as exc:
                form.add_error(
                    None,
                    str(exc),
                )

    else:
        initial = {}
        requested_rule_id = request.GET.get("indicator_rule")
        if requested_rule_id:
            selected_rule = IndicatorRule.objects.filter(
                pk=requested_rule_id,
                owner=request.user,
                is_active=True,
            ).first()
            if selected_rule is not None:
                initial = {"workspace": selected_rule.workspace_id, "indicator_rule": selected_rule.pk}
        form = SearchRunForm(user=request.user, initial=initial)

    return render(
        request,
        "search/search.html",
        {
            "form": form,
            "search_run": search_run,
            "saved_searches": get_saved_searches_for_user(
                request.user
            ),
            "indicator_rules": get_indicator_rules_for_user(
                request.user
            ),
            "search_history": SearchRun.objects.filter(owner=request.user)
            .select_related("workspace", "source_file")[:10],
        },
    )


@login_required
@reviewer_required
def search_history(request):
    search_runs = (
        SearchRun.objects.filter(owner=request.user)
        .select_related("workspace", "source_file")[:100]
    )
    return render(request, "search/history.html", {"search_runs": search_runs})


@login_required
@reviewer_required
def search_run_detail(request, run_id):
    search_run = get_object_or_404(
        SearchRun.objects.select_related("workspace", "source_file", "indicator_rule").prefetch_related(
            "match_results__segment", "match_results__source_file"
        ),
        pk=run_id,
        owner=request.user,
    )
    match_results = Paginator(
        search_run.match_results.select_related("segment", "source_file").order_by("segment__sequence"),
        100,
    ).get_page(request.GET.get("page"))
    _prepare_search_result_page(match_results, search_run)
    saved_search_form = None
    if search_run.status == SearchRun.Status.SUCCEEDED and search_run.source_file_id:
        saved_search_form = SavedSearchForm(
            user=request.user,
            initial={
                "workspace": search_run.workspace_id,
                "source_file": search_run.source_file_id,
                "pattern": search_run.pattern,
                "algorithm": search_run.algorithm,
                "case_sensitive": search_run.case_sensitive,
                "unicode_normalization": search_run.unicode_normalization,
            },
        )
    return render(
        request,
        "search/search_results.html",
        {
            "search_run": search_run,
            "match_results": match_results,
            "error_message": search_run.error_message or None,
            "saved_search_form": saved_search_form,
        },
    )


@login_required
@analyst_required
@require_POST
def run_saved_search(request, saved_search_id):
    saved_search = get_object_or_404(
        SavedSearch.objects.select_related("workspace", "source_file"),
        pk=saved_search_id,
        owner=request.user,
        workspace__owner=request.user,
        is_active=True,
    )
    if saved_search.source_file is None:
        messages.error(request, "The saved search source is no longer available.")
        return redirect("search:saved")
    try:
        search_run = create_search_run(
            workspace=saved_search.workspace,
            owner=request.user,
            source_file=saved_search.source_file,
            pattern=saved_search.pattern,
            algorithm=saved_search.algorithm,
            case_sensitive=saved_search.case_sensitive,
            unicode_normalization=saved_search.unicode_normalization,
        )
    except (PermissionError, ValueError):
        messages.error(request, "The saved search could not be rerun. Check that its source is available and try again.")
        return redirect("search:saved")
    return redirect("search:history-detail", run_id=search_run.pk)


class _CsvEcho:
    def write(self, value):
        return value


def _spreadsheet_safe(value):
    value = str(value)
    first = value.lstrip()[:1]
    if first in {"=", "+", "-", "@"}:
        return "'" + value
    return value


@login_required
@reviewer_required
def export_search_csv(request, run_id):
    import csv

    search_run = get_object_or_404(SearchRun, pk=run_id, owner=request.user)
    record_event(
        actor=request.user,
        workspace=search_run.workspace,
        action=AuditEvent.Action.EXPORT_CREATED,
        object_type="SearchRun",
        object_id=search_run.pk,
        details={"format": "csv"},
    )
    results = (
        search_run.match_results.select_related("segment", "source_file")
        .order_by("segment__sequence")
    )
    echo = _CsvEcho()
    writer = csv.writer(echo)

    def rows():
        yield writer.writerow(
            ["run_id", "pattern", "indicator", "algorithm", "case_sensitive", "unicode_normalization", "source_file", "line", "page", "paragraph", "positions", "match_count", "text"]
        )
        for result in results.iterator(chunk_size=500):
            yield writer.writerow(
                [
                    search_run.pk,
                    _spreadsheet_safe(search_run.pattern),
                    _spreadsheet_safe(search_run.indicator_name_snapshot),
                    search_run.algorithm,
                    search_run.case_sensitive,
                    search_run.unicode_normalization,
                    _spreadsheet_safe(result.source_file.original_name),
                    result.segment.line_number or "",
                    result.segment.page_number or "",
                    result.segment.paragraph_number or "",
                    ",".join(str(position) for position in result.positions),
                    result.match_count,
                    _spreadsheet_safe(result.segment.text),
                ]
            )

    response = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="loglens-search-{search_run.pk}.csv"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@reviewer_required
def export_search_json(request, run_id):
    search_run = get_object_or_404(SearchRun, pk=run_id, owner=request.user)
    record_event(
        actor=request.user,
        workspace=search_run.workspace,
        action=AuditEvent.Action.EXPORT_CREATED,
        object_type="SearchRun",
        object_id=search_run.pk,
        details={"format": "json"},
    )
    payload = {
        "run": {
            "id": search_run.pk,
            "pattern": search_run.pattern,
            "indicator": search_run.indicator_name_snapshot,
            "algorithm": search_run.algorithm,
            "case_sensitive": search_run.case_sensitive,
            "unicode_normalization": search_run.unicode_normalization,
            "source_checksum": search_run.source_checksum,
            "created_at": search_run.created_at.isoformat(),
            "total_match_count": search_run.total_match_count,
            "status": search_run.status,
        },
        "results": [
            {
                "source_file": result.source_file.original_name,
                "sequence": result.segment.sequence,
                "line": result.segment.line_number,
                "page": result.segment.page_number,
                "paragraph": result.segment.paragraph_number,
                "positions": result.positions,
                "match_count": result.match_count,
                "text": result.segment.text,
            }
            for result in search_run.match_results.select_related(
                "segment", "source_file"
            ).order_by("segment__sequence")
        ],
    }
    response = JsonResponse(payload, json_dumps_params={"ensure_ascii": False})
    response["Content-Disposition"] = f'attachment; filename="loglens-search-{search_run.pk}.json"'
    response["X-Content-Type-Options"] = "nosniff"
    return response

@login_required
@reviewer_required
def saved_searches_workspace(request):
    saved_searches = list(
        get_saved_searches_for_user(request.user)
    )

    for saved_search in saved_searches:
        saved_search.source_status = get_saved_search_source_status(
            saved_search
        )

    return render(
        request,
        "search/saved_searches.html",
        {
            "saved_searches": saved_searches,
        },
    )


@login_required
@reviewer_required
def indicators_workspace(request):
    from apps.accounts.services import is_reviewer

    form = IndicatorRuleForm(
        user=request.user,
    )

    return render(
        request,
        "search/indicators.html",
        {
            "form": form,
            "indicator_rules": get_indicator_rules_for_user(request.user),
            "can_manage_indicators": not is_reviewer(request.user),
        },
    )


@login_required
@reviewer_required
def error_groups_workspace(request):
    error_groups = (
        ErrorGroup.objects
        .filter(
            owner=request.user,
            workspace__owner=request.user,
        )
        .prefetch_related(
            "members__source_file",
            "members__segment",
        )
        .select_related("workspace")
        .order_by(
            "-occurrence_count",
            "name",
        )
    )

    return render(
        request,
        "search/error_groups.html",
        {
            "error_groups": error_groups,
        },
    )


@login_required
@analyst_required
def save_search(request):
    if request.method != "POST":
        return redirect("search:run")

    form = SavedSearchForm(
        request.POST,
        user=request.user,
    )

    if form.is_valid():
        try:
            create_saved_search(
                owner=request.user,
                workspace=form.cleaned_data["workspace"],
                source_file=form.cleaned_data["source_file"],
                name=form.cleaned_data["name"],
                pattern=form.cleaned_data["pattern"],
                algorithm=form.cleaned_data["algorithm"],
                case_sensitive=form.cleaned_data["case_sensitive"],
                unicode_normalization=form.cleaned_data["unicode_normalization"],
                description=form.cleaned_data["description"],
            )
        except (PermissionError, ValueError, IntegrityError):
            messages.error(request, "The saved search could not be saved. Check that its name is unique and its source is available.")
        else:
            messages.success(request, "Saved search created.")
    else:
        messages.error(request, "The saved search could not be saved. Review the supplied values.")

    return redirect("search:run")


@login_required
@analyst_required
def create_indicator(request):
    if request.method != "POST":
        return redirect("search:indicators")

    form = IndicatorRuleForm(
        request.POST,
        user=request.user,
    )

    if form.is_valid():
        try:
            create_indicator_rule(
                owner=request.user,
                workspace=form.cleaned_data["workspace"],
                name=form.cleaned_data["name"],
                pattern=form.cleaned_data["pattern"],
                description=form.cleaned_data["description"],
                is_active=form.cleaned_data["is_active"],
            )
        except (PermissionError, IntegrityError):
            messages.error(request, "The indicator could not be saved. Check that its name is unique and its workspace is available.")
        else:
            record_event(
                actor=request.user,
                workspace=form.cleaned_data["workspace"],
                action=AuditEvent.Action.INDICATOR_RULE_CREATED,
                object_type="IndicatorRule",
                details={"name": form.cleaned_data["name"]},
            )
            messages.success(request, "Indicator created.")
    else:
        messages.error(request, "The indicator could not be saved. Review the supplied values.")

    return redirect("search:indicators")


@login_required
@analyst_required
def edit_indicator(request, rule_id):
    rule = get_object_or_404(
        IndicatorRule.objects.select_related("workspace"),
        pk=rule_id,
        owner=request.user,
    )
    initial = {
        "workspace": rule.workspace_id,
        "name": rule.name,
        "pattern": rule.pattern,
        "description": rule.description,
        "is_active": rule.is_active,
    }
    if request.method == "POST":
        form = IndicatorRuleForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                update_indicator_rule(
                    owner=request.user,
                    rule=rule,
                    workspace=form.cleaned_data["workspace"],
                    name=form.cleaned_data["name"],
                    pattern=form.cleaned_data["pattern"],
                    description=form.cleaned_data["description"],
                    is_active=form.cleaned_data["is_active"],
                )
            except (PermissionError, IntegrityError):
                form.add_error(None, "The indicator could not be updated. Check its name and workspace.")
            else:
                record_event(
                    actor=request.user,
                    workspace=rule.workspace,
                    action=AuditEvent.Action.INDICATOR_RULE_UPDATED,
                    object_type="IndicatorRule",
                    object_id=rule.pk,
                    details={"name": rule.name, "active": rule.is_active},
                )
                messages.success(request, "Indicator updated.")
                return redirect("search:indicators")
    else:
        form = IndicatorRuleForm(user=request.user, initial=initial)
    return render(request, "search/edit_indicator.html", {"form": form, "rule": rule})
