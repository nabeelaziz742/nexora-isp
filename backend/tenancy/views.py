from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.models import AuditLog, OrganizationMembership
from tenancy.permissions import (
    CanViewAuditLogs,
    HasActiveTenantContext,
    IsOrganizationOwner,
    IsOrganizationStaffOrOwner,
)
from tenancy.services import record_audit_log


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


class OrganizationProfileAPIView(APIView):
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationStaffOrOwner,
    ]

    def get(self, request):
        org = request.organization
        return Response(
            {
                "id": str(org.id),
                "name": org.name,
                "code": org.code,
                "phone": org.phone,
                "email": org.email,
                "address": org.address,
                "city": org.city,
                "timezone": org.timezone,
                "currency": org.currency,
                "is_active": org.is_active,
                "created_at": org.created_at,
                "updated_at": org.updated_at,
            }
        )

    def patch(self, request):
        if request.organization_role != OrganizationMembership.Role.OWNER:
            return Response(
                {"detail": "Only organization owners can modify company profile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        org = request.organization
        data = request.data

        if "name" in data:
            name = str(data["name"]).strip()
            if not name:
                return Response(
                    {"detail": "Company name cannot be empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            org.name = name

        if "phone" in data:
            org.phone = str(data["phone"]).strip()

        if "email" in data:
            org.email = str(data["email"]).strip()

        if "address" in data:
            org.address = str(data["address"]).strip()

        if "city" in data:
            org.city = str(data["city"]).strip()

        if "timezone" in data:
            org.timezone = str(data["timezone"]).strip()

        if "currency" in data:
            org.currency = str(data["currency"]).strip()

        org.save()

        record_audit_log(
            organization=org,
            actor=request.user,
            action="COMPANY_PROFILE_UPDATED",
            resource_type="Organization",
            resource_id=org.id,
            metadata={
                "name": org.name,
                "phone": org.phone,
                "email": org.email,
                "city": org.city,
            },
        )

        return Response(
            {
                "id": str(org.id),
                "name": org.name,
                "code": org.code,
                "phone": org.phone,
                "email": org.email,
                "address": org.address,
                "city": org.city,
                "timezone": org.timezone,
                "currency": org.currency,
                "is_active": org.is_active,
                "created_at": org.created_at,
                "updated_at": org.updated_at,
            }
        )


class AuditLogListView(APIView):
    permission_classes = [HasActiveTenantContext, CanViewAuditLogs]

    def get(self, request):
        qs = (
            AuditLog.objects
            .filter(organization=request.organization)
            .select_related("actor")
            .order_by("-created_at")
        )

        action = request.query_params.get("action", "").strip()
        resource_type = request.query_params.get("resource_type", "").strip()
        actor_id = request.query_params.get("actor_id", "").strip()
        start_date = request.query_params.get("start_date", "").strip()
        end_date = request.query_params.get("end_date", "").strip()
        search = request.query_params.get("search", "").strip()

        if action:
            qs = qs.filter(action__icontains=action)
        if resource_type:
            qs = qs.filter(resource_type__iexact=resource_type)
        if actor_id:
            qs = qs.filter(actor_id=actor_id)
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
        if search:
            qs = qs.filter(
                Q(action__icontains=search)
                | Q(resource_type__icontains=search)
                | Q(resource_id__icontains=search)
                | Q(actor__email__icontains=search)
                | Q(actor__first_name__icontains=search)
                | Q(actor__last_name__icontains=search)
            )

        logs = qs[:200]

        data = []
        for log in logs:
            actor_name = ""
            actor_email = ""
            if log.actor:
                actor_name = f"{log.actor.first_name} {log.actor.last_name}".strip() or log.actor.email
                actor_email = log.actor.email

            data.append({
                "id": str(log.id),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "actor_id": str(log.actor_id) if log.actor_id else None,
                "actor_name": actor_name,
                "actor_email": actor_email,
                "metadata": log.metadata,
                "created_at": log.created_at.isoformat(),
            })

        return Response(data, status=status.HTTP_200_OK)
