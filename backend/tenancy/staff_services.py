import re
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from tenancy.models import AuditLog, OrganizationMembership, StaffProfile


User = get_user_model()


MANAGEABLE_BASE_ROLES = {
    OrganizationMembership.Role.STAFF,
    OrganizationMembership.Role.TECHNICIAN,
}

VALID_OPERATIONAL_ROLES = {
    StaffProfile.Role.OWNER,
    StaffProfile.Role.ADMIN,
    StaffProfile.Role.MANAGER,
    StaffProfile.Role.ACCOUNTANT,
    StaffProfile.Role.OPERATOR,
    StaffProfile.Role.RECOVERY_OFFICER,
    StaffProfile.Role.TECHNICIAN,
    StaffProfile.Role.SUPPORT_OFFICER,
    StaffProfile.Role.FIELD_OFFICER,
    StaffProfile.Role.STAFF,
}


def _validate_role(role):
    if role not in VALID_OPERATIONAL_ROLES and role not in MANAGEABLE_BASE_ROLES:
        raise ValidationError(
            {
                "role": f"Role must be one of: {', '.join(sorted(list(VALID_OPERATIONAL_ROLES)))}."
            }
        )


def generate_staff_code(organization):
    """Generate sequential staff code {ORG}-STF-XXXX."""
    prefix = f"{organization.code.upper()}-STF-"
    last_profile = (
        StaffProfile.objects.filter(
            organization=organization,
            staff_code__startswith=prefix,
        )
        .order_by("-staff_code")
        .first()
    )

    if not last_profile:
        return f"{prefix}0001"

    match = re.search(r"(\d+)$", last_profile.staff_code)
    if match:
        next_seq = int(match.group(1)) + 1
        return f"{prefix}{next_seq:04d}"

    count = StaffProfile.objects.filter(organization=organization).count() + 1
    return f"{prefix}{count:04d}"


def get_or_create_staff_profile(membership):
    """Ensure a StaffProfile exists for an OrganizationMembership."""
    profile = getattr(membership, "profile", None)
    if not profile:
        profile = StaffProfile.objects.filter(membership=membership).first()
    if not profile:
        code = generate_staff_code(membership.organization)
        profile = StaffProfile.objects.create(
            organization=membership.organization,
            membership=membership,
            user=membership.user,
            staff_code=code,
            role=(
                StaffProfile.Role.OWNER
                if membership.role == OrganizationMembership.Role.OWNER
                else (
                    StaffProfile.Role.TECHNICIAN
                    if membership.role == OrganizationMembership.Role.TECHNICIAN
                    else StaffProfile.Role.STAFF
                )
            ),
            status=StaffProfile.Status.ACTIVE if membership.is_active else StaffProfile.Status.INACTIVE,
        )
    return profile


@transaction.atomic
def create_organization_staff(
    *,
    organization,
    actor,
    first_name,
    last_name,
    email,
    password,
    role=StaffProfile.Role.STAFF,
    phone="",
    alternate_phone="",
    cnic="",
    department="",
    designation="",
    assigned_area=None,
    supervisor=None,
    joining_date=None,
    notes="",
):
    _validate_role(role)

    normalized_email = email.strip().lower()

    if User.objects.filter(email__iexact=normalized_email).exists():
        raise ValidationError(
            {
                "email": "A user with this email already exists."
            }
        )

    user = User.objects.create_user(
        username=normalized_email,
        email=normalized_email,
        password=password,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
    )

    membership_role = (
        OrganizationMembership.Role.TECHNICIAN
        if role == StaffProfile.Role.TECHNICIAN
        else OrganizationMembership.Role.STAFF
    )

    membership = OrganizationMembership.objects.create(
        organization=organization,
        user=user,
        role=membership_role,
        is_active=True,
    )

    staff_code = generate_staff_code(organization)

    profile = StaffProfile.objects.create(
        organization=organization,
        membership=membership,
        user=user,
        staff_code=staff_code,
        phone=phone.strip() if phone else "",
        alternate_phone=alternate_phone.strip() if alternate_phone else "",
        cnic=cnic.strip() if cnic else "",
        department=department.strip() if department else "",
        designation=designation.strip() if designation else "",
        role=role,
        assigned_area=assigned_area,
        supervisor=supervisor,
        joining_date=joining_date,
        status=StaffProfile.Status.ACTIVE,
        notes=notes.strip() if notes else "",
    )

    AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action="ORGANIZATION_STAFF_CREATED",
        resource_type="OrganizationMembership",
        resource_id=str(membership.id),
        metadata={
            "user_id": str(user.id),
            "email": user.email,
            "role": profile.role,
            "staff_code": profile.staff_code,
            "department": profile.department,
        },
    )

    return membership


@transaction.atomic
def update_organization_staff(
    *,
    organization,
    actor,
    membership,
    first_name=None,
    last_name=None,
    role=None,
    phone=None,
    alternate_phone=None,
    cnic=None,
    department=None,
    designation=None,
    assigned_area=None,
    supervisor=None,
    joining_date=None,
    notes=None,
):
    if membership.organization_id != organization.id:
        raise ValidationError(
            {
                "detail": "Staff membership does not belong to organization."
            }
        )

    if membership.role == OrganizationMembership.Role.OWNER and role is not None and role != OrganizationMembership.Role.OWNER and role != StaffProfile.Role.OWNER:
        raise ValidationError(
            {
                "detail": "Owner role cannot be changed here."
            }
        )

    user = membership.user
    changed_user_fields = []

    if first_name is not None:
        user.first_name = first_name.strip()
        changed_user_fields.append("first_name")

    if last_name is not None:
        user.last_name = last_name.strip()
        changed_user_fields.append("last_name")

    if changed_user_fields:
        user.save(update_fields=changed_user_fields)

    profile = get_or_create_staff_profile(membership)
    changed_profile_fields = []

    if role is not None:
        _validate_role(role)
        profile.role = role
        changed_profile_fields.append("role")

        membership_role = (
            OrganizationMembership.Role.OWNER
            if role == StaffProfile.Role.OWNER or membership.role == OrganizationMembership.Role.OWNER
            else (
                OrganizationMembership.Role.TECHNICIAN
                if role == StaffProfile.Role.TECHNICIAN
                else OrganizationMembership.Role.STAFF
            )
        )
        if membership.role != membership_role:
            membership.role = membership_role
            membership.save(update_fields=["role", "updated_at"])

    if phone is not None:
        profile.phone = phone.strip()
        changed_profile_fields.append("phone")

    if alternate_phone is not None:
        profile.alternate_phone = alternate_phone.strip()
        changed_profile_fields.append("alternate_phone")

    if cnic is not None:
        profile.cnic = cnic.strip()
        changed_profile_fields.append("cnic")

    if department is not None:
        profile.department = department.strip()
        changed_profile_fields.append("department")

    if designation is not None:
        profile.designation = designation.strip()
        changed_profile_fields.append("designation")

    if assigned_area is not None:
        profile.assigned_area = assigned_area
        changed_profile_fields.append("assigned_area")

    if supervisor is not None:
        profile.supervisor = supervisor
        changed_profile_fields.append("supervisor")

    if joining_date is not None:
        profile.joining_date = joining_date
        changed_profile_fields.append("joining_date")

    if notes is not None:
        profile.notes = notes.strip()
        changed_profile_fields.append("notes")

    if changed_profile_fields:
        profile.save(update_fields=changed_profile_fields)

    AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action="ORGANIZATION_STAFF_UPDATED",
        resource_type="OrganizationMembership",
        resource_id=str(membership.id),
        metadata={
            "user_id": str(user.id),
            "email": user.email,
            "role": profile.role,
            "staff_code": profile.staff_code,
            "department": profile.department,
        },
    )

    return membership


@transaction.atomic
def set_organization_staff_active_state(
    *,
    organization,
    actor,
    membership,
    is_active,
):
    if membership.organization_id != organization.id:
        raise ValidationError(
            {
                "detail": "Staff membership does not belong to organization."
            }
        )

    if membership.role == OrganizationMembership.Role.OWNER:
        raise ValidationError(
            {
                "detail": "Owner membership cannot be deactivated here."
            }
        )

    membership.is_active = is_active
    membership.save(
        update_fields=[
            "is_active",
            "updated_at",
        ]
    )

    profile = get_or_create_staff_profile(membership)
    profile.status = StaffProfile.Status.ACTIVE if is_active else StaffProfile.Status.INACTIVE
    profile.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action=(
            "ORGANIZATION_STAFF_ACTIVATED"
            if is_active
            else "ORGANIZATION_STAFF_DEACTIVATED"
        ),
        resource_type="OrganizationMembership",
        resource_id=str(membership.id),
        metadata={
            "user_id": str(membership.user_id),
            "email": membership.user.email,
            "role": membership.role,
            "staff_code": profile.staff_code,
        },
    )

    return membership


@transaction.atomic
def set_organization_staff_status(
    *,
    organization,
    actor,
    membership,
    status,
):
    if membership.organization_id != organization.id:
        raise ValidationError(
            {
                "detail": "Staff membership does not belong to organization."
            }
        )

    if membership.role == OrganizationMembership.Role.OWNER and status != StaffProfile.Status.ACTIVE:
        raise ValidationError(
            {
                "detail": "Owner membership status cannot be deactivated or changed."
            }
        )

    if status not in StaffProfile.Status.values:
        raise ValidationError(
            {
                "status": f"Invalid status. Must be one of: {', '.join(StaffProfile.Status.values)}"
            }
        )

    profile = get_or_create_staff_profile(membership)
    profile.status = status
    profile.save(update_fields=["status", "updated_at"])

    is_active = status == StaffProfile.Status.ACTIVE
    if membership.is_active != is_active:
        membership.is_active = is_active
        membership.save(update_fields=["is_active", "updated_at"])

    AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action="ORGANIZATION_STAFF_STATUS_CHANGED",
        resource_type="OrganizationMembership",
        resource_id=str(membership.id),
        metadata={
            "user_id": str(membership.user_id),
            "email": membership.user.email,
            "new_status": status,
            "staff_code": profile.staff_code,
        },
    )

    return membership


def get_operator_workload(organization, user):
    """Compute authentic workload metrics for an operator/recovery officer."""
    from billing.models import RecoveryAllocation

    allocations = RecoveryAllocation.objects.for_organization(organization).filter(assigned_staff=user)

    total_assigned = allocations.count()
    pending_count = allocations.filter(status__in=[RecoveryAllocation.Status.ALLOCATED, RecoveryAllocation.Status.IN_PROGRESS]).count()
    contacted_count = allocations.filter(status=RecoveryAllocation.Status.CONTACTED).count()
    promises_count = allocations.filter(status=RecoveryAllocation.Status.PROMISE_RECEIVED).count()
    payments_collected_count = allocations.filter(status=RecoveryAllocation.Status.PAYMENT_COLLECTED).count()
    completed_count = allocations.filter(status=RecoveryAllocation.Status.COMPLETED).count()

    active_allocations = allocations.filter(
        status__in=[
            RecoveryAllocation.Status.ALLOCATED,
            RecoveryAllocation.Status.IN_PROGRESS,
            RecoveryAllocation.Status.CONTACTED,
            RecoveryAllocation.Status.PROMISE_RECEIVED,
        ]
    )
    outstanding_assigned_amount = active_allocations.aggregate(total=Sum("outstanding_amount"))["total"] or Decimal("0.00")

    return {
        "total_assigned": total_assigned,
        "pending_count": pending_count,
        "contacted_count": contacted_count,
        "promises_count": promises_count,
        "payments_collected_count": payments_collected_count,
        "completed_count": completed_count,
        "outstanding_assigned_amount": outstanding_assigned_amount,
    }