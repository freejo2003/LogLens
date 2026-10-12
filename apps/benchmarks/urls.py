from django.urls import path

from . import views


app_name = "benchmarks"

urlpatterns = [
    path(
        "",
        views.benchmark_workspace,
        name="run",
    ),
]