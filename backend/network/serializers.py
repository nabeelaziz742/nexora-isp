from rest_framework import serializers

from network.models import (
    NetworkAssignment,
    NetworkNode,
    PointOfPresence,
    ProvisioningRequest,
)


class PointOfPresenceSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source="area.name", read_only=True)
    area_city = serializers.CharField(source="area.city.name", read_only=True)
    supervisor_name = serializers.SerializerMethodField()
    nodes_count = serializers.IntegerField(read_only=True, default=0)
    active_subscribers_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = PointOfPresence
        fields = [
            "id",
            "code",
            "name",
            "pop_type",
            "area",
            "area_name",
            "area_city",
            "address",
            "latitude",
            "longitude",
            "rack_capacity_units",
            "power_backup_type",
            "status",
            "supervisor",
            "supervisor_name",
            "notes",
            "is_active",
            "nodes_count",
            "active_subscribers_count",
            "created_at",
            "updated_at",
        ]

    def get_supervisor_name(self, obj):
        if not obj.supervisor:
            return None
        full = f"{obj.supervisor.first_name} {obj.supervisor.last_name}".strip()
        return full or obj.supervisor.email


class NetworkNodeSerializer(serializers.ModelSerializer):
    assignment_count = serializers.IntegerField(
        read_only=True,
        default=0,
    )
    pop_site_name = serializers.CharField(
        source="pop_site.name",
        read_only=True,
    )
    pop_site_code = serializers.CharField(
        source="pop_site.code",
        read_only=True,
    )

    class Meta:
        model = NetworkNode
        fields = [
            "id",
            "name",
            "code",
            "node_type",
            "pop_site",
            "pop_site_name",
            "pop_site_code",
            "management_ip",
            "location",
            "is_active",
            "assignment_count",
            "created_at",
            "updated_at",
        ]


class PointOfPresenceDetailSerializer(PointOfPresenceSerializer):
    nodes = NetworkNodeSerializer(many=True, read_only=True)

    class Meta(PointOfPresenceSerializer.Meta):
        fields = PointOfPresenceSerializer.Meta.fields + ["nodes"]


class NetworkAssignmentSerializer(serializers.ModelSerializer):
    service_number = serializers.CharField(
        source="service_account.service_number",
        read_only=True,
    )
    service_status = serializers.CharField(
        source="service_account.status",
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
    network_node_name = serializers.CharField(
        source="network_node.name",
        read_only=True,
    )
    network_node_code = serializers.CharField(
        source="network_node.code",
        read_only=True,
    )

    class Meta:
        model = NetworkAssignment
        fields = [
            "id",
            "service_account",
            "service_number",
            "service_status",
            "customer_id",
            "customer_number",
            "customer_name",
            "network_node",
            "network_node_name",
            "network_node_code",
            "username",
            "ip_address",
            "is_active",
            "assigned_at",
            "updated_at",
        ]


class ProvisioningRequestSerializer(serializers.ModelSerializer):
    service_number = serializers.CharField(
        source="service_account.service_number",
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
    network_node_id = serializers.UUIDField(
        source="network_assignment.network_node_id",
        read_only=True,
    )
    network_node_name = serializers.CharField(
        source="network_assignment.network_node.name",
        read_only=True,
    )
    network_node_code = serializers.CharField(
        source="network_assignment.network_node.code",
        read_only=True,
    )

    class Meta:
        model = ProvisioningRequest
        fields = [
            "id",
            "service_account",
            "service_number",
            "customer_number",
            "customer_name",
            "network_assignment",
            "network_node_id",
            "network_node_name",
            "network_node_code",
            "action",
            "status",
            "idempotency_key",
            "requested_payload",
            "provider_reference",
            "error_message",
            "requested_at",
            "started_at",
            "completed_at",
            "updated_at",
        ]


class RequestPackageChangeSerializer(serializers.Serializer):
    internet_package_id = serializers.UUIDField()