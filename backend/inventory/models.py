import uuid

from django.conf import settings
from django.db import models

from customers.models import ServiceAccount
from tenancy.base_models import TenantScopedModel


class InventoryDevice(TenantScopedModel):
    class DeviceType(models.TextChoices):
        ONU = "ONU", "ONU"
        ONT = "ONT", "ONT"
        ROUTER = "ROUTER", "Router"
        MODEM = "MODEM", "Modem"
        ACCESS_POINT = "ACCESS_POINT", "Access Point"
        SWITCH = "SWITCH", "Switch"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ASSIGNED = "ASSIGNED", "Assigned"
        FAULTY = "FAULTY", "Faulty"
        IN_REPAIR = "IN_REPAIR", "In Repair"
        RETIRED = "RETIRED", "Retired"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    asset_tag = models.CharField(
        max_length=100,
    )

    device_type = models.CharField(
        max_length=30,
        choices=DeviceType.choices,
    )

    manufacturer = models.CharField(
        max_length=150,
        blank=True,
    )

    model_name = models.CharField(
        max_length=150,
        blank=True,
    )

    serial_number = models.CharField(
        max_length=150,
        blank=True,
    )

    mac_address = models.CharField(
        max_length=50,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "inventory_device"
        ordering = ["asset_tag"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "asset_tag"],
                name="unique_device_asset_tag_per_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "serial_number"],
                condition=~models.Q(serial_number=""),
                name="unique_device_serial_per_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "mac_address"],
                condition=~models.Q(mac_address=""),
                name="unique_device_mac_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="device_org_status_idx",
            ),
            models.Index(
                fields=["organization", "device_type"],
                name="device_org_type_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.asset_tag} - "
            f"{self.device_type} - "
            f"{self.status}"
        )


class DeviceAssignment(TenantScopedModel):
    class ReturnCondition(models.TextChoices):
        GOOD = "GOOD", "Good"
        DAMAGED = "DAMAGED", "Damaged"
        FAULTY = "FAULTY", "Faulty"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    device = models.ForeignKey(
        InventoryDevice,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.PROTECT,
        related_name="device_assignments",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_device_assignments",
    )

    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_device_returns",
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    returned_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    return_condition = models.CharField(
        max_length=20,
        choices=ReturnCondition.choices,
        blank=True,
    )

    assignment_notes = models.TextField(
        blank=True,
    )

    return_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "inventory_device_assignment"
        ordering = ["-assigned_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["device"],
                condition=models.Q(returned_at__isnull=True),
                name="unique_active_assignment_per_device",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "service_account"],
                name="device_assign_org_service_idx",
            ),
            models.Index(
                fields=["organization", "device"],
                name="device_assign_org_device_idx",
            ),
            models.Index(
                fields=["organization", "returned_at"],
                name="device_assign_org_return_idx",
            ),
        ]

    @property
    def is_active(self):
        return self.returned_at is None

    def __str__(self):
        return (
            f"{self.device.asset_tag} -> "
            f"{self.service_account.service_number}"
        )