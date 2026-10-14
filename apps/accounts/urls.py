from django.urls import path

from apps.accounts.views import LogLensLoginView, logout_view

app_name = "accounts"

urlpatterns = [
    path("login/", LogLensLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
]