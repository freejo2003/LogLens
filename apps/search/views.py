from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from apps.search.services.saved_search_status import (
    get_saved_search_source_status,
)
from apps.search.forms import IndicatorRuleForm, SavedSearchForm, SearchRunForm
from apps.search.models import ErrorGroup
from apps.search.services.indicators import (
    create_indicator_rule,
    get_indicator_rules_for_user,
)
from apps.search.services.saved_searches import (
    create_saved_search,
    get_saved_searches_for_user,
)
from apps.search.services.search_persistence import create_search_run


@login_required
def search_workspace(request):
    search_run = None
    match_results = []

    if request.method == "POST":
        form = SearchRunForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            workspace = form.cleaned_data["workspace"]
            source_file = form.cleaned_data["source_file"]
            pattern = form.cleaned_data["pattern"]
            algorithm = form.cleaned_data["algorithm"]

            try:
                search_run = create_search_run(
                    workspace=workspace,
                    owner=request.user,
                    source_file=source_file,
                    pattern=pattern,
                    algorithm=algorithm,
                )

                match_results = list(
                    search_run.match_results
                    .select_related(
                        "segment",
                        "source_file",
                    )
                    .order_by("segment__sequence")
                )

            except (PermissionError, ValueError) as exc:
                form.add_error(
                    None,
                    str(exc),
                )

    else:
        form = SearchRunForm(
            user=request.user,
        )

    return render(
        request,
        "search/search.html",
        {
            "form": form,
            "search_run": search_run,
            "match_results": match_results,
            "saved_searches": get_saved_searches_for_user(
                request.user
            ),
            "indicator_rules": get_indicator_rules_for_user(
                request.user
            ),
        },
    )
@login_required
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
def indicators_workspace(request):
    form = IndicatorRuleForm(
        user=request.user,
    )

    return render(
        request,
        "search/indicators.html",
        {
            "form": form,
            "indicator_rules": get_indicator_rules_for_user(
                request.user
            ),
        },
    )


@login_required
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
                description=form.cleaned_data["description"],
            )
        except (PermissionError, ValueError):
            pass

    return redirect("search:run")


@login_required
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
        except PermissionError:
            pass

    return redirect("search:indicators")