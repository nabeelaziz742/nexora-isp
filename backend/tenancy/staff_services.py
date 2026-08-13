from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

from tenancy.models import AuditLog, OrganizationMembership


User = get_user_model()


MANAGEABLE_ROLES = {
    OrganizationMembership.Role.STAFF,
    OrganizationMembership.Role.TECHNICIAN,
}


def _validate_role(role):
    if role not in MANAGEABLE_ROLES:
        raise ValidationError(
            {
                "role": (
                    "Role must be STAFF or TECHNICIAN."
                )
            }
        )


@transaction.atomic
def create_organization_staff(
    *,
    organization,
    actor,
    first_name,
    last_name,
    email,
    password,
    role,
):
    _validate_role(role)

    normalized_email = email.strip().lower()

    if User.objects.filter(email__iexact=normalized_email).exists():
        raise ValidationError(
            {
                "email": (
                    "A user with this email already exists."
                )
            }
        )

    user = User.objects.create_user(
        username=normalized_email,
        email=normalized_email,
        password=password,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
    )

    membership = OrganizationMembership.objects.create(
        organization=organization,
        user=user,
        role=role,
        is_active=True,
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
            "role": membership.role,
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
                "detail": "Owner membership cannot be modified here."
            }
        )

    user = membership.user

    changed_fields = []

    if first_name is not None:
        user.first_name = first_name.strip()
        changed_fields.append("first_name")

    if last_name is not None:
        user.last_name = last_name.strip()
        changed_fields.append("last_name")

    if changed_fields:
        user.save(
            update_fields=[
                *changed_fields,
                "updated_at",
            ]
        )

    if role is not None:
        _validate_role(role)

        membership.role = role
        membership.save(
            update_fields=[
                "role",
                "updated_at",
            ]
        )

    AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action="ORGANIZATION_STAFF_UPDATED",
        resource_type="OrganizationMembership",
        resource_id=str(membership.id),
        metadata={
            "user_id": str(user.id),
            "email": user.email,
            "role": membership.role,
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
        },
    )

    return membership