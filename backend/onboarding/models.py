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
