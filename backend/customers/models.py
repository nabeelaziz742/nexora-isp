import uuid

from django.db import models

from tenancy.base_models import TenantScopedModel


class Customer(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    customer_number = models.CharField(
        max_length=50,
    )

    first_name = models.CharField(
        max_length=150,
    )

    last_name = models.CharField(
        max_length=150,
        blank=True,
    )

    phone = models.CharField(
        max_length=30,
    )

    alternate_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    address_line = models.CharField(
        max_length=255,
    )

    area = models.CharField(
        max_length=150,
        blank=True,
    )

    city = models.CharField(
        max_length=150,
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
        db_table = "customers_customer"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "customer_number"],
                name="unique_customer_number_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "phone"],
                name="customer_org_phone_idx",
            ),
            models.Index(
                fields=["organization", "is_active"],
                name="customer_org_active_idx",
            ),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return (
            f"{self.customer_number} - "
            f"{self.full_name}"
        )


class InternetPackage(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
    )

    code = models.CharField(
        max_length=50,
    )

    download_speed_mbps = models.PositiveIntegerField()

    upload_speed_mbps = models.PositiveIntegerField()

    monthly_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
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
        db_table = "customers_internet_package"
        ordering = ["monthly_price", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_package_code_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "is_active"],
                name="package_org_active_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.name} - "
            f"{self.download_speed_mbps} Mbps"
        )


class ServiceAccount(TenantScopedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        GRACE_PERIOD = "GRACE_PERIOD", "Grace Period"
        SUSPENSION_PENDING = (
            "SUSPENSION_PENDING",
            "Suspension Pending",
        )
        SUSPENDED_NON_PAYMENT = (
            "SUSPENDED_NON_PAYMENT",
            "Suspended Non-Payment",
        )
        RESTORE_PENDING = (
            "RESTORE_PENDING",
            "Restore Pending",
        )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    service_number = models.CharField(
        max_length=50,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="service_accounts",
    )

    internet_package = models.ForeignKey(
        InternetPackage,
        on_delete=models.PROTECT,
        related_name="service_accounts",
    )

    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    activated_at = models.DateTimeField(
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
        db_table = "customers_service_account"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "service_number"],
                name="unique_service_number_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="service_org_status_idx",
            ),
            models.Index(
                fields=["organization", "customer"],
                name="service_org_customer_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.service_number} - "
            f"{self.customer.full_name}"
        )


class BillingProfile(TenantScopedModel):
    class BillingCycle(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    service_account = models.OneToOneField(
        ServiceAccount,
        on_delete=models.CASCADE,
        related_name="billing_profile",
    )

    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
    )

    billing_day = models.PositiveSmallIntegerField()

    due_day = models.PositiveSmallIntegerField()

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
        db_table = "customers_billing_profile"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    billing_day__gte=1,
                    billing_day__lte=28,
                ),
                name="billing_day_between_1_and_28",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    due_day__gte=1,
                    due_day__lte=28,
                ),
                name="due_day_between_1_and_28",
            ),
        ]

    def __str__(self):
        return (
            f"{self.service_account.service_number} - "
            f"{self.billing_cycle}"
        )


class NotificationPreference(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )

    sms_enabled = models.BooleanField(
        default=True,
    )

    whatsapp_enabled = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_notification_preference"

    def __str__(self):
        return (
            f"{self.customer.customer_number} - "
            f"SMS={self.sms_enabled} - "
            f"WHATSAPP={self.whatsapp_enabled}"
        )