from django.urls import path

from tenancy.staff_views import (
    OperatorListView,
    OperatorWorkloadDetailView,
    OrganizationStaffActiveStateView,
    OrganizationStaffDetailView,
    OrganizationStaffListCreateView,
    OrganizationStaffStatusView,
)
from tenancy.views import (
    AuditLogListView,
    OrganizationProfileAPIView,
    OrganizationTechnicianListAPIView,
    OwnerSecurityCheckView,
)


urlpatterns = [
    path(
        "organization/",
        OrganizationProfileAPIView.as_view(),
        name="organization-profile",
    ),
    path(
        "profile/",
        OrganizationProfileAPIView.as_view(),
        name="organization-profile-alias",
    ),
    path(
        "audit-logs/",
        AuditLogListView.as_view(),
        name="tenant-audit-logs",
    ),
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
        OrganizationStaffListCreateView.as_view(),
        name="organization-staff-list-create",
    ),
    path(
        "staff/<uuid:membership_id>/",
        OrganizationStaffDetailView.as_view(),
        name="organization-staff-detail",
    ),
    path(
        "staff/<uuid:membership_id>/active-state/",
        OrganizationStaffActiveStateView.as_view(),
        name="organization-staff-active-state",
    ),
    path(
        "staff/<uuid:membership_id>/status/",
        OrganizationStaffStatusView.as_view(),
        name="organization-staff-status",
    ),
    path(
        "operators/",
        OperatorListView.as_view(),
        name="operator-list",
    ),
    path(
        "operators/<uuid:user_id>/workload/",
        OperatorWorkloadDetailView.as_view(),
        name="operator-workload-detail",
    ),
]