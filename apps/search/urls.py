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
        "saved/",
        views.saved_searches_workspace,
        name="saved",
    ),
    path("saved/compare/", views.compare_saved_searches, name="saved-compare"),
    path("saved/<int:saved_search_id>/run/", views.run_saved_search, name="saved-run"),
    path("history/", views.search_history, name="history"),
    path("history/<int:run_id>/", views.search_run_detail, name="history-detail"),
    path("history/<int:run_id>/export.csv", views.export_search_csv, name="history-export-csv"),
    path("history/<int:run_id>/export.json", views.export_search_json, name="history-export-json"),
    path("batches/<int:batch_id>/", views.search_batch_detail, name="batch-detail"),
    path("batches/<int:batch_id>/cancel/", views.cancel_search_batch, name="batch-cancel"),
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
    path("indicators/<int:rule_id>/edit/", views.edit_indicator, name="indicator-edit"),
    path(
        "error-groups/",
        views.error_groups_workspace,
        name="error-groups",
    ),
    
]
