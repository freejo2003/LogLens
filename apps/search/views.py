from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.search.forms import SearchRunForm
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
                    .select_related("segment", "source_file")
                    .order_by("segment__sequence")
                )

            except PermissionError as exc:
                form.add_error(None, str(exc))

            except ValueError as exc:
                form.add_error(None, str(exc))

    else:
        form = SearchRunForm(user=request.user)

    return render(
        request,
        "search/search.html",
        {
            "form": form,
            "search_run": search_run,
            "match_results": match_results,
        },
    )