from django.urls import path

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from accounts.api.views import (
    CurrentSessionAPIView,
    TenantLoginAPIView,
)


urlpatterns = [
    path(
        "login/",
        TenantLoginAPIView.as_view(),
        name="tenant-login",
    ),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "me/",
        CurrentSessionAPIView.as_view(),
        name="current-session",
    ),
]