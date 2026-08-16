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
)


urlpatterns = [
    path("register/", ISPRegistrationAPIView.as_view(), name="isp-register"),
    path("registration/<uuid:access_token>/", RegistrationStatusAPIView.as_view(), name="registration-status"),
    path("registration/<uuid:access_token>/receipt/", RegistrationReceiptAPIView.as_view(), name="registration-receipt"),
    path("superadmin/login/", SuperAdminLoginAPIView.as_view(), name="superadmin-login"),
    path("superadmin/payment-settings/", SuperAdminPaymentSettingsAPIView.as_view(), name="superadmin-payment-settings"),
    path("superadmin/registrations/", SuperAdminRegistrationListAPIView.as_view(), name="superadmin-registrations"),
    path("superadmin/registrations/<uuid:registration_id>/receipt/", SuperAdminReceiptAPIView.as_view(), name="superadmin-registration-receipt"),
    path("superadmin/registrations/<uuid:registration_id>/<str:action>/", SuperAdminRegistrationDetailAPIView.as_view(), name="superadmin-registration-action"),
]
