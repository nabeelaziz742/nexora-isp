import uuid

from django.conf import settings
from django.db import models

from customers.models import Customer, ServiceAccount
from network.models import NetworkNode
from tenancy.base_models import TenantScopedModel


class Complaint(TenantScopedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        NEW = "NEW", "New"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        WAITING_CUSTOMER = "WAITING_CUSTOMER", "Waiting for Customer"
        WAITING_PARTS = "WAITING_PARTS", "Waiting for Parts"
        ESCALATED = "ESCALATED", "Escalated"
        RESOLVED = "RESOLVED", "Resolved"
        CUSTOMER_CONFIRMED = "CUSTOMER_CONFIRMED", "Customer Confirmed"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Category(models.TextChoices):
        CONNECTIVITY = "CONNECTIVITY", "Connectivity"
        SPEED = "SPEED", "Speed"
        BILLING = "BILLING", "Billing"
        DEVICE = "DEVICE", "Device"
        INSTALLATION = "INSTALLATION", "Installation"
        ROUTER_ISSUE = "ROUTER_ISSUE", "Router Issue"
        ONU_ISSUE = "ONU_ISSUE", "ONU / Optical Issue"
        FIBER_CABLE_DAMAGE = "FIBER_CABLE_DAMAGE", "Fiber / Cable Damage"
        POWER_ISSUE = "POWER_ISSUE", "Power / Adapter Issue"
        PAYMENT_RELATED = "PAYMENT_RELATED", "Payment Related"
        CONFIGURATION = "CONFIGURATION", "Configuration"
        OTHER = "OTHER", "Other"

    class Source(models.TextChoices):
        CUSTOMER_PORTAL = "CUSTOMER_PORTAL", "Customer Portal"
        PHONE = "PHONE", "Phone Call"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        SMS = "SMS", "SMS"
        WALK_IN = "WALK_IN", "Walk-in Desk"
        STAFF = "STAFF", "Staff Registered"
        SYSTEM = "SYSTEM", "System Automated"
        OTHER = "OTHER", "Other"

    class SLAStatus(models.TextChoices):
        ON_TRACK = "ON_TRACK", "On Track"
        DUE_SOON = "DUE_SOON", "Due Soon"
        BREACHED = "BREACHED", "SLA Breached"
        RESOLVED = "RESOLVED", "Resolved"

    class CustomerConfirmation(models.TextChoices):
        PENDING = "PENDING", "Pending Confirmation"
        CONFIRMED = "CONFIRMED", "Customer Confirmed"
        REJECTED = "REJECTED", "Reopened / Rejected by Customer"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    complaint_number = models.CharField(
        max_length=50,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="complaints",
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="complaints",
    )

    category = models.CharField(
        max_length=40,
        choices=Category.choices,
        default=Category.CONNECTIVITY,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    source = models.CharField(
        max_length=30,
        choices=Source.choices,
        default=Source.STAFF,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.OPEN,
    )

    subject = models.CharField(
        max_length=255,
    )

    description = models.TextField()

    # Assignment Tracking
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_support_complaints",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_by_support_complaints",
    )

    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reassignment_reason = models.TextField(
        blank=True,
    )

    # SLA Tracking
    first_response_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    response_due_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    resolution_due_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_response_sla_breached = models.BooleanField(
        default=False,
    )

    is_resolution_sla_breached = models.BooleanField(
        default=False,
    )

    sla_status = models.CharField(
        max_length=20,
        choices=SLAStatus.choices,
        default=SLAStatus.ON_TRACK,
    )

    # Escalation
    is_escalated = models.BooleanField(
        default=False,
    )

    escalation_level = models.PositiveSmallIntegerField(
        default=0,
    )

    escalation_reason = models.TextField(
        blank=True,
    )

    escalated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escalated_support_complaints",
    )

    escalated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    escalated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escalated_to_support_complaints",
    )

    # Diagnosis & Resolution
    diagnosis_category = models.CharField(
        max_length=100,
        blank=True,
    )

    resolution_summary = models.TextField(
        blank=True,
    )

    resolution_notes = models.TextField(
        blank=True,
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_support_complaints",
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Customer Confirmation & Closure
    customer_confirmation = models.CharField(
        max_length=20,
        choices=CustomerConfirmation.choices,
        default=CustomerConfirmation.PENDING,
    )

    customer_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    customer_feedback_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    customer_feedback_notes = models.TextField(
        blank=True,
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Linked Outage / Incident
    linked_incident = models.ForeignKey(
        "support.Incident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_complaints",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_support_complaints",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "support_complaint"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "complaint_number",
                ],
                name="unique_complaint_number_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="complaint_org_status_idx",
            ),
            models.Index(
                fields=["organization", "priority"],
                name="complaint_org_priority_idx",
            ),
            models.Index(
                fields=["organization", "assigned_to"],
                name="complaint_org_assigned_idx",
            ),
            models.Index(
                fields=["organization", "sla_status"],
                name="complaint_org_sla_idx",
            ),
            models.Index(
                fields=["organization", "customer"],
                name="complaint_org_customer_idx",
            ),
            models.Index(
                fields=["organization", "service_account"],
                name="complaint_org_service_idx",
            ),
        ]

    def __str__(self):
        return f"{self.complaint_number} - {self.subject}"


class ComplaintTimeline(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="timeline_events",
    )

    event_type = models.CharField(
        max_length=50,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaint_timeline_events",
    )

    previous_value = models.CharField(
        max_length=100,
        blank=True,
    )

    new_value = models.CharField(
        max_length=100,
        blank=True,
    )

    summary = models.CharField(
        max_length=255,
    )

    notes = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "support_complaint_timeline"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "complaint"],
                name="complaint_time_org_cmp_idx",
            ),
            models.Index(
                fields=["organization", "created_at"],
                name="complaint_time_org_dt_idx",
            ),
        ]

    def __str__(self):
        return f"{self.complaint.complaint_number} - {self.event_type} at {self.created_at}"


class ComplaintInternalNote(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="internal_notes_list",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaint_internal_notes",
    )

    note = models.TextField()

    is_internal = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "support_complaint_internal_note"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "complaint"],
                name="complaint_note_org_cmp_idx",
            ),
        ]

    def __str__(self):
        return f"Note on {self.complaint.complaint_number} by {self.author} at {self.created_at}"


class ComplaintSLAPolicy(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    priority = models.CharField(
        max_length=20,
        choices=Complaint.Priority.choices,
    )

    response_target_minutes = models.PositiveIntegerField(
        default=60,
    )

    resolution_target_hours = models.PositiveIntegerField(
        default=24,
    )

    escalation_threshold_hours = models.PositiveIntegerField(
        default=12,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "support_complaint_sla_policy"
        ordering = ["priority"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "priority"],
                name="unique_sla_policy_per_priority_org",
            ),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.priority} SLA"


class ComplaintAttachment(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="attachments_list",
    )

    file_name = models.CharField(
        max_length=255,
    )

    file_url = models.CharField(
        max_length=500,
    )

    file_size_bytes = models.PositiveIntegerField(
        default=0,
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_complaint_attachments",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "support_complaint_attachment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.complaint.complaint_number} - {self.file_name}"


class Incident(TenantScopedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        INVESTIGATING = "INVESTIGATING", "Investigating"
        IDENTIFIED = "IDENTIFIED", "Identified"
        MONITORING = "MONITORING", "Monitoring"
        RESOLVED = "RESOLVED", "Resolved"

    class Severity(models.TextChoices):
        MINOR = "MINOR", "Minor"
        MAJOR = "MAJOR", "Major"
        CRITICAL = "CRITICAL", "Critical"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    incident_number = models.CharField(
        max_length=50,
    )

    network_node = models.ForeignKey(
        NetworkNode,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incidents",
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField()

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MINOR,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.OPEN,
    )

    root_cause = models.TextField(
        blank=True,
    )

    resolution_notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_support_incidents",
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_support_incidents",
    )

    started_at = models.DateTimeField()

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "support_incident"
        ordering = ["-started_at", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "incident_number",
                ],
                name="unique_incident_number_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="incident_org_status_idx",
            ),
            models.Index(
                fields=["organization", "severity"],
                name="incident_org_severity_idx",
            ),
            models.Index(
                fields=["organization", "network_node"],
                name="incident_org_node_idx",
            ),
        ]

    def __str__(self):
        return f"{self.incident_number} - {self.title}"


class IncidentAffectedService(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="affected_services",
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.PROTECT,
        related_name="incident_impacts",
    )

    added_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "support_incident_affected_service"
        ordering = ["added_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "incident",
                    "service_account",
                ],
                name="unique_service_per_incident",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "incident"],
                name="incident_service_org_inc_idx",
            ),
            models.Index(
                fields=["organization", "service_account"],
                name="incident_service_org_srv_idx",
            ),
        ]

    def __str__(self):
        return f"{self.incident.incident_number} - {self.service_account.service_number}"