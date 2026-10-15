from django.urls import path

from apps.accounts.views import LogLensLoginView, audit_events, logout_view, manage_roles

app_name = "accounts"

urlpatterns = [
    path("login/", LogLensLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("audit/", audit_events, name="audit"),
    path("roles/", manage_roles, name="roles"),
]
