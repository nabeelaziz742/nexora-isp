import uuid

from django.conf import settings
from django.db import models

from customers.models import Customer, ServiceAccount
from network.models import NetworkNode
from tenancy.base_models import TenantScopedModel


class Complaint(TenantScopedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

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
        OTHER = "OTHER", "Other"

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
        max_length=30,
        choices=Category.choices,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
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

    resolution_notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_support_complaints",
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_support_complaints",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
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
                fields=["organization", "customer"],
                name="complaint_org_customer_idx",
            ),
            models.Index(
                fields=["organization", "service_account"],
                name="complaint_org_service_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.complaint_number} - "
            f"{self.subject}"
        )


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
        return (
            f"{self.incident_number} - "
            f"{self.title}"
        )


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
        return (
            f"{self.incident.incident_number} - "
            f"{self.service_account.service_number}"
        )