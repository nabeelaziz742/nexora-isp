from rest_framework.permissions import BasePermission

from tenancy.models import OrganizationMembership, StaffProfile


def get_effective_role(request) -> str:
    """
    Safely resolves the authenticated user's operational role:
    1. If membership is OWNER or organization_role is OWNER -> "OWNER"
    2. Check linked StaffProfile.role
    3. Fallback safely to membership.role ("STAFF" or "TECHNICIAN")
    """
    membership = getattr(request, "organization_membership", None)
    if not membership or not membership.is_active:
        return ""

    if membership.role == OrganizationMembership.Role.OWNER:
        return StaffProfile.Role.OWNER

    profile = getattr(membership, "profile", None)
    if profile is None:
        try:
            profile = StaffProfile.objects.filter(membership=membership).first()
        except Exception:
            profile = None

    if profile and profile.role:
        return profile.role

    if membership.role == OrganizationMembership.Role.TECHNICIAN:
        return StaffProfile.Role.TECHNICIAN

    return StaffProfile.Role.STAFF


class HasActiveTenantContext(BasePermission):
    message = "Active tenant context is required."

    def has_permission(self, request, view):
        organization = getattr(request, "organization", None)
        membership = getattr(request, "organization_membership", None)
        role = getattr(request, "organization_role", None)
        user = getattr(request, "user", None)

        if organization is None or membership is None or role is None or user is None:
            return False

        if not user.is_authenticated:
            return False

        if not organization.is_active or not membership.is_active:
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

        return get_effective_role(request) == StaffProfile.Role.OWNER


class IsOrganizationAdminOrOwner(HasActiveTenantContext):
    message = "Organization owner or administrator access is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
        }


class IsOrganizationManagerOrAdmin(HasActiveTenantContext):
    message = "Organization manager or administrator access is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
        }


class IsOrganizationStaffOrOwner(HasActiveTenantContext):
    message = "Organization staff or owner access is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        # Any active staff/owner/technician membership that is not unauthenticated
        return request.organization_role in {
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.STAFF,
        }


class IsOrganizationTechnician(HasActiveTenantContext):
    message = "Organization technician access is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.TECHNICIAN,
            StaffProfile.Role.FIELD_OFFICER,
        }


# ==============================================================================
# FINE-GRAINED DOMAIN CAPABILITIES (BATCH 13 RBAC HARDENING)
# ==============================================================================

class CanManageAccounting(HasActiveTenantContext):
    message = "Accounting management privilege is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.ACCOUNTANT,
        }


class CanCloseFinancialPeriod(HasActiveTenantContext):
    message = "Only owners, administrators, or senior accountants can close financial periods."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.ACCOUNTANT,
        }


class CanManageBilling(HasActiveTenantContext):
    message = "Billing and collections privilege is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
            StaffProfile.Role.ACCOUNTANT,
            StaffProfile.Role.OPERATOR,
        }


class CanCancelInvoice(HasActiveTenantContext):
    message = "Only owners, administrators, or accountants can void or cancel invoices."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.ACCOUNTANT,
        }


class CanManageInventory(HasActiveTenantContext):
    message = "Inventory management privilege is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
            StaffProfile.Role.OPERATOR,
            StaffProfile.Role.FIELD_OFFICER,
            StaffProfile.Role.STAFF,
        }


class CanAdjustInventory(HasActiveTenantContext):
    message = "Only owners, administrators, or inventory managers can adjust warehouse stock counts."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
        }


class CanManagePos(HasActiveTenantContext):
    message = "Point of Sale cashier privilege is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
            StaffProfile.Role.OPERATOR,
            StaffProfile.Role.STAFF,
        }


class CanCancelPosSale(HasActiveTenantContext):
    message = "Only owners, administrators, or managers can cancel POS sales and reverse journals."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
        }


class CanManageNetwork(HasActiveTenantContext):
    message = "Network operations privilege is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
            StaffProfile.Role.TECHNICIAN,
        }


class CanManageStaff(HasActiveTenantContext):
    message = "Staff management privilege is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
        }


class CanViewAuditLogs(HasActiveTenantContext):
    message = "Audit log investigation privilege is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
        }


class CanViewFinancialReports(HasActiveTenantContext):
    message = "Financial report access is restricted to owners, managers, and accountants."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
            StaffProfile.Role.ACCOUNTANT,
        }


class CanManageSupport(HasActiveTenantContext):
    message = "Customer support management privilege is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
            StaffProfile.Role.SUPPORT_OFFICER,
            StaffProfile.Role.OPERATOR,
            StaffProfile.Role.STAFF,
        }


class CanManageRecovery(HasActiveTenantContext):
    message = "Recovery and debt collection privilege is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return get_effective_role(request) in {
            StaffProfile.Role.OWNER,
            StaffProfile.Role.ADMIN,
            StaffProfile.Role.MANAGER,
            StaffProfile.Role.RECOVERY_OFFICER,
            StaffProfile.Role.OPERATOR,
        }
