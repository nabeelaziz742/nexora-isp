import uuid

from django.conf import settings
from django.db import models


class Organization(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=255,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    city = models.CharField(
        max_length=150,
        blank=True,
    )

    timezone = models.CharField(
        max_length=100,
        default="UTC",
    )

    currency = models.CharField(
        max_length=10,
        default="PKR",
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
        db_table = "tenancy_organization"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        STAFF = "STAFF", "Staff"
        TECHNICIAN = "TECHNICIAN", "Technician"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
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
        db_table = "tenancy_organization_membership"
        ordering = ["organization", "user"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_user_organization_membership",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "role"],
                name="membership_org_role_idx",
            ),
            models.Index(
                fields=["user", "is_active"],
                name="membership_user_active_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.organization.code} - "
            f"{self.role}"
        )


class AuditLog(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=100,
    )

    resource_type = models.CharField(
        max_length=100,
    )

    resource_id = models.CharField(
        max_length=255,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = "tenancy_audit_log"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "action",
                    "created_at",
                ],
                name="audit_org_action_idx",
            ),
            models.Index(
                fields=[
                    "organization",
                    "resource_type",
                    "resource_id",
                ],
                name="audit_org_resource_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.organization.code} | "
            f"{self.action} | "
            f"{self.resource_type}"
        )