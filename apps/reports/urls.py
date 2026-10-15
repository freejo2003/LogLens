from django.urls import path

from . import views


app_name = "reports"

urlpatterns = [
    path(
        "benchmark/<int:benchmark_id>/",
        views.benchmark_analysis,
        name="analysis",
    ),
    path("benchmark/<int:benchmark_id>/export.csv", views.export_benchmark_csv, name="export-csv"),
    path("benchmark/<int:benchmark_id>/export.json", views.export_benchmark_json, name="export-json"),
]
