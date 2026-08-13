from django.urls import path

from tenancy.views import (
    OrganizationStaffActiveStateAPIView,
    OrganizationStaffListCreateAPIView,
    OrganizationTechnicianListAPIView,
    OwnerSecurityCheckView,
)


urlpatterns = [
    path(
        "security/owner-check/",
        OwnerSecurityCheckView.as_view(),
        name="owner-security-check",
    ),
    path(
        "technicians/",
        OrganizationTechnicianListAPIView.as_view(),
        name="organization-technician-list",
    ),
    path(
        "staff/",
        OrganizationStaffListCreateAPIView.as_view(),
        name="organization-staff-list-create",
    ),
    path(
        "staff/<uuid:membership_id>/active-state/",
        OrganizationStaffActiveStateAPIView.as_view(),
        name="organization-staff-active-state",
    ),
]