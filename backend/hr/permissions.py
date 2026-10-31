from rest_framework.permissions import BasePermission

from tenancy.models import OrganizationMembership, StaffProfile
from tenancy.permissions import (
    HasActiveTenantContext,
    IsOrganizationManagerOrAdmin,
    IsOrganizationOwner,
    IsOrganizationStaffOrOwner,
    get_effective_role,
)


class CanManageHR(HasActiveTenantContext):
    """
    Privilege to manage HR operations: manual attendance overrides, bulk marking,
    leave approval/rejection, and organization-wide attendance matrices.
    Restricted strictly to OWNER, ADMIN, and MANAGER roles.
    """

    message = "HR management privilege (Owner, Admin, or Manager) is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
        }


class CanSubmitAttendance(HasActiveTenantContext):
    """
    Privilege for staff to record self-check-in, self-checkout, and self-leave requests.
    Permitted for all active staff and technicians within the tenant organization.
    """

    message = "Active organization staff membership is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return bool(
            request.organization_membership
            and request.organization_membership.is_active
        )
