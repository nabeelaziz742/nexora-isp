from django.urls import path

from accounts.api.password_views import (
    ChangePasswordAPIView,
    PasswordResetConfirmAPIView,
    PasswordResetRequestAPIView,
)
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
        "change-password/",
        ChangePasswordAPIView.as_view(),
        name="change-password",
    ),
    path(
        "password-reset/",
        PasswordResetRequestAPIView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmAPIView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "me/",
        CurrentSessionAPIView.as_view(),
        name="current-session",
    ),
]