from django.urls import path

from . import views


app_name = "reports"

urlpatterns = [
    path(
        "benchmark/<int:benchmark_id>/",
        views.benchmark_analysis,
        name="analysis",
    ),
]