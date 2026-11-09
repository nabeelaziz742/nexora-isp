from django.urls import path

from onboarding.views import (
    ISPRegistrationAPIView,
    RegistrationReceiptAPIView,
    RegistrationStatusAPIView,
    SuperAdminLoginAPIView,
    SuperAdminPaymentSettingsAPIView,
    SuperAdminReceiptAPIView,
    SuperAdminRegistrationDetailAPIView,
    SuperAdminRegistrationListAPIView,
    SuperAdminTokenRefreshAPIView,
)

from onboarding.platform_views import (
    ISPActivateAPIView,
    ISPDetailAPIView,
    ISPListAPIView,
    ISPSubscriptionAPIView,
    ISPSubscriptionPaymentAPIView,
    ISPSuspendAPIView,
    PlatformDashboardAPIView,
)


urlpatterns = [
    path("register/", ISPRegistrationAPIView.as_view(), name="isp-register"),
    path("registration/<uuid:access_token>/", RegistrationStatusAPIView.as_view(), name="registration-status"),
    path("registration/<uuid:access_token>/receipt/", RegistrationReceiptAPIView.as_view(), name="registration-receipt"),
    path("superadmin/login/", SuperAdminLoginAPIView.as_view(), name="superadmin-login"),
    path("superadmin/refresh/", SuperAdminTokenRefreshAPIView.as_view(), name="superadmin-refresh"),
    path("superadmin/payment-settings/", SuperAdminPaymentSettingsAPIView.as_view(), name="superadmin-payment-settings"),
    path("superadmin/registrations/", SuperAdminRegistrationListAPIView.as_view(), name="superadmin-registrations"),
    path("superadmin/registrations/<uuid:registration_id>/receipt/", SuperAdminReceiptAPIView.as_view(), name="superadmin-registration-receipt"),
    path("superadmin/registrations/<uuid:registration_id>/<str:action>/", SuperAdminRegistrationDetailAPIView.as_view(), name="superadmin-registration-action"),
    path("superadmin/dashboard/", PlatformDashboardAPIView.as_view(), name="superadmin-dashboard"),
    path("superadmin/isps/", ISPListAPIView.as_view(), name="superadmin-isps"),
    path("superadmin/isps/<uuid:organization_id>/", ISPDetailAPIView.as_view(), name="superadmin-isp-detail"),
    path("superadmin/isps/<uuid:organization_id>/suspend/", ISPSuspendAPIView.as_view(), name="superadmin-isp-suspend"),
    path("superadmin/isps/<uuid:organization_id>/activate/", ISPActivateAPIView.as_view(), name="superadmin-isp-activate"),
    path("superadmin/isps/<uuid:organization_id>/subscription/", ISPSubscriptionAPIView.as_view(), name="superadmin-isp-subscription"),
    path("superadmin/isps/<uuid:organization_id>/subscription/payments/", ISPSubscriptionPaymentAPIView.as_view(), name="superadmin-isp-subscription-payment"),
]
