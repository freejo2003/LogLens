from django.urls import path

from apps.search import views


app_name = "search"


urlpatterns = [
    path(
        "",
        views.search_workspace,
        name="run",
    ),
    path(
        "save/",
        views.save_search,
        name="save",
    ),
    path(
        "indicators/",
        views.indicators_workspace,
        name="indicators",
    ),
    path(
        "indicators/create/",
        views.create_indicator,
        name="indicator-create",
    ),
    path(
        "error-groups/",
        views.error_groups_workspace,
        name="error-groups",
    ),
]