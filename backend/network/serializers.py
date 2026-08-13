from rest_framework import serializers

from network.models import (
    NetworkAssignment,
    NetworkNode,
    ProvisioningRequest,
)


class NetworkNodeSerializer(serializers.ModelSerializer):
    assignment_count = serializers.IntegerField(
        read_only=True,
        default=0,
    )

    class Meta:
        model = NetworkNode
        fields = [
            "id",
            "name",
            "code",
            "node_type",
            "management_ip",
            "location",
            "is_active",
            "assignment_count",
            "created_at",
            "updated_at",
        ]


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