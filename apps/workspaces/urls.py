from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("workspaces/create/", views.create_workspace, name="workspace-create"),
    path("workspaces/<int:workspace_id>/share/", views.share_workspace, name="workspace-share"),
]
