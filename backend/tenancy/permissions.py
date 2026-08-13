from rest_framework.permissions import BasePermission
from tenancy.models import OrganizationMembership


class HasActiveTenantContext(BasePermission):
    message = "Active tenant context is required."

    def has_permission(self, request, view):
        organization = getattr(
            request,
            "organization",
            None,
        )
        membership = getattr(
            request,
            "organization_membership",
            None,
        )
        role = getattr(
            request,
            "organization_role",
            None,
        )
        user = getattr(
            request,
            "user",
            None,
        )

        if organization is None:
            return False

        if membership is None:
            return False

        if role is None:
            return False

        if user is None:
            return False

        if not user.is_authenticated:
            return False

        if not organization.is_active:
            return False

        if not membership.is_active:
            return False

        if membership.organization_id != organization.id:
            return False

        if membership.user_id != user.id:
            return False

        if membership.role != role:
            return False

        return True


class IsOrganizationOwner(HasActiveTenantContext):
    message = "Organization owner access is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return (
            request.organization_role
            == OrganizationMembership.Role.OWNER
        )


class IsOrganizationStaffOrOwner(HasActiveTenantContext):
    message = "Organization staff or owner access is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return request.organization_role in {
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.STAFF,
        }


class IsOrganizationTechnician(HasActiveTenantContext):
    message = "Organization technician access is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return (
            request.organization_role
            == OrganizationMembership.Role.TECHNICIAN
        )

