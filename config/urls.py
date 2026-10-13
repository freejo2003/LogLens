from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("apps.workspaces.urls")),
    path("ingestion/", include("apps.ingestion.urls")),
    path("search/", include("apps.search.urls")),
    path("benchmarks/", include("apps.benchmarks.urls")),
    path("reports/", include("apps.reports.urls")),
]
