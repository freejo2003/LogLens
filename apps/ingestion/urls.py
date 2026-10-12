from django.urls import path

from . import views

app_name = "ingestion"

urlpatterns = [
    path("upload/", views.upload_source_file, name="upload"),
    path(
        "extract/<int:source_file_id>/",
        views.extract_source_file,
        name="extract",
    ),
    path(
        "delete/<int:source_file_id>/",
        views.delete_source_file_view,
        name="delete",
    ),
]