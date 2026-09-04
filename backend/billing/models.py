import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from customers.models import (
    BillingProfile,
    Customer,
    ServiceAccount,
)
from tenancy.base_models import TenantScopedModel


class Invoice(TenantScopedModel):
    class Status(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    invoice_number = models.CharField(
        max_length=100,
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.PROTECT,
        related_name="invoices",
    )

    billing_profile = models.ForeignKey(
        BillingProfile,
        on_delete=models.PROTECT,
        related_name="invoices",
    )

    billing_period_start = models.DateField()

    billing_period_end = models.DateField()

    issue_date = models.DateField()

    due_date = models.DateField()

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.UNPAID,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancellation_reason = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "billing_invoice"
        ordering = ["-issue_date", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "invoice_number",
                ],
                name="unique_invoice_number_per_org",
            ),
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "service_account",
                    "billing_period_start",
                    "billing_period_end",
                ],
                name="unique_service_billing_period",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    billing_period_end__gte=models.F(
                        "billing_period_start"
                    )
                ),
                name="invoice_period_end_gte_start",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    due_date__gte=models.F("issue_date")
                ),
                name="invoice_due_date_gte_issue",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="invoice_org_status_idx",
            ),
            models.Index(
                fields=[
                    "organization",
                    "service_account",
                ],
                name="invoice_org_service_idx",
            ),
            models.Index(
                fields=["organization", "due_date"],
                name="invoice_org_due_idx",
            ),
            models.Index(
                fields=[
                    "organization",
                    "service_account",
                    "billing_period_start",
                    "billing_period_end",
                ],
                name="inv_org_svc_period_idx",
            ),
        ]

    @property
    def total_amount(self):
        if hasattr(self, "annotated_total_amount") and self.annotated_total_amount is not None:
            return self.annotated_total_amount
        total = self.lines.aggregate(
            total=models.Sum("amount")
        )["total"]

        return total or Decimal("0.00")

    @property
    def paid_amount(self):
        if hasattr(self, "annotated_paid_amount") and self.annotated_paid_amount is not None:
            return self.annotated_paid_amount
        total = self.allocations.aggregate(
            total=models.Sum("amount")
        )["total"]

        return total or Decimal("0.00")

    @property
    def outstanding_amount(self):
        return self.total_amount - self.paid_amount

    def __str__(self):
        return (
            f"{self.invoice_number} - "
            f"{self.service_account.service_number}"
        )


class InvoiceLine(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="lines",
    )

    description = models.CharField(
        max_length=255,
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "billing_invoice_line"
        ordering = ["created_at"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="invoice_line_amount_gt_zero",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "invoice"],
                name="invoice_line_org_invoice_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.invoice.invoice_number} - "
            f"{self.description}"
        )


class Payment(TenantScopedModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        CARD = "CARD", "Card"
        MOBILE_WALLET = "MOBILE_WALLET", "Mobile Wallet"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    payment_number = models.CharField(
        max_length=100,
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=30,
        choices=Method.choices,
    )

    reference = models.CharField(
        max_length=150,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    is_reversed = models.BooleanField(
        default=False,
    )

    reversed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reversal_reason = models.TextField(
        blank=True,
    )

    reversal_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="billing_payments_received",
    )

    paid_at = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "billing_payment"
        ordering = ["-paid_at", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "payment_number",
                ],
                name="unique_payment_number_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="payment_amount_gt_zero",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "service_account",
                ],
                name="payment_org_service_idx",
            ),
            models.Index(
                fields=["organization", "paid_at"],
                name="payment_org_paid_idx",
            ),
        ]

    @property
    def allocated_amount(self):
        total = self.allocations.aggregate(
            total=models.Sum("amount")
        )["total"]

        return total or Decimal("0.00")

    @property
    def unallocated_amount(self):
        return self.amount - self.allocated_amount

    def __str__(self):
        return (
            f"{self.payment_number} - "
            f"{self.amount}"
        )


class PaymentAllocation(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="allocations",
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="allocations",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "billing_payment_allocation"
        ordering = ["created_at"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="payment_allocation_amount_gt_zero",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "payment"],
                name="allocation_org_payment_idx",
            ),
            models.Index(
                fields=["organization", "invoice"],
                name="allocation_org_invoice_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.payment.payment_number} -> "
            f"{self.invoice.invoice_number}"
        )


class PromiseToPay(TenantScopedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Approval"
        ACTIVE = "ACTIVE", "Active Promise"
        FULFILLED = "FULFILLED", "Fulfilled"
        BROKEN = "BROKEN", "Broken"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    promise_number = models.CharField(
        max_length=50,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="promises_to_pay",
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.PROTECT,
        related_name="promises_to_pay",
    )

    invoice = models.ForeignKey(
        Invoice,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="promises_to_pay",
    )

    outstanding_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    promised_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    promise_date = models.DateField()

    deadline = models.DateField()

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    notes = models.TextField(
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_promises",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_promises",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "billing_promise_to_pay"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "promise_number"],
                name="unique_promise_number_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(promised_amount__gt=0),
                name="ptp_promised_amount_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(deadline__gte=models.F("promise_date")),
                name="ptp_deadline_gte_promise_date",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="ptp_org_status_idx",
            ),
            models.Index(
                fields=["organization", "service_account"],
                name="ptp_org_service_idx",
            ),
            models.Index(
                fields=["organization", "deadline"],
                name="ptp_org_deadline_idx",
            ),
        ]

    def __str__(self):
        return f"{self.promise_number} - {self.customer.full_name} ({self.status})"


class RecoveryAllocation(TenantScopedModel):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        ALLOCATED = "ALLOCATED", "Allocated"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        CONTACTED = "CONTACTED", "Contacted"
        PROMISE_RECEIVED = "PROMISE_RECEIVED", "Promise Received"
        PAYMENT_COLLECTED = "PAYMENT_COLLECTED", "Payment Collected"
        NO_RESPONSE = "NO_RESPONSE", "No Response"
        FAILED = "FAILED", "Failed"
        ESCALATED = "ESCALATED", "Escalated"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    allocation_number = models.CharField(
        max_length=50,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="recovery_allocations",
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recovery_allocations",
    )

    invoice = models.ForeignKey(
        Invoice,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recovery_allocations",
    )

    outstanding_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assigned_recoveries",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_recoveries",
    )

    assigned_date = models.DateField(
        default=timezone.now,
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ALLOCATED,
    )

    notes = models.TextField(
        blank=True,
    )

    reassigned_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reassignments",
    )

    reassignment_reason = models.CharField(
        max_length=255,
        blank=True,
    )

    linked_promise = models.ForeignKey(
        PromiseToPay,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recovery_allocations",
    )

    completed_date = models.DateTimeField(
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
        db_table = "billing_recovery_allocation"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "allocation_number"],
                name="unique_allocation_number_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="rec_org_status_idx",
            ),
            models.Index(
                fields=["organization", "assigned_staff"],
                name="rec_org_staff_idx",
            ),
            models.Index(
                fields=["organization", "customer"],
                name="rec_org_customer_idx",
            ),
            models.Index(
                fields=["organization", "due_date"],
                name="rec_org_due_date_idx",
            ),
        ]

    def __str__(self):
        return f"{self.allocation_number} - {self.customer.full_name} ({self.status})"
