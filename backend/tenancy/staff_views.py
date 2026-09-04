from django.db.models import Q
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
)
from rest_framework.views import APIView

from customers.models import Area
from tenancy.models import OrganizationMembership, StaffProfile
from tenancy.permissions import IsOrganizationOwner, IsOrganizationStaffOrOwner
from tenancy.staff_serializers import (
    CreateOrganizationStaffSerializer,
    OrganizationStaffSerializer,
    StaffActiveStateSerializer,
    StaffStatusSerializer,
    UpdateOrganizationStaffSerializer,
)
from tenancy.staff_services import (
    create_organization_staff,
    get_operator_workload,
    set_organization_staff_active_state,
    set_organization_staff_status,
    update_organization_staff,
)


class OrganizationStaffListCreateView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        role_filter = request.query_params.get("role", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        dept_filter = request.query_params.get("department", "").strip()
        area_filter = request.query_params.get("area_id", "").strip()
        search_query = request.query_params.get("search", "").strip()

        memberships = (
            OrganizationMembership.objects.filter(
                organization=request.organization,
            )
            .select_related("user", "profile", "profile__assigned_area")
            .order_by("user__first_name", "user__last_name")
        )

        if search_query:
            memberships = memberships.filter(
                Q(user__first_name__icontains=search_query)
                | Q(user__last_name__icontains=search_query)
                | Q(user__email__icontains=search_query)
                | Q(profile__staff_code__icontains=search_query)
                | Q(profile__phone__icontains=search_query)
                | Q(profile__department__icontains=search_query)
                | Q(profile__designation__icontains=search_query)
            )

        if role_filter:
            memberships = memberships.filter(
                Q(role__iexact=role_filter) | Q(profile__role__iexact=role_filter)
            )

        if status_filter:
            if status_filter.upper() == "ACTIVE":
                memberships = memberships.filter(is_active=True)
            elif status_filter.upper() == "INACTIVE":
                memberships = memberships.filter(is_active=False)
            else:
                memberships = memberships.filter(profile__status__iexact=status_filter)

        if dept_filter:
            memberships = memberships.filter(profile__department__iexact=dept_filter)

        if area_filter:
            memberships = memberships.filter(profile__assigned_area_id=area_filter)

        serializer = OrganizationStaffSerializer(
            memberships,
            many=True,
        )

        return Response(
            serializer.data,
            status=HTTP_200_OK,
        )

    def post(self, request):
        serializer = CreateOrganizationStaffSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        assigned_area = None
        area_id = serializer.validated_data.get("assigned_area_id")
        if area_id:
            assigned_area = Area.objects.filter(organization=request.organization, id=area_id).first()

        supervisor = None
        sup_id = serializer.validated_data.get("supervisor_id")
        if sup_id:
            supervisor = StaffProfile.objects.filter(organization=request.organization, id=sup_id).first()

        create_data = {k: v for k, v in serializer.validated_data.items() if k not in ["assigned_area_id", "supervisor_id"]}

        membership = create_organization_staff(
            organization=request.organization,
            actor=request.user,
            assigned_area=assigned_area,
            supervisor=supervisor,
            **create_data,
        )

        response_serializer = OrganizationStaffSerializer(
            membership,
        )

        return Response(
            response_serializer.data,
            status=HTTP_201_CREATED,
        )


class OrganizationStaffDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get_membership(self, request, membership_id):
        membership = (
            OrganizationMembership.objects.filter(
                organization=request.organization,
                id=membership_id,
            )
            .select_related("user", "profile", "profile__assigned_area")
            .first()
        )
        if not membership:
            raise NotFound({"detail": "Staff member not found."})
        return membership

    def get(self, request, membership_id):
        membership = self.get_membership(
            request,
            membership_id,
        )

        serializer = OrganizationStaffSerializer(
            membership,
        )

        return Response(
            serializer.data,
            status=HTTP_200_OK,
        )

    def patch(self, request, membership_id):
        membership = self.get_membership(
            request,
            membership_id,
        )

        serializer = UpdateOrganizationStaffSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        assigned_area = None
        if "assigned_area_id" in serializer.validated_data:
            area_id = serializer.validated_data.pop("assigned_area_id")
            if area_id:
                assigned_area = Area.objects.filter(organization=request.organization, id=area_id).first()

        supervisor = None
        if "supervisor_id" in serializer.validated_data:
            sup_id = serializer.validated_data.pop("supervisor_id")
            if sup_id:
                supervisor = StaffProfile.objects.filter(organization=request.organization, id=sup_id).first()

        update_kwargs = dict(serializer.validated_data)
        if "assigned_area_id" in request.data:
            update_kwargs["assigned_area"] = assigned_area
        if "supervisor_id" in request.data:
            update_kwargs["supervisor"] = supervisor

        membership = update_organization_staff(
            organization=request.organization,
            actor=request.user,
            membership=membership,
            **update_kwargs,
        )

        response_serializer = OrganizationStaffSerializer(
            membership,
        )

        return Response(
            response_serializer.data,
            status=HTTP_200_OK,
        )


class OrganizationStaffActiveStateView(APIView):
    permission_classes = [IsOrganizationOwner]

    def patch(self, request, membership_id):
        membership = (
            OrganizationMembership.objects.filter(
                organization=request.organization,
                id=membership_id,
            )
            .select_related("user", "profile")
            .first()
        )
        if not membership:
            raise NotFound({"detail": "Staff member not found."})

        serializer = StaffActiveStateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        membership = set_organization_staff_active_state(
            organization=request.organization,
            actor=request.user,
            membership=membership,
            is_active=serializer.validated_data["is_active"],
        )

        return Response(
            OrganizationStaffSerializer(membership).data,
            status=HTTP_200_OK,
        )


class OrganizationStaffStatusView(APIView):
    permission_classes = [IsOrganizationOwner]

    def patch(self, request, membership_id):
        membership = (
            OrganizationMembership.objects.filter(
                organization=request.organization,
                id=membership_id,
            )
            .select_related("user", "profile")
            .first()
        )
        if not membership:
            raise NotFound({"detail": "Staff member not found."})

        serializer = StaffStatusSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        membership = set_organization_staff_status(
            organization=request.organization,
            actor=request.user,
            membership=membership,
            status=serializer.validated_data["status"],
        )

        return Response(
            OrganizationStaffSerializer(membership).data,
            status=HTTP_200_OK,
        )


class OperatorListView(APIView):
    """
    List operators and recovery officers with authentic live workload metrics.
    """
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        area_id = request.query_params.get("area_id", "").strip()
        search = request.query_params.get("search", "").strip()

        memberships = (
            OrganizationMembership.objects.filter(
                organization=request.organization,
                is_active=True,
            )
            .select_related("user", "profile", "profile__assigned_area")
            .order_by("user__first_name", "user__last_name")
        )

        if area_id:
            memberships = memberships.filter(profile__assigned_area_id=area_id)

        if search:
            memberships = memberships.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(profile__staff_code__icontains=search)
            )

        results = []
        for m in memberships:
            profile = getattr(m, "profile", None) or StaffProfile.objects.filter(membership=m).first()
            workload = get_operator_workload(request.organization, m.user)
            results.append(
                {
                    "membership_id": str(m.id),
                    "user_id": str(m.user_id),
                    "staff_code": profile.staff_code if profile else "",
                    "full_name": m.user.get_full_name() or m.user.email,
                    "email": m.user.email,
                    "phone": profile.phone if profile else "",
                    "role": profile.role if profile else m.role,
                    "department": profile.department if profile else "",
                    "designation": profile.designation if profile else "",
                    "assigned_area_id": str(profile.assigned_area_id) if profile and profile.assigned_area_id else None,
                    "assigned_area_name": profile.assigned_area.name if profile and profile.assigned_area else None,
                    "status": profile.status if profile else ("ACTIVE" if m.is_active else "INACTIVE"),
                    "workload": {
                        "total_assigned": workload["total_assigned"],
                        "pending_count": workload["pending_count"],
                        "contacted_count": workload["contacted_count"],
                        "promises_count": workload["promises_count"],
                        "payments_collected_count": workload["payments_collected_count"],
                        "completed_count": workload["completed_count"],
                        "outstanding_assigned_amount": str(workload["outstanding_assigned_amount"]),
                    },
                }
            )

        return Response(results, status=HTTP_200_OK)


class OperatorWorkloadDetailView(APIView):
    """
    Get detailed workload and active allocations for a specific operator.
    """
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request, user_id):
        membership = (
            OrganizationMembership.objects.filter(
                organization=request.organization,
                user_id=user_id,
            )
            .select_related("user", "profile", "profile__assigned_area")
            .first()
        )
        if not membership:
            raise NotFound({"detail": "Operator not found in organization."})

        from billing.models import RecoveryAllocation

        workload = get_operator_workload(request.organization, membership.user)
        active_allocs = (
            RecoveryAllocation.objects.for_organization(request.organization)
            .filter(
                assigned_staff=membership.user,
                status__in=[
                    RecoveryAllocation.Status.ALLOCATED,
                    RecoveryAllocation.Status.IN_PROGRESS,
                    RecoveryAllocation.Status.CONTACTED,
                    RecoveryAllocation.Status.PROMISE_RECEIVED,
                ],
            )
            .select_related("customer", "service_account", "invoice")
            .order_by("due_date", "-created_at")
        )

        profile = getattr(membership, "profile", None) or StaffProfile.objects.filter(membership=membership).first()

        data = {
            "membership_id": str(membership.id),
            "user_id": str(membership.user_id),
            "staff_code": profile.staff_code if profile else "",
            "full_name": membership.user.get_full_name() or membership.user.email,
            "email": membership.user.email,
            "phone": profile.phone if profile else "",
            "role": profile.role if profile else membership.role,
            "assigned_area_name": profile.assigned_area.name if profile and profile.assigned_area else None,
            "workload": {
                "total_assigned": workload["total_assigned"],
                "pending_count": workload["pending_count"],
                "contacted_count": workload["contacted_count"],
                "promises_count": workload["promises_count"],
                "payments_collected_count": workload["payments_collected_count"],
                "completed_count": workload["completed_count"],
                "outstanding_assigned_amount": str(workload["outstanding_assigned_amount"]),
            },
            "active_allocations": [
                {
                    "id": str(a.id),
                    "allocation_number": a.allocation_number,
                    "customer_id": str(a.customer_id),
                    "customer_name": a.customer.full_name,
                    "customer_number": a.customer.customer_number,
                    "phone": a.customer.phone,
                    "outstanding_amount": str(a.outstanding_amount),
                    "priority": a.priority,
                    "status": a.status,
                    "assigned_date": a.assigned_date.isoformat(),
                    "due_date": a.due_date.isoformat() if a.due_date else None,
                }
                for a in active_allocs
            ],
        }

        return Response(data, status=HTTP_200_OK)