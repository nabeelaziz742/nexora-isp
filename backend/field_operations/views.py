from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from field_operations.models import WorkOrder
from field_operations.serializers import (
    WorkOrderAssignmentSerializer,
    WorkOrderCompletionSerializer,
    WorkOrderCreateSerializer,
    WorkOrderDetailSerializer,
    WorkOrderDispatchSerializer,
    WorkOrderListSerializer,
    WorkOrderOnsiteSerializer,
)
from field_operations.services import (
    FieldOperationsDomainError,
    assign_work_order_technician,
    complete_work_order,
    create_work_order,
    dispatch_work_order,
    mark_work_order_onsite,
)
from tenancy.models import OrganizationMembership
from tenancy.permissions import HasActiveTenantContext


MANAGEMENT_ROLES = {
    OrganizationMembership.Role.OWNER,
    OrganizationMembership.Role.STAFF,
}


class FieldOperationsAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasActiveTenantContext,
    ]

    def is_management(self, request):
        return request.organization_role in MANAGEMENT_ROLES

    def is_technician(self, request):
        return (
            request.organization_role
            == OrganizationMembership.Role.TECHNICIAN
        )

    def deny(self):
        return Response(
            {
                "detail": (
                    "You do not have permission to perform "
                    "this field operation."
                ),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    def get_work_order_queryset(self, request):
        queryset = (
            WorkOrder.objects
            .for_organization(request.organization)
            .select_related(
                "customer",
                "service_account",
                "network_node",
                "complaint",
                "incident",
                "assigned_technician",
                "created_by",
            )
        )

        if self.is_technician(request):
            queryset = queryset.filter(
                assigned_technician=request.user,
            )

        return queryset

    def get_work_order(self, request, work_order_id):
        return (
            self.get_work_order_queryset(request)
            .filter(id=work_order_id)
            .first()
        )

    def domain_error_response(self, exc):
        return Response(
            {
                "detail": str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class WorkOrderListCreateAPIView(FieldOperationsAPIView):
    def get(self, request):
        if not (
            self.is_management(request)
            or self.is_technician(request)
        ):
            return self.deny()

        queryset = self.get_work_order_queryset(request)

        status_value = request.query_params.get("status")
        priority = request.query_params.get("priority")
        work_type = request.query_params.get("work_type")
        customer_id = request.query_params.get("customer_id")
        service_account_id = request.query_params.get(
            "service_account_id"
        )
        network_node_id = request.query_params.get(
            "network_node_id"
        )
        complaint_id = request.query_params.get("complaint_id")
        incident_id = request.query_params.get("incident_id")
        assigned_technician_id = request.query_params.get(
            "assigned_technician_id"
        )
        search = request.query_params.get(
            "search",
            "",
        ).strip()

        if status_value:
            queryset = queryset.filter(status=status_value)

        if priority:
            queryset = queryset.filter(priority=priority)

        if work_type:
            queryset = queryset.filter(work_type=work_type)

        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        if service_account_id:
            queryset = queryset.filter(
                service_account_id=service_account_id
            )

        if network_node_id:
            queryset = queryset.filter(
                network_node_id=network_node_id
            )

        if complaint_id:
            queryset = queryset.filter(
                complaint_id=complaint_id
            )

        if incident_id:
            queryset = queryset.filter(
                incident_id=incident_id
            )

        if (
            assigned_technician_id
            and self.is_management(request)
        ):
            queryset = queryset.filter(
                assigned_technician_id=(
                    assigned_technician_id
                )
            )

        if search:
            queryset = queryset.filter(
                Q(work_order_number__icontains=search)
                | Q(title__icontains=search)
                | Q(
                    customer__customer_number__icontains=search
                )
                | Q(customer__first_name__icontains=search)
                | Q(customer__last_name__icontains=search)
                | Q(
                    service_account__service_number__icontains=search
                )
                | Q(network_node__name__icontains=search)
                | Q(network_node__code__icontains=search)
                | Q(
                    complaint__complaint_number__icontains=search
                )
                | Q(
                    incident__incident_number__icontains=search
                )
            )

        serializer = WorkOrderListSerializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        if not self.is_management(request):
            return self.deny()

        serializer = WorkOrderCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = create_work_order(
                organization=request.organization,
                created_by=request.user,
                **serializer.validated_data,
            )
        except FieldOperationsDomainError as exc:
            return self.domain_error_response(exc)

        return Response(
            WorkOrderDetailSerializer(
                result.work_order,
            ).data,
            status=status.HTTP_201_CREATED,
        )


class WorkOrderDetailAPIView(FieldOperationsAPIView):
    def get(self, request, work_order_id):
        if not (
            self.is_management(request)
            or self.is_technician(request)
        ):
            return self.deny()

        work_order = self.get_work_order(
            request,
            work_order_id,
        )

        if work_order is None:
            return Response(
                {
                    "detail": "Not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            WorkOrderDetailSerializer(work_order).data
        )


class WorkOrderAssignmentAPIView(FieldOperationsAPIView):
    def post(self, request, work_order_id):
        if not self.is_management(request):
            return self.deny()

        serializer = WorkOrderAssignmentSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = assign_work_order_technician(
                organization=request.organization,
                work_order_id=work_order_id,
                technician_id=(
                    serializer.validated_data["technician_id"]
                ),
                actor=request.user,
            )
        except FieldOperationsDomainError as exc:
            return self.domain_error_response(exc)

        return Response(
            WorkOrderDetailSerializer(
                result.work_order,
            ).data
        )


class WorkOrderDispatchAPIView(FieldOperationsAPIView):
    def post(self, request, work_order_id):
        if not self.is_management(request):
            return self.deny()

        serializer = WorkOrderDispatchSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = dispatch_work_order(
                organization=request.organization,
                work_order_id=work_order_id,
                dispatch_notes=(
                    serializer.validated_data["dispatch_notes"]
                ),
                actor=request.user,
            )
        except FieldOperationsDomainError as exc:
            return self.domain_error_response(exc)

        return Response(
            WorkOrderDetailSerializer(
                result.work_order,
            ).data
        )


class WorkOrderOnsiteAPIView(FieldOperationsAPIView):
    def post(self, request, work_order_id):
        if not (
            self.is_management(request)
            or self.is_technician(request)
        ):
            return self.deny()

        serializer = WorkOrderOnsiteSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = mark_work_order_onsite(
                organization=request.organization,
                work_order_id=work_order_id,
                onsite_notes=(
                    serializer.validated_data["onsite_notes"]
                ),
                actor=request.user,
            )
        except FieldOperationsDomainError as exc:
            return self.domain_error_response(exc)

        return Response(
            WorkOrderDetailSerializer(
                result.work_order,
            ).data
        )


class WorkOrderCompletionAPIView(FieldOperationsAPIView):
    def post(self, request, work_order_id):
        if not (
            self.is_management(request)
            or self.is_technician(request)
        ):
            return self.deny()

        serializer = WorkOrderCompletionSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = complete_work_order(
                organization=request.organization,
                work_order_id=work_order_id,
                completion_notes=(
                    serializer.validated_data[
                        "completion_notes"
                    ]
                ),
                actor=request.user,
            )
        except FieldOperationsDomainError as exc:
            return self.domain_error_response(exc)

        return Response(
            WorkOrderDetailSerializer(
                result.work_order,
            ).data
        )