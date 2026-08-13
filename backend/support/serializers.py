from rest_framework import serializers

from support.models import (
    Complaint,
    Incident,
    IncidentAffectedService,
)


class ComplaintCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    service_account_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    category = serializers.ChoiceField(
        choices=Complaint.Category.choices,
    )
    priority = serializers.ChoiceField(
        choices=Complaint.Priority.choices,
    )
    subject = serializers.CharField(
        max_length=255,
    )
    description = serializers.CharField()


class ComplaintStatusTransitionSerializer(
    serializers.Serializer
):
    target_status = serializers.ChoiceField(
        choices=Complaint.Status.choices,
    )
    resolution_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ComplaintSerializer(serializers.ModelSerializer):
    customer_id = serializers.UUIDField(
        source="customer.id",
        read_only=True,
    )
    customer_number = serializers.CharField(
        source="customer.customer_number",
        read_only=True,
    )
    customer_name = serializers.SerializerMethodField()

    service_account_id = serializers.UUIDField(
        source="service_account.id",
        read_only=True,
        allow_null=True,
    )
    service_number = serializers.CharField(
        source="service_account.service_number",
        read_only=True,
        allow_null=True,
    )

    created_by_email = serializers.EmailField(
        source="created_by.email",
        read_only=True,
        allow_null=True,
    )
    resolved_by_email = serializers.EmailField(
        source="resolved_by.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_number",
            "customer_id",
            "customer_number",
            "customer_name",
            "service_account_id",
            "service_number",
            "category",
            "priority",
            "status",
            "subject",
            "description",
            "resolution_notes",
            "created_by_email",
            "resolved_by_email",
            "created_at",
            "updated_at",
            "resolved_at",
            "closed_at",
        ]

    def get_customer_name(self, obj):
        return (
            f"{obj.customer.first_name} "
            f"{obj.customer.last_name}"
        ).strip()


class IncidentAffectedServiceSerializer(
    serializers.ModelSerializer
):
    service_account_id = serializers.UUIDField(
        source="service_account.id",
        read_only=True,
    )
    service_number = serializers.CharField(
        source="service_account.service_number",
        read_only=True,
    )
    service_status = serializers.CharField(
        source="service_account.status",
        read_only=True,
    )
    customer_id = serializers.UUIDField(
        source="service_account.customer.id",
        read_only=True,
    )
    customer_number = serializers.CharField(
        source="service_account.customer.customer_number",
        read_only=True,
    )
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = IncidentAffectedService
        fields = [
            "service_account_id",
            "service_number",
            "service_status",
            "customer_id",
            "customer_number",
            "customer_name",
            "added_at",
        ]

    def get_customer_name(self, obj):
        customer = obj.service_account.customer

        return (
            f"{customer.first_name} "
            f"{customer.last_name}"
        ).strip()


class IncidentCreateSerializer(serializers.Serializer):
    title = serializers.CharField(
        max_length=255,
    )
    description = serializers.CharField()
    severity = serializers.ChoiceField(
        choices=Incident.Severity.choices,
    )
    started_at = serializers.DateTimeField()
    network_node_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    affected_service_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )


class IncidentStatusTransitionSerializer(
    serializers.Serializer
):
    target_status = serializers.ChoiceField(
        choices=Incident.Status.choices,
    )
    root_cause = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    resolution_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class IncidentSerializer(serializers.ModelSerializer):
    network_node_id = serializers.UUIDField(
        source="network_node.id",
        read_only=True,
        allow_null=True,
    )
    network_node_name = serializers.CharField(
        source="network_node.name",
        read_only=True,
        allow_null=True,
    )
    network_node_code = serializers.CharField(
        source="network_node.code",
        read_only=True,
        allow_null=True,
    )

    created_by_email = serializers.EmailField(
        source="created_by.email",
        read_only=True,
        allow_null=True,
    )
    resolved_by_email = serializers.EmailField(
        source="resolved_by.email",
        read_only=True,
        allow_null=True,
    )

    affected_services = (
        IncidentAffectedServiceSerializer(
            many=True,
            read_only=True,
        )
    )

    class Meta:
        model = Incident
        fields = [
            "id",
            "incident_number",
            "network_node_id",
            "network_node_name",
            "network_node_code",
            "title",
            "description",
            "severity",
            "status",
            "root_cause",
            "resolution_notes",
            "created_by_email",
            "resolved_by_email",
            "started_at",
            "resolved_at",
            "created_at",
            "updated_at",
            "affected_services",
        ]