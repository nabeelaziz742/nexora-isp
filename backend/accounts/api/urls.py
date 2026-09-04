from django.urls import path

from accounts.api.views import (
    CurrentSessionAPIView,
    LogoutAPIView,
    TenantLoginAPIView,
    TenantTokenRefreshAPIView,
)


urlpatterns = [
    path(
        "login/",
        TenantLoginAPIView.as_view(),
        name="tenant-login",
    ),
    path(
        "logout/",
        LogoutAPIView.as_view(),
        name="tenant-logout",
    ),
    path(
        "token/refresh/",
        TenantTokenRefreshAPIView.as_view(),
        name="token-refresh",
    ),
    path(
        "me/",
        CurrentSessionAPIView.as_view(),
        name="current-session",
    ),
]