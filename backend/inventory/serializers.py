from rest_framework import serializers

from inventory.models import (
    DeviceAssignment,
    InventoryDevice,
)


class InventoryDeviceSerializer(serializers.ModelSerializer):
    active_assignment_id = serializers.SerializerMethodField()
    assigned_service_number = serializers.SerializerMethodField()
    assigned_customer_number = serializers.SerializerMethodField()
    assigned_customer_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryDevice
        fields = [
            "id",
            "asset_tag",
            "device_type",
            "manufacturer",
            "model_name",
            "serial_number",
            "mac_address",
            "status",
            "notes",
            "active_assignment_id",
            "assigned_service_number",
            "assigned_customer_number",
            "assigned_customer_name",
            "created_at",
            "updated_at",
        ]

    def _get_active_assignment(self, obj):
        prefetched_assignments = getattr(
            obj,
            "active_assignments",
            None,
        )

        if prefetched_assignments is not None:
            return (
                prefetched_assignments[0]
                if prefetched_assignments
                else None
            )

        return (
            obj.assignments
            .filter(returned_at__isnull=True)
            .select_related(
                "service_account",
                "service_account__customer",
            )
            .first()
        )

    def get_active_assignment_id(self, obj):
        assignment = self._get_active_assignment(obj)

        if assignment is None:
            return None

        return assignment.id

    def get_assigned_service_number(self, obj):
        assignment = self._get_active_assignment(obj)

        if assignment is None:
            return None

        return assignment.service_account.service_number

    def get_assigned_customer_number(self, obj):
        assignment = self._get_active_assignment(obj)

        if assignment is None:
            return None

        return assignment.service_account.customer.customer_number

    def get_assigned_customer_name(self, obj):
        assignment = self._get_active_assignment(obj)

        if assignment is None:
            return None

        return assignment.service_account.customer.full_name


class DeviceAssignmentSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(
        source="device.asset_tag",
        read_only=True,
    )
    device_type = serializers.CharField(
        source="device.device_type",
        read_only=True,
    )
    device_status = serializers.CharField(
        source="device.status",
        read_only=True,
    )
    service_number = serializers.CharField(
        source="service_account.service_number",
        read_only=True,
    )
    customer_id = serializers.UUIDField(
        source="service_account.customer_id",
        read_only=True,
    )
    customer_number = serializers.CharField(
        source="service_account.customer.customer_number",
        read_only=True,
    )
    customer_name = serializers.CharField(
        source="service_account.customer.full_name",
        read_only=True,
    )
    assigned_by_email = serializers.EmailField(
        source="assigned_by.email",
        read_only=True,
        allow_null=True,
    )
    returned_by_email = serializers.EmailField(
        source="returned_by.email",
        read_only=True,
        allow_null=True,
    )
    is_active = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = DeviceAssignment
        fields = [
            "id",
            "device",
            "asset_tag",
            "device_type",
            "device_status",
            "service_account",
            "service_number",
            "customer_id",
            "customer_number",
            "customer_name",
            "assigned_by_email",
            "returned_by_email",
            "assigned_at",
            "returned_at",
            "return_condition",
            "assignment_notes",
            "return_notes",
            "is_active",
            "created_at",
            "updated_at",
        ]


class AssignDeviceSerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    service_account_id = serializers.UUIDField()
    assignment_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ReturnDeviceSerializer(serializers.Serializer):
    return_condition = serializers.ChoiceField(
        choices=DeviceAssignment.ReturnCondition.choices,
    )
    return_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )