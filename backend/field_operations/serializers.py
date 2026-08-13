from rest_framework import serializers

from field_operations.models import WorkOrder


class WorkOrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    service_account_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    network_node_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    complaint_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    incident_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    work_type = serializers.ChoiceField(
        choices=WorkOrder.WorkType.choices,
    )
    priority = serializers.ChoiceField(
        choices=WorkOrder.Priority.choices,
    )

    title = serializers.CharField(
        max_length=255,
    )
    description = serializers.CharField()


class WorkOrderAssignmentSerializer(serializers.Serializer):
    technician_id = serializers.UUIDField()


class WorkOrderDispatchSerializer(serializers.Serializer):
    dispatch_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class WorkOrderOnsiteSerializer(serializers.Serializer):
    onsite_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class WorkOrderCompletionSerializer(serializers.Serializer):
    completion_notes = serializers.CharField()


class WorkOrderListSerializer(serializers.ModelSerializer):
    customer_number = serializers.CharField(
        source="customer.customer_number",
        allow_null=True,
        read_only=True,
    )
    customer_name = serializers.SerializerMethodField()

    service_number = serializers.CharField(
        source="service_account.service_number",
        allow_null=True,
        read_only=True,
    )

    network_node_name = serializers.CharField(
        source="network_node.name",
        allow_null=True,
        read_only=True,
    )
    network_node_code = serializers.CharField(
        source="network_node.code",
        allow_null=True,
        read_only=True,
    )

    complaint_number = serializers.CharField(
        source="complaint.complaint_number",
        allow_null=True,
        read_only=True,
    )

    incident_number = serializers.CharField(
        source="incident.incident_number",
        allow_null=True,
        read_only=True,
    )

    assigned_technician_email = serializers.EmailField(
        source="assigned_technician.email",
        allow_null=True,
        read_only=True,
    )
    assigned_technician_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "work_order_number",
            "work_type",
            "priority",
            "status",
            "title",
            "customer_number",
            "customer_name",
            "service_number",
            "network_node_name",
            "network_node_code",
            "complaint_number",
            "incident_number",
            "assigned_technician_email",
            "assigned_technician_name",
            "assigned_at",
            "dispatched_at",
            "onsite_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_customer_name(self, obj):
        if obj.customer is None:
            return None

        return (
            f"{obj.customer.first_name} "
            f"{obj.customer.last_name}"
        ).strip()

    def get_assigned_technician_name(self, obj):
        if obj.assigned_technician is None:
            return None

        return (
            f"{obj.assigned_technician.first_name} "
            f"{obj.assigned_technician.last_name}"
        ).strip()


class WorkOrderDetailSerializer(serializers.ModelSerializer):
    customer_id = serializers.UUIDField(
        source="customer.id",
        allow_null=True,
        read_only=True,
    )
    customer_number = serializers.CharField(
        source="customer.customer_number",
        allow_null=True,
        read_only=True,
    )
    customer_name = serializers.SerializerMethodField()

    service_account_id = serializers.UUIDField(
        source="service_account.id",
        allow_null=True,
        read_only=True,
    )
    service_number = serializers.CharField(
        source="service_account.service_number",
        allow_null=True,
        read_only=True,
    )
    service_status = serializers.CharField(
        source="service_account.status",
        allow_null=True,
        read_only=True,
    )

    network_node_id = serializers.UUIDField(
        source="network_node.id",
        allow_null=True,
        read_only=True,
    )
    network_node_name = serializers.CharField(
        source="network_node.name",
        allow_null=True,
        read_only=True,
    )
    network_node_code = serializers.CharField(
        source="network_node.code",
        allow_null=True,
        read_only=True,
    )

    complaint_id = serializers.UUIDField(
        source="complaint.id",
        allow_null=True,
        read_only=True,
    )
    complaint_number = serializers.CharField(
        source="complaint.complaint_number",
        allow_null=True,
        read_only=True,
    )

    incident_id = serializers.UUIDField(
        source="incident.id",
        allow_null=True,
        read_only=True,
    )
    incident_number = serializers.CharField(
        source="incident.incident_number",
        allow_null=True,
        read_only=True,
    )

    assigned_technician_id = serializers.UUIDField(
        source="assigned_technician.id",
        allow_null=True,
        read_only=True,
    )
    assigned_technician_email = serializers.EmailField(
        source="assigned_technician.email",
        allow_null=True,
        read_only=True,
    )
    assigned_technician_name = serializers.SerializerMethodField()

    created_by_email = serializers.EmailField(
        source="created_by.email",
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "work_order_number",
            "work_type",
            "priority",
            "status",
            "title",
            "description",
            "customer_id",
            "customer_number",
            "customer_name",
            "service_account_id",
            "service_number",
            "service_status",
            "network_node_id",
            "network_node_name",
            "network_node_code",
            "complaint_id",
            "complaint_number",
            "incident_id",
            "incident_number",
            "assigned_technician_id",
            "assigned_technician_email",
            "assigned_technician_name",
            "created_by_email",
            "dispatch_notes",
            "onsite_notes",
            "completion_notes",
            "assigned_at",
            "dispatched_at",
            "onsite_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_customer_name(self, obj):
        if obj.customer is None:
            return None

        return (
            f"{obj.customer.first_name} "
            f"{obj.customer.last_name}"
        ).strip()

    def get_assigned_technician_name(self, obj):
        if obj.assigned_technician is None:
            return None

        return (
            f"{obj.assigned_technician.first_name} "
            f"{obj.assigned_technician.last_name}"
        ).strip()