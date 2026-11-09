import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class PaymentSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_name = models.CharField(max_length=150)
    account_title = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100)
    iban = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    instructions = models.TextField(blank=True)
    # Days an ISP may stay past its paid-until date before it is locked.
    subscription_grace_days = models.PositiveSmallIntegerField(default=7)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onboarding_payment_settings"


class ISPRegistration(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
        PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending Verification"
        ACTIVE = "ACTIVE", "Active"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    organization = models.OneToOneField("tenancy.Organization", on_delete=models.CASCADE, related_name="registration")
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="isp_registration")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_PAYMENT, db_index=True)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    receipt = models.ImageField(upload_to="payment_receipts/%Y/%m/", null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_isp_registrations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onboarding_isp_registration"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"], name="onboard_status_created_idx")]


class ISPSubscription(models.Model):
    """The platform subscription of one ISP (tenant): its fee and paid-until date."""

    class SuspensionKind(models.TextChoices):
        NONE = "", "Not suspended"
        MANUAL = "MANUAL", "Suspended by super admin"
        EXPIRED = "EXPIRED", "Subscription expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField("tenancy.Organization", on_delete=models.CASCADE, related_name="platform_subscription")
    monthly_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    # Null means no paid period is tracked yet, so the ISP is never auto-locked.
    paid_until = models.DateField(null=True, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    suspension_kind = models.CharField(max_length=20, choices=SuspensionKind.choices, blank=True, default="")
    suspension_reason = models.TextField(blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onboarding_isp_subscription"


class ISPSubscriptionPayment(models.Model):
    """A subscription fee an ISP paid to the platform, extending its paid-until date."""

    class Method(models.TextChoices):
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        MOBILE_WALLET = "MOBILE_WALLET", "Mobile Wallet"
        CASH = "CASH", "Cash"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.CASCADE, related_name="platform_payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    months = models.PositiveSmallIntegerField(default=1)
    period_start = models.DateField()
    period_end = models.DateField()
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.BANK_TRANSFER)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "onboarding_isp_subscription_payment"
        ordering = ["-created_at"]
