import uuid

from django.conf import settings
from django.db import models

from customers.models import Customer, ServiceAccount
from network.models import NetworkNode
from support.models import Complaint, Incident
from tenancy.base_models import TenantScopedModel


class WorkOrder(TenantScopedModel):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        ASSIGNED = "ASSIGNED", "Assigned"
        DISPATCHED = "DISPATCHED", "Dispatched"
        ONSITE = "ONSITE", "Onsite"
        COMPLETED = "COMPLETED", "Completed"
        SCHEDULED = "SCHEDULED", "Scheduled"
        STARTED = "STARTED", "Started"
        RESTORED = "RESTORED", "Restored"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class WorkType(models.TextChoices):
        INSTALLATION = "INSTALLATION", "Installation"
        REPAIR = "REPAIR", "Repair"
        DEVICE_REPLACEMENT = (
            "DEVICE_REPLACEMENT",
            "Device Replacement",
        )
        NETWORK_MAINTENANCE = (
            "NETWORK_MAINTENANCE",
            "Network Maintenance",
        )
        SITE_VISIT = "SITE_VISIT", "Site Visit"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    work_order_number = models.CharField(max_length=50)

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="work_orders",
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="work_orders",
    )

    network_node = models.ForeignKey(
        NetworkNode,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="work_orders",
    )

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="work_orders",
    )

    incident = models.ForeignKey(
        Incident,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="work_orders",
    )

    assigned_technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_work_orders",
    )

    work_type = models.CharField(max_length=40, choices=WorkType.choices)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.CREATED,
    )
    title = models.CharField(max_length=255)
    description = models.TextField()

    dispatch_notes = models.TextField(blank=True)
    onsite_notes = models.TextField(blank=True)
    completion_notes = models.TextField(blank=True)
    maintenance_notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_work_orders",
    )

    scheduled_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    onsite_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "field_operations_work_order"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "work_order_number"],
                name="unique_work_order_number_per_org",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="work_order_org_status_idx",
            ),
            models.Index(
                fields=["organization", "priority"],
                name="work_order_org_priority_idx",
            ),
            models.Index(
                fields=["organization", "assigned_technician"],
                name="work_order_org_tech_idx",
            ),
            models.Index(
                fields=["organization", "customer"],
                name="work_order_org_customer_idx",
            ),
            models.Index(
                fields=["organization", "service_account"],
                name="work_order_org_service_idx",
            ),
        ]

    def __str__(self):
        return f"{self.work_order_number} - {self.title}"
