from django.urls import path

from . import views

app_name = "ingestion"

urlpatterns = [
    path("upload/", views.upload_source_file, name="upload"),
]