import uuid

from django.conf import settings
from django.db import models

from customers.models import ServiceAccount
from tenancy.base_models import TenantScopedModel


class PointOfPresence(TenantScopedModel):
    class PopType(models.TextChoices):
        CORE = "CORE", "Core POP"
        AGGREGATION = "AGGREGATION", "Aggregation Node"
        DISTRIBUTION = "DISTRIBUTION", "Distribution Point / Cabinet"
        TOWER = "TOWER", "Wireless Tower Site"
        CABINET = "CABINET", "Street Cabinet / ODF"
        CENTRAL_OFFICE = "CENTRAL_OFFICE", "Central Office"
        OTHER = "OTHER", "Other Facility"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        MAINTENANCE = "MAINTENANCE", "Under Maintenance"
        DEGRADED = "DEGRADED", "Degraded Performance"
        OFFLINE = "OFFLINE", "Offline"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    code = models.CharField(
        max_length=50,
        help_text="Unique POP identifier per organization, e.g. POP-LHR-01",
    )
    name = models.CharField(
        max_length=150,
        help_text="Human-readable name, e.g. Gulberg Main Core POP",
    )
    pop_type = models.CharField(
        max_length=30,
        choices=PopType.choices,
        default=PopType.DISTRIBUTION,
    )
    area = models.ForeignKey(
        "customers.Area",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pop_sites",
    )
    address = models.TextField(
        blank=True,
        help_text="Physical street address or building details",
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    rack_capacity_units = models.PositiveIntegerField(
        default=42,
        help_text="Total rack units available at facility",
    )
    power_backup_type = models.CharField(
        max_length=100,
        blank=True,
        default="UPS_GENERATOR",
        help_text="e.g. SOLAR_HYBRID, UPS_GENERATOR, BATTERY_BANK, GRID_ONLY",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervised_pops",
    )
    notes = models.TextField(
        blank=True,
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
        db_table = "network_point_of_presence"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_pop_code_per_org",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="pop_org_status_idx",
            ),
            models.Index(
                fields=["organization", "pop_type"],
                name="pop_org_type_idx",
            ),
            models.Index(
                fields=["organization", "area"],
                name="pop_org_area_idx",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name} [{self.get_pop_type_display()}]"


class NetworkNode(TenantScopedModel):
    class NodeType(models.TextChoices):
        ROUTER = "ROUTER", "Router"
        OLT = "OLT", "OLT"
        SWITCH = "SWITCH", "Switch"
        ACCESS_POINT = "ACCESS_POINT", "Access Point"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)
    node_type = models.CharField(
        max_length=30,
        choices=NodeType.choices,
    )
    pop_site = models.ForeignKey(
        PointOfPresence,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="nodes",
    )
    management_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
    )
    location = models.CharField(
        max_length=255,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_network_node_code_per_org",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "is_active"],
                name="network_node_org_active_idx",
            ),
            models.Index(
                fields=["organization", "node_type"],
                name="network_node_org_type_idx",
            ),
            models.Index(
                fields=["organization", "pop_site"],
                name="network_node_org_pop_idx",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class NetworkAssignment(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    service_account = models.OneToOneField(
        ServiceAccount,
        on_delete=models.PROTECT,
        related_name="network_assignment",
    )
    network_node = models.ForeignKey(
        NetworkNode,
        on_delete=models.PROTECT,
        related_name="service_assignments",
    )
    username = models.CharField(
        max_length=150,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(
                fields=["organization", "is_active"],
                name="network_assign_org_active_idx",
            ),
            models.Index(
                fields=["organization", "network_node"],
                name="network_assign_org_node_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.service_account.service_number} "
            f"-> {self.network_node.code}"
        )


class ProvisioningRequest(TenantScopedModel):
    class Action(models.TextChoices):
        ACTIVATE = "ACTIVATE", "Activate"
        SUSPEND = "SUSPEND", "Suspend"
        RESTORE = "RESTORE", "Restore"
        CHANGE_PACKAGE = "CHANGE_PACKAGE", "Change Package"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.PROTECT,
        related_name="provisioning_requests",
    )
    network_assignment = models.ForeignKey(
        NetworkAssignment,
        on_delete=models.PROTECT,
        related_name="provisioning_requests",
    )
    action = models.CharField(
        max_length=30,
        choices=Action.choices,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )
    idempotency_key = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
    )
    requested_payload = models.JSONField(
        default=dict,
        blank=True,
    )
    provider_reference = models.CharField(
        max_length=255,
        blank=True,
    )
    error_message = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"],
                name="unique_provisioning_idempotency_per_org",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="provision_org_status_idx",
            ),
            models.Index(
                fields=["organization", "action"],
                name="provision_org_action_idx",
            ),
            models.Index(
                fields=["organization", "service_account"],
                name="provision_org_service_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.action} "
            f"{self.service_account.service_number} "
            f"[{self.status}]"
        )