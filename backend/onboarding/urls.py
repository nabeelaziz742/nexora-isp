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
    ISPOwnerPasswordResetAPIView,
    OwnerSubscriptionReceiptAPIView,
    OwnerSubscriptionStatusAPIView,
    SuperAdminChangePasswordAPIView,
    ISPDetailAPIView,
    ISPListAPIView,
    ISPSubscriptionAPIView,
    ISPSubscriptionPaymentAPIView,
    ISPSuspendAPIView,
    PlatformDashboardAPIView,
    SubscriptionReceiptAPIView,
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
    path("superadmin/isps/<uuid:organization_id>/reset-owner-password/", ISPOwnerPasswordResetAPIView.as_view(), name="superadmin-isp-reset-owner-password"),
    path("superadmin/change-password/", SuperAdminChangePasswordAPIView.as_view(), name="superadmin-change-password"),
    path("superadmin/subscription-payments/<uuid:payment_id>/receipt/", SubscriptionReceiptAPIView.as_view(), name="superadmin-subscription-receipt"),
    path("subscription/", OwnerSubscriptionStatusAPIView.as_view(), name="owner-subscription-status"),
    path("subscription/payments/<uuid:payment_id>/receipt/", OwnerSubscriptionReceiptAPIView.as_view(), name="owner-subscription-receipt"),
]
