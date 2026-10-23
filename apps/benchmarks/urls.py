from django.urls import path

from . import views


app_name = "benchmarks"

urlpatterns = [
    path(
        "",
        views.benchmark_workspace,
        name="run",
    ),
    path(
        "runs/<int:benchmark_id>/progress/",
        views.benchmark_progress,
        name="progress",
    ),
]
