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

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    address = models.CharField(
        max_length=255,
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


class StaffProfile(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        ACCOUNTANT = "ACCOUNTANT", "Accountant"
        OPERATOR = "OPERATOR", "Operator"
        RECOVERY_OFFICER = "RECOVERY_OFFICER", "Recovery Officer"
        TECHNICIAN = "TECHNICIAN", "Technician"
        SUPPORT_OFFICER = "SUPPORT_OFFICER", "Support Officer"
        FIELD_OFFICER = "FIELD_OFFICER", "Field Officer"
        STAFF = "STAFF", "Staff"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        SUSPENDED = "SUSPENDED", "Suspended"
        TERMINATED = "TERMINATED", "Terminated"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="staff_profiles",
    )

    membership = models.OneToOneField(
        OrganizationMembership,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profiles",
    )

    staff_code = models.CharField(
        max_length=50,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    alternate_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    cnic = models.CharField(
        max_length=30,
        blank=True,
    )

    department = models.CharField(
        max_length=100,
        blank=True,
    )

    designation = models.CharField(
        max_length=100,
        blank=True,
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.STAFF,
    )

    assigned_area = models.ForeignKey(
        "customers.Area",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_staff",
    )

    supervisor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subordinates",
    )

    joining_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE,
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
        db_table = "tenancy_staff_profile"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "staff_code"],
                name="unique_staff_code_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="staff_org_status_idx",
            ),
            models.Index(
                fields=["organization", "role"],
                name="staff_org_role_idx",
            ),
            models.Index(
                fields=["organization", "department"],
                name="staff_org_dept_idx",
            ),
        ]

    def __str__(self):
        return f"{self.staff_code} - {self.user.get_full_name() or self.user.email}"


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