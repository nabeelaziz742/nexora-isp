from django.db.models import Prefetch, Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import (
    DeviceAssignment,
    InventoryDevice,
)
from inventory.serializers import (
    AssignDeviceSerializer,
    DeviceAssignmentSerializer,
    InventoryDeviceSerializer,
    ReturnDeviceSerializer,
)
from inventory.services import (
    InventoryCustodyError,
    assign_device_to_service,
    return_device_from_service,
)
from tenancy.permissions import IsOrganizationStaffOrOwner


def _device_queryset_for_organization(organization):
    active_assignments = (
        DeviceAssignment.objects
        .for_organization(organization)
        .filter(returned_at__isnull=True)
        .select_related(
            "service_account",
            "service_account__customer",
        )
    )

    return (
        InventoryDevice.objects
        .for_organization(organization)
        .prefetch_related(
            Prefetch(
                "assignments",
                queryset=active_assignments,
                to_attr="active_assignments",
            )
        )
    )


class InventoryDeviceListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        devices = _device_queryset_for_organization(
            request.organization
        )

        device_status = request.query_params.get(
            "status",
            "",
        ).strip()

        device_type = request.query_params.get(
            "type",
            "",
        ).strip()

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        if device_status:
            devices = devices.filter(
                status=device_status
            )

        if device_type:
            devices = devices.filter(
                device_type=device_type
            )

        if search:
            devices = devices.filter(
                Q(asset_tag__icontains=search)
                | Q(manufacturer__icontains=search)
                | Q(model_name__icontains=search)
                | Q(serial_number__icontains=search)
                | Q(mac_address__icontains=search)
            )

        devices = devices.order_by("asset_tag")

        serializer = InventoryDeviceSerializer(
            devices,
            many=True,
        )

        return Response(serializer.data)


class InventoryDeviceDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request, device_id):
        try:
            device = (
                _device_queryset_for_organization(
                    request.organization
                )
                .get(id=device_id)
            )
        except InventoryDevice.DoesNotExist as exc:
            raise NotFound(
                "Inventory device was not found "
                "in this organization."
            ) from exc

        serializer = InventoryDeviceSerializer(device)

        return Response(serializer.data)


class DeviceAssignmentListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        assignments = (
            DeviceAssignment.objects
            .for_organization(request.organization)
            .select_related(
                "device",
                "service_account",
                "service_account__customer",
                "assigned_by",
                "returned_by",
            )
        )

        device_id = request.query_params.get(
            "device_id",
            "",
        ).strip()

        service_account_id = request.query_params.get(
            "service_account_id",
            "",
        ).strip()

        active = request.query_params.get(
            "active",
            "",
        ).strip().lower()

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        if device_id:
            assignments = assignments.filter(
                device_id=device_id
            )

        if service_account_id:
            assignments = assignments.filter(
                service_account_id=service_account_id
            )

        if active == "true":
            assignments = assignments.filter(
                returned_at__isnull=True
            )
        elif active == "false":
            assignments = assignments.filter(
                returned_at__isnull=False
            )

        if search:
            assignments = assignments.filter(
                Q(device__asset_tag__icontains=search)
                | Q(
                    service_account__service_number__icontains=search
                )
                | Q(
                    service_account__customer__customer_number__icontains=search
                )
                | Q(
                    service_account__customer__first_name__icontains=search
                )
                | Q(
                    service_account__customer__last_name__icontains=search
                )
            )

        assignments = assignments.order_by("-assigned_at")

        serializer = DeviceAssignmentSerializer(
            assignments,
            many=True,
        )

        return Response(serializer.data)


class AssignDeviceView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request):
        input_serializer = AssignDeviceSerializer(
            data=request.data
        )
        input_serializer.is_valid(raise_exception=True)

        try:
            result = assign_device_to_service(
                organization=request.organization,
                actor=request.user,
                device_id=input_serializer.validated_data[
                    "device_id"
                ],
                service_account_id=(
                    input_serializer.validated_data[
                        "service_account_id"
                    ]
                ),
                assignment_notes=(
                    input_serializer.validated_data[
                        "assignment_notes"
                    ]
                ),
            )
        except InventoryCustodyError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment = (
            DeviceAssignment.objects
            .for_organization(request.organization)
            .select_related(
                "device",
                "service_account",
                "service_account__customer",
                "assigned_by",
                "returned_by",
            )
            .get(id=result.assignment.id)
        )

        serializer = DeviceAssignmentSerializer(
            assignment
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ReturnDeviceView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, assignment_id):
        input_serializer = ReturnDeviceSerializer(
            data=request.data
        )
        input_serializer.is_valid(raise_exception=True)

        try:
            result = return_device_from_service(
                organization=request.organization,
                actor=request.user,
                assignment_id=assignment_id,
                return_condition=(
                    input_serializer.validated_data[
                        "return_condition"
                    ]
                ),
                return_notes=(
                    input_serializer.validated_data[
                        "return_notes"
                    ]
                ),
            )
        except InventoryCustodyError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment = (
            DeviceAssignment.objects
            .for_organization(request.organization)
            .select_related(
                "device",
                "service_account",
                "service_account__customer",
                "assigned_by",
                "returned_by",
            )
            .get(id=result.assignment.id)
        )

        serializer = DeviceAssignmentSerializer(
            assignment
        )

        return Response(serializer.data)