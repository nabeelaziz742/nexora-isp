from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from field_operations.maintenance import (
    MaintenanceDomainError,
    complete_maintenance,
    restore_maintenance,
    schedule_maintenance,
    start_maintenance,
)
from field_operations.maintenance_serializers import (
    MaintenanceCompletionSerializer,
    MaintenanceScheduleSerializer,
)
from field_operations.models import WorkOrder
from field_operations.serializers import WorkOrderDetailSerializer
from tenancy.models import OrganizationMembership
from tenancy.permissions import HasActiveTenantContext


def maintenance_data(work_order):
    data = dict(WorkOrderDetailSerializer(work_order).data)
    data.update(
        {
            "maintenance_notes": work_order.maintenance_notes,
            "scheduled_at": work_order.scheduled_at,
            "started_at": work_order.started_at,
            "restored_at": work_order.restored_at,
        }
    )
    return data


class MaintenanceAPIView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext]

    def management(self, request):
        return request.organization_role in {
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.STAFF,
        }

    def allowed(self, request, work_order_id):
        qs = WorkOrder.objects.for_organization(request.organization).filter(
            id=work_order_id,
            work_type=WorkOrder.WorkType.NETWORK_MAINTENANCE,
        )
        if request.organization_role == OrganizationMembership.Role.TECHNICIAN:
            qs = qs.filter(assigned_technician=request.user)
        return qs.first()

    def deny(self):
        return Response(
            {"detail": "You do not have permission to perform this maintenance operation."},
            status=status.HTTP_403_FORBIDDEN,
        )

    def error(self, exc):
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class MaintenanceScheduleAPIView(MaintenanceAPIView):
    def post(self, request, work_order_id):
        if not self.management(request):
            return self.deny()
        if self.allowed(request, work_order_id) is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = MaintenanceScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = schedule_maintenance(
                organization=request.organization,
                work_order_id=work_order_id,
                actor=request.user,
                **serializer.validated_data,
            )
        except MaintenanceDomainError as exc:
            return self.error(exc)
        return Response(maintenance_data(result.work_order))


class MaintenanceStartAPIView(MaintenanceAPIView):
    def post(self, request, work_order_id):
        if not (self.management(request) or request.organization_role == OrganizationMembership.Role.TECHNICIAN):
            return self.deny()
        if self.allowed(request, work_order_id) is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            result = start_maintenance(
                organization=request.organization,
                work_order_id=work_order_id,
                actor=request.user,
            )
        except MaintenanceDomainError as exc:
            return self.error(exc)
        return Response(maintenance_data(result.work_order))


class MaintenanceCompletionAPIView(MaintenanceAPIView):
    def post(self, request, work_order_id):
        if not (self.management(request) or request.organization_role == OrganizationMembership.Role.TECHNICIAN):
            return self.deny()
        if self.allowed(request, work_order_id) is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = MaintenanceCompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = complete_maintenance(
                organization=request.organization,
                work_order_id=work_order_id,
                actor=request.user,
                **serializer.validated_data,
            )
        except MaintenanceDomainError as exc:
            return self.error(exc)
        return Response(maintenance_data(result.work_order))


class MaintenanceRestoreAPIView(MaintenanceAPIView):
    def post(self, request, work_order_id):
        if not (self.management(request) or request.organization_role == OrganizationMembership.Role.TECHNICIAN):
            return self.deny()
        if self.allowed(request, work_order_id) is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            result = restore_maintenance(
                organization=request.organization,
                work_order_id=work_order_id,
                actor=request.user,
            )
        except MaintenanceDomainError as exc:
            return self.error(exc)
        return Response(maintenance_data(result.work_order))
