from rest_framework import serializers

from support.models import (
    Complaint,
    ComplaintAttachment,
    ComplaintInternalNote,
    ComplaintSLAPolicy,
    ComplaintTimeline,
    Incident,
    IncidentAffectedService,
)


class ComplaintSLAPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintSLAPolicy
        fields = [
            "id",
            "priority",
            "response_target_minutes",
            "resolution_target_hours",
            "escalation_threshold_hours",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ComplaintTimelineSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(
        source="actor.email",
        read_only=True,
        allow_null=True,
    )
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ComplaintTimeline
        fields = [
            "id",
            "event_type",
            "actor_email",
            "actor_name",
            "previous_value",
            "new_value",
            "summary",
            "notes",
            "metadata",
            "created_at",
        ]

    def get_actor_name(self, obj):
        if not obj.actor:
            return "System / Unspecified"
        return f"{obj.actor.first_name} {obj.actor.last_name}".strip() or obj.actor.email


class ComplaintInternalNoteSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(
        source="author.email",
        read_only=True,
        allow_null=True,
    )
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ComplaintInternalNote
        fields = [
            "id",
            "author_email",
            "author_name",
            "note",
            "is_internal",
            "created_at",
        ]
        read_only_fields = ["id", "author_email", "author_name", "created_at"]

    def get_author_name(self, obj):
        if not obj.author:
            return "Staff"
        return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.email


class ComplaintAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ComplaintAttachment
        fields = [
            "id",
            "file_name",
            "file_url",
            "file_size_bytes",
            "mime_type",
            "uploaded_by_email",
            "created_at",
        ]


class ComplaintCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    service_account_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    category = serializers.ChoiceField(
        choices=Complaint.Category.choices,
        default=Complaint.Category.CONNECTIVITY,
    )
    priority = serializers.ChoiceField(
        choices=Complaint.Priority.choices,
        default=Complaint.Priority.MEDIUM,
    )
    source = serializers.ChoiceField(
        choices=Complaint.Source.choices,
        default=Complaint.Source.STAFF,
    )
    subject = serializers.CharField(
        max_length=255,
    )
    description = serializers.CharField()
    assigned_to_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    linked_incident_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )


class ComplaintAssignSerializer(serializers.Serializer):
    technician_id = serializers.UUIDField()
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ComplaintReassignSerializer(serializers.Serializer):
    technician_id = serializers.UUIDField()
    reason = serializers.CharField()
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ComplaintStatusTransitionSerializer(serializers.Serializer):
    target_status = serializers.ChoiceField(
        choices=Complaint.Status.choices,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    resolution_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ComplaintEscalateSerializer(serializers.Serializer):
    reason = serializers.CharField()
    escalated_to_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )


class ComplaintResolveSerializer(serializers.Serializer):
    diagnosis_category = serializers.CharField(
        max_length=100,
    )
    resolution_summary = serializers.CharField()
    resolution_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ComplaintCloseSerializer(serializers.Serializer):
    confirmation = serializers.ChoiceField(
        choices=Complaint.CustomerConfirmation.choices,
        default=Complaint.CustomerConfirmation.CONFIRMED,
    )
    feedback_rating = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=5,
    )
    feedback_notes = serializers.CharField(
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
    customer_phone = serializers.CharField(
        source="customer.phone",
        read_only=True,
    )
    customer_address = serializers.CharField(
        source="customer.address_line",
        read_only=True,
    )

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

    assigned_to_id = serializers.UUIDField(
        source="assigned_to.id",
        read_only=True,
        allow_null=True,
    )
    assigned_to_email = serializers.EmailField(
        source="assigned_to.email",
        read_only=True,
        allow_null=True,
    )
    assigned_to_name = serializers.SerializerMethodField()

    assigned_by_email = serializers.EmailField(
        source="assigned_by.email",
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
    escalated_by_email = serializers.EmailField(
        source="escalated_by.email",
        read_only=True,
        allow_null=True,
    )
    escalated_to_email = serializers.EmailField(
        source="escalated_to.email",
        read_only=True,
        allow_null=True,
    )

    linked_incident_id = serializers.UUIDField(
        source="linked_incident.id",
        read_only=True,
        allow_null=True,
    )
    linked_incident_number = serializers.CharField(
        source="linked_incident.incident_number",
        read_only=True,
        allow_null=True,
    )

    timeline_events = ComplaintTimelineSerializer(
        many=True,
        read_only=True,
    )
    internal_notes = ComplaintInternalNoteSerializer(
        source="internal_notes_list",
        many=True,
        read_only=True,
    )
    work_orders_count = serializers.SerializerMethodField()

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_number",
            "customer_id",
            "customer_number",
            "customer_name",
            "customer_phone",
            "customer_address",
            "service_account_id",
            "service_number",
            "category",
            "priority",
            "source",
            "status",
            "subject",
            "description",
            "assigned_to_id",
            "assigned_to_email",
            "assigned_to_name",
            "assigned_by_email",
            "assigned_at",
            "reassignment_reason",
            "first_response_at",
            "response_due_at",
            "resolution_due_at",
            "is_response_sla_breached",
            "is_resolution_sla_breached",
            "sla_status",
            "is_escalated",
            "escalation_level",
            "escalation_reason",
            "escalated_by_email",
            "escalated_at",
            "escalated_to_email",
            "diagnosis_category",
            "resolution_summary",
            "resolution_notes",
            "resolved_by_email",
            "resolved_at",
            "customer_confirmation",
            "customer_confirmed_at",
            "customer_feedback_rating",
            "customer_feedback_notes",
            "closed_at",
            "linked_incident_id",
            "linked_incident_number",
            "created_by_email",
            "created_at",
            "updated_at",
            "timeline_events",
            "internal_notes",
            "work_orders_count",
        ]

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}".strip()

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return None
        return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip() or obj.assigned_to.email

    def get_work_orders_count(self, obj):
        return getattr(obj, "work_orders", []).count() if hasattr(obj, "work_orders") else 0


# ==================== INCIDENT SERIALIZERS (PRESERVED) ====================

class IncidentAffectedServiceSerializer(serializers.ModelSerializer):
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
        return f"{customer.first_name} {customer.last_name}".strip()


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


class IncidentStatusTransitionSerializer(serializers.Serializer):
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

    affected_services = IncidentAffectedServiceSerializer(
        many=True,
        read_only=True,
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