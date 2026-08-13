from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.models import OrganizationMembership
from tenancy.permissions import (
    HasActiveTenantContext,
    IsOrganizationOwner,
    IsOrganizationStaffOrOwner,
)


User = get_user_model()


def serialize_staff_membership(membership):
    user = membership.user

    return {
        "id": str(membership.id),
        "user_id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": (
            f"{user.first_name} {user.last_name}"
        ).strip(),
        "role": membership.role,
        "is_active": membership.is_active,
        "created_at": membership.created_at,
        "updated_at": membership.updated_at,
    }


class OwnerSecurityCheckView(APIView):
    permission_classes = [IsOrganizationOwner]

    def get(self, request):
        return Response(
            {
                "detail": "OWNER ACCESS GRANTED",
                "organization_code": request.organization.code,
                "role": request.organization_role,
            }
        )


class OrganizationTechnicianListAPIView(APIView):
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationStaffOrOwner,
    ]

    def get(self, request):
        memberships = (
            OrganizationMembership.objects
            .filter(
                organization=request.organization,
                role=OrganizationMembership.Role.TECHNICIAN,
                is_active=True,
                user__is_active=True,
            )
            .select_related("user")
            .order_by(
                "user__first_name",
                "user__last_name",
                "user__email",
            )
        )

        return Response(
            [
                {
                    "id": str(membership.user.id),
                    "email": membership.user.email,
                    "first_name": membership.user.first_name,
                    "last_name": membership.user.last_name,
                    "full_name": (
                        f"{membership.user.first_name} "
                        f"{membership.user.last_name}"
                    ).strip(),
                }
                for membership in memberships
            ]
        )


class OrganizationStaffListCreateAPIView(APIView):
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationOwner,
    ]

    def get(self, request):
        memberships = (
            OrganizationMembership.objects
            .filter(
                organization=request.organization,
            )
            .select_related("user")
            .order_by(
                "role",
                "user__first_name",
                "user__last_name",
                "user__email",
            )
        )

        return Response(
            [
                serialize_staff_membership(membership)
                for membership in memberships
            ]
        )

    @transaction.atomic
    def post(self, request):
        first_name = request.data.get("first_name", "").strip()
        last_name = request.data.get("last_name", "").strip()
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")
        role = request.data.get("role", "").strip().upper()

        allowed_roles = {
            OrganizationMembership.Role.STAFF,
            OrganizationMembership.Role.TECHNICIAN,
        }

        if not first_name:
            return Response(
                {"detail": "First name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not password:
            return Response(
                {"detail": "Password is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if role not in allowed_roles:
            return Response(
                {
                    "detail": (
                        "Role must be STAFF or TECHNICIAN."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()

        if user is None:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
        else:
            if OrganizationMembership.objects.filter(
                organization=request.organization,
                user=user,
            ).exists():
                return Response(
                    {
                        "detail": (
                            "This user is already a member "
                            "of this organization."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        membership = OrganizationMembership.objects.create(
            organization=request.organization,
            user=user,
            role=role,
            is_active=True,
        )

        return Response(
            serialize_staff_membership(membership),
            status=status.HTTP_201_CREATED,
        )


class OrganizationStaffActiveStateAPIView(APIView):
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationOwner,
    ]

    def patch(self, request, membership_id):
        membership = get_object_or_404(
            OrganizationMembership.objects.select_related("user"),
            id=membership_id,
            organization=request.organization,
        )

        if membership.role == OrganizationMembership.Role.OWNER:
            return Response(
                {
                    "detail": (
                        "Owner access cannot be changed "
                        "from staff management."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_active = request.data.get("is_active")

        if not isinstance(is_active, bool):
            return Response(
                {
                    "detail": (
                        "is_active must be a boolean value."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership.is_active = is_active
        membership.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        return Response(
            serialize_staff_membership(membership)
        )