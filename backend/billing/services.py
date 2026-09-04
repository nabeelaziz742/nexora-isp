import calendar
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

from communications.models import CommunicationAutomation
from communications.automation_service import CommunicationAutomationService

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
    PromiseToPay,
)
from billing.automation import (
    process_fully_paid_invoice_lifecycle,
    queue_invoice_generated_notification,
)
from customers.models import (
    BillingProfile,
    ServiceAccount,
)
from tenancy.models import Organization
from tenancy.services import record_audit_log


User = get_user_model()


class BillingDomainError(Exception):
    pass


@dataclass(frozen=True)
class InvoiceGenerationResult:
    invoice: Invoice
    invoice_line: InvoiceLine


@dataclass(frozen=True)
class PaymentRecordingResult:
    payment: Payment
    allocation: PaymentAllocation
    invoice: Invoice


@dataclass(frozen=True)
class MonthlyBillingGenerationResult:
    organization: Organization
    billing_year: int
    billing_month: int
    eligible_services: int
    generated_invoices: int
    skipped_existing_invoices: int
    failed_services: int


def _lock_organization_for_numbering(
    *,
    organization: Organization,
) -> Organization:
    """Serialize tenant-local number allocation inside the transaction."""
    return (
        Organization.objects
        .select_for_update()
        .get(id=organization.id)
    )


def _build_invoice_number(
    *,
    organization: Organization,
) -> str:
    prefix = organization.code.upper()[:12]

    sequence = (
        Invoice.objects
        .for_organization(organization)
        .count()
        + 1
    )

    return f"{prefix}-INV-{sequence:06d}"


def _build_payment_number(
    *,
    organization: Organization,
) -> str:
    prefix = organization.code.upper()[:12]

    sequence = (
        Payment.objects
        .for_organization(organization)
        .count()
        + 1
    )

    return f"{prefix}-PAY-{sequence:06d}"


def _normalize_amount(
    *,
    amount,
    error_message: str,
) -> Decimal:
    try:
        normalized_amount = Decimal(str(amount))
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise BillingDomainError(error_message) from exc

    if normalized_amount <= Decimal("0.00"):
        raise BillingDomainError(error_message)

    return normalized_amount.quantize(Decimal("0.01"))


def _refresh_invoice_status(*, invoice: Invoice) -> Invoice:
    if invoice.status == Invoice.Status.CANCELLED:
        return invoice

    total_amount = invoice.total_amount
    paid_amount = invoice.paid_amount

    if paid_amount <= Decimal("0.00"):
        status = Invoice.Status.UNPAID
    elif paid_amount < total_amount:
        status = Invoice.Status.PARTIALLY_PAID
    else:
        status = Invoice.Status.PAID

    if invoice.status != status:
        invoice.status = status
        invoice.save(update_fields=["status", "updated_at"])

    return invoice


def _get_month_period(*, billing_year: int, billing_month: int) -> tuple[date, date]:
    if billing_year < 2000:
        raise BillingDomainError("Billing year is invalid.")

    if billing_month < 1 or billing_month > 12:
        raise BillingDomainError("Billing month must be between 1 and 12.")

    last_day = calendar.monthrange(billing_year, billing_month)[1]

    return (
        date(billing_year, billing_month, 1),
        date(billing_year, billing_month, last_day),
    )


def _resolve_billing_dates(*, billing_profile: BillingProfile, billing_year: int, billing_month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(billing_year, billing_month)[1]

    issue_day = min(billing_profile.billing_day, last_day)
    due_day = min(billing_profile.due_day, last_day)

    issue_date = date(billing_year, billing_month, issue_day)
    due_date = date(billing_year, billing_month, due_day)

    if due_date < issue_date:
        raise BillingDomainError(
            "Billing profile due day cannot produce a due date before the invoice issue date."
        )

    return issue_date, due_date


@transaction.atomic
def generate_service_invoice(
    *,
    organization: Organization,
    actor: User | None,
    service_account_id,
    billing_period_start: date,
    billing_period_end: date,
    issue_date: date,
    due_date: date,
) -> InvoiceGenerationResult:
    if not organization.is_active:
        raise BillingDomainError("Organization is inactive.")

    organization = _lock_organization_for_numbering(organization=organization)

    if billing_period_end < billing_period_start:
        raise BillingDomainError("Billing period end cannot be before billing period start.")

    if due_date < issue_date:
        raise BillingDomainError("Invoice due date cannot be before issue date.")

    try:
        service_account = (
            ServiceAccount.objects
            .select_for_update()
            .select_related("internet_package")
            .for_organization(organization)
            .get(id=service_account_id)
        )
    except ServiceAccount.DoesNotExist as exc:
        raise BillingDomainError(
            "Service account was not found for this organization."
        ) from exc

    try:
        billing_profile = service_account.billing_profile
    except ServiceAccount.billing_profile.RelatedObjectDoesNotExist as exc:
        raise BillingDomainError(
            "Active billing profile was not found for this service account."
        ) from exc

    if not billing_profile.is_active:
        raise BillingDomainError("Billing profile is inactive.")

    duplicate_invoice_exists = (
        Invoice.objects
        .for_organization(organization)
        .filter(
            service_account=service_account,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
        )
        .exists()
    )

    if duplicate_invoice_exists:
        raise BillingDomainError(
            "Invoice already exists for this service and billing period."
        )

    package_price = _normalize_amount(
        amount=service_account.internet_package.monthly_price,
        error_message="Internet package monthly price must be greater than zero.",
    )

    invoice = Invoice.objects.create(
        organization=organization,
        invoice_number=_build_invoice_number(organization=organization),
        service_account=service_account,
        billing_profile=billing_profile,
        billing_period_start=billing_period_start,
        billing_period_end=billing_period_end,
        issue_date=issue_date,
        due_date=due_date,
        status=Invoice.Status.UNPAID,
    )

    invoice_line = InvoiceLine.objects.create(
        organization=organization,
        invoice=invoice,
        description=(
            f"{service_account.internet_package.name} monthly internet service"
        ),
        amount=package_price,
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="BILLING_INVOICE_GENERATED",
        resource_type="Invoice",
        resource_id=invoice.id,
        metadata={
            "invoice_number": invoice.invoice_number,
            "service_account_id": str(service_account.id),
            "service_number": service_account.service_number,
            "billing_period_start": billing_period_start.isoformat(),
            "billing_period_end": billing_period_end.isoformat(),
            "total_amount": str(invoice.total_amount),
        },
    )

    queue_invoice_generated_notification(
        organization=organization,
        invoice=invoice,
        actor=actor,
    )

    CommunicationAutomationService.execute_trigger(
        organization=organization,
        trigger=CommunicationAutomation.Trigger.INVOICE_GENERATED,
        customer=service_account.customer,
        invoice=invoice,
    )

    try:
        from accounting.services import post_invoice_journal_entry
        post_invoice_journal_entry(invoice=invoice, actor=actor)
    except Exception as exc:
        logger.exception("Error in accounting invoice hook for %s: %s", invoice.invoice_number, exc)

    return InvoiceGenerationResult(invoice=invoice, invoice_line=invoice_line)


def generate_monthly_invoices(
    *,
    organization: Organization,
    actor: User | None,
    billing_year: int,
    billing_month: int,
) -> MonthlyBillingGenerationResult:
    if not organization.is_active:
        raise BillingDomainError("Organization is inactive.")

    billing_period_start, billing_period_end = _get_month_period(
        billing_year=billing_year,
        billing_month=billing_month,
    )

    billing_profiles = (
        BillingProfile.objects
        .for_organization(organization)
        .filter(
            is_active=True,
            service_account__status__in=["ACTIVE", "GRACE_PERIOD"],
        )
        .filter(
            Q(service_account__activated_at__isnull=True)
            | Q(service_account__activated_at__date__lte=billing_period_end)
        )
        .select_related("service_account", "service_account__internet_package")
        .order_by("service_account__service_number")
    )

    eligible_services = billing_profiles.count()
    generated_invoices = 0
    skipped_existing_invoices = 0
    failed_services = 0

    for billing_profile in billing_profiles:
        service_account = billing_profile.service_account

        invoice_exists = (
            Invoice.objects
            .for_organization(organization)
            .filter(
                service_account=service_account,
                billing_period_start=billing_period_start,
                billing_period_end=billing_period_end,
            )
            .exists()
        )

        if invoice_exists:
            skipped_existing_invoices += 1
            continue

        try:
            issue_date, due_date = _resolve_billing_dates(
                billing_profile=billing_profile,
                billing_year=billing_year,
                billing_month=billing_month,
            )

            generate_service_invoice(
                organization=organization,
                actor=actor,
                service_account_id=service_account.id,
                billing_period_start=billing_period_start,
                billing_period_end=billing_period_end,
                issue_date=issue_date,
                due_date=due_date,
            )
        except BillingDomainError:
            failed_services += 1
            continue

        generated_invoices += 1

    record_audit_log(
        organization=organization,
        actor=actor,
        action="BILLING_MONTHLY_GENERATION_COMPLETED",
        resource_type="Organization",
        resource_id=organization.id,
        metadata={
            "billing_year": billing_year,
            "billing_month": billing_month,
            "eligible_services": eligible_services,
            "generated_invoices": generated_invoices,
            "skipped_existing_invoices": skipped_existing_invoices,
            "failed_services": failed_services,
        },
    )

    return MonthlyBillingGenerationResult(
        organization=organization,
        billing_year=billing_year,
        billing_month=billing_month,
        eligible_services=eligible_services,
        generated_invoices=generated_invoices,
        skipped_existing_invoices=skipped_existing_invoices,
        failed_services=failed_services,
    )


@transaction.atomic
def record_invoice_payment(
    *,
    organization: Organization,
    actor: User,
    invoice_id,
    amount,
    payment_method: str,
    reference: str = "",
    notes: str = "",
    paid_at=None,
) -> PaymentRecordingResult:
    if not organization.is_active:
        raise BillingDomainError("Organization is inactive.")

    organization = _lock_organization_for_numbering(organization=organization)

    normalized_amount = _normalize_amount(
        amount=amount,
        error_message="Payment amount must be greater than zero.",
    )

    valid_payment_methods = {choice for choice, _ in Payment.Method.choices}

    if payment_method not in valid_payment_methods:
        raise BillingDomainError("Invalid payment method.")

    try:
        invoice = (
            Invoice.objects
            .select_for_update()
            .select_related("service_account")
            .for_organization(organization)
            .get(id=invoice_id)
        )
    except Invoice.DoesNotExist as exc:
        raise BillingDomainError(
            "Invoice was not found for this organization."
        ) from exc

    outstanding_amount = invoice.outstanding_amount

    if outstanding_amount <= Decimal("0.00"):
        raise BillingDomainError("Invoice is already fully paid.")

    if normalized_amount > outstanding_amount:
        raise BillingDomainError(
            "Payment amount cannot exceed invoice outstanding amount."
        )

    previous_status = invoice.status

    payment = Payment.objects.create(
        organization=organization,
        payment_number=_build_payment_number(organization=organization),
        service_account=invoice.service_account,
        amount=normalized_amount,
        payment_method=payment_method,
        reference=reference.strip(),
        notes=notes.strip(),
        received_by=actor,
        paid_at=paid_at or timezone.now(),
    )

    allocation = PaymentAllocation.objects.create(
        organization=organization,
        payment=payment,
        invoice=invoice,
        amount=normalized_amount,
    )

    invoice = _refresh_invoice_status(invoice=invoice)

    record_audit_log(
        organization=organization,
        actor=actor,
        action="BILLING_PAYMENT_RECORDED",
        resource_type="Payment",
        resource_id=payment.id,
        metadata={
            "payment_number": payment.payment_number,
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "service_account_id": str(invoice.service_account_id),
            "service_number": invoice.service_account.service_number,
            "payment_amount": str(normalized_amount),
            "invoice_status": invoice.status,
            "invoice_outstanding_amount": str(invoice.outstanding_amount),
        },
    )

    if previous_status != Invoice.Status.PAID and invoice.status == Invoice.Status.PAID:
        record_audit_log(
            organization=organization,
            actor=actor,
            action="BILLING_INVOICE_FULLY_PAID",
            resource_type="Invoice",
            resource_id=invoice.id,
            metadata={
                "invoice_number": invoice.invoice_number,
                "payment_id": str(payment.id),
                "payment_number": payment.payment_number,
                "total_amount": str(invoice.total_amount),
                "paid_amount": str(invoice.paid_amount),
                "outstanding_amount": str(invoice.outstanding_amount),
            },
        )

        process_fully_paid_invoice_lifecycle(
            organization=organization,
            invoice=invoice,
            actor=actor,
        )

    try:
        from accounting.services import post_payment_journal_entry
        post_payment_journal_entry(payment=payment, actor=actor)
    except Exception as exc:
        logger.exception("Error in accounting payment hook for %s: %s", payment.payment_number, exc)

    return PaymentRecordingResult(
        payment=payment,
        allocation=allocation,
        invoice=invoice,
    )


def generate_promise_number(*, organization: Organization) -> str:
    prefix = organization.code.upper()[:12]
    sequence = PromiseToPay.objects.for_organization(organization).count() + 1
    return f"{prefix}-PTP-{sequence:05d}"


@transaction.atomic
def create_promise_to_pay(
    *,
    organization: Organization,
    actor: User,
    customer_id,
    service_account_id,
    promised_amount: Decimal | str | float | int,
    promise_date: date,
    deadline: date,
    invoice_id=None,
    notes: str = "",
    status: str = PromiseToPay.Status.PENDING,
) -> PromiseToPay:
    if not organization.is_active:
        raise BillingDomainError("Organization is inactive.")

    try:
        service_account = (
            ServiceAccount.objects.for_organization(organization)
            .select_related("customer")
            .get(id=service_account_id, customer_id=customer_id)
        )
    except ServiceAccount.DoesNotExist as exc:
        raise BillingDomainError("Service account not found for this customer.") from exc

    try:
        normalized_amount = Decimal(str(promised_amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError) as exc:
        raise BillingDomainError("Promised amount must be a valid positive decimal number.") from exc

    if normalized_amount <= Decimal("0.00"):
        raise BillingDomainError("Promised amount must be greater than zero.")

    if deadline < promise_date:
        raise BillingDomainError("Promise deadline cannot be earlier than the promise date.")

    # Prevent duplicate active/pending promises on this service account
    active_promise_exists = (
        PromiseToPay.objects.for_organization(organization)
        .filter(
            service_account=service_account,
            status__in=[PromiseToPay.Status.PENDING, PromiseToPay.Status.ACTIVE],
        )
        .exists()
    )

    if active_promise_exists:
        raise BillingDomainError(
            "An active or pending promise to pay already exists for this service account."
        )

    invoice = None
    if invoice_id:
        try:
            invoice = (
                Invoice.objects.for_organization(organization)
                .get(id=invoice_id, service_account=service_account)
            )
        except Invoice.DoesNotExist as exc:
            raise BillingDomainError("Specified invoice not found for this service account.") from exc

    # Compute current outstanding amount
    if invoice:
        outstanding = invoice.outstanding_amount
    else:
        # Sum all unpaid / partially paid invoices
        unpaid_invoices = Invoice.objects.for_organization(organization).filter(
            service_account=service_account,
            status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID],
        )
        outstanding = sum((inv.outstanding_amount for inv in unpaid_invoices), Decimal("0.00"))

    promise = PromiseToPay.objects.create(
        organization=organization,
        promise_number=generate_promise_number(organization=organization),
        customer=service_account.customer,
        service_account=service_account,
        invoice=invoice,
        outstanding_amount=outstanding,
        promised_amount=normalized_amount,
        promise_date=promise_date,
        deadline=deadline,
        status=status,
        notes=notes.strip(),
        created_by=actor,
        approved_by=actor if status == PromiseToPay.Status.ACTIVE else None,
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="PROMISE_TO_PAY_CREATED",
        resource_type="PromiseToPay",
        resource_id=str(promise.id),
        metadata={
            "promise_number": promise.promise_number,
            "customer_id": str(promise.customer_id),
            "service_account_id": str(promise.service_account_id),
            "promised_amount": str(promise.promised_amount),
            "deadline": str(promise.deadline),
            "status": promise.status,
        },
    )

    return promise


@transaction.atomic
def transition_promise_status(
    *,
    promise_id,
    organization: Organization,
    actor: User,
    new_status: str,
    failure_reason: str = "",
    notes: str = "",
) -> PromiseToPay:
    try:
        promise = (
            PromiseToPay.objects.for_organization(organization)
            .select_for_update()
            .get(id=promise_id)
        )
    except PromiseToPay.DoesNotExist as exc:
        raise BillingDomainError("Promise to pay not found.") from exc

    terminal_statuses = [
        PromiseToPay.Status.FULFILLED,
        PromiseToPay.Status.BROKEN,
        PromiseToPay.Status.EXPIRED,
        PromiseToPay.Status.CANCELLED,
    ]

    if promise.status in terminal_statuses:
        raise BillingDomainError(
            f"Cannot change status of a completed promise (current status: {promise.status})."
        )

    valid_transitions = {
        PromiseToPay.Status.PENDING: [
            PromiseToPay.Status.ACTIVE,
            PromiseToPay.Status.CANCELLED,
        ],
        PromiseToPay.Status.ACTIVE: [
            PromiseToPay.Status.FULFILLED,
            PromiseToPay.Status.BROKEN,
            PromiseToPay.Status.EXPIRED,
            PromiseToPay.Status.CANCELLED,
        ],
    }

    allowed = valid_transitions.get(promise.status, [])
    if new_status not in allowed:
        raise BillingDomainError(
            f"Invalid transition from {promise.status} to {new_status}."
        )

    # If fulfilling, verify that actual payments exist
    if new_status == PromiseToPay.Status.FULFILLED:
        # Check actual payment history since promise creation
        if promise.invoice:
            # Invoice is fully paid OR has payments made on/after promise_date totaling >= promised_amount
            paid_since = PaymentAllocation.objects.for_organization(organization).filter(
                invoice=promise.invoice,
                payment__paid_at__date__gte=promise.promise_date,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

            if promise.invoice.outstanding_amount > 0 and paid_since < promise.promised_amount:
                raise BillingDomainError(
                    f"Promise cannot be fulfilled: Invoice still has outstanding balance of {promise.invoice.outstanding_amount} "
                    f"and recorded payments since promise ({paid_since}) are less than promised amount ({promise.promised_amount})."
                )
        else:
            # Check payments on service account
            paid_since = Payment.objects.for_organization(organization).filter(
                service_account=promise.service_account,
                paid_at__date__gte=promise.promise_date,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

            if paid_since < promise.promised_amount:
                raise BillingDomainError(
                    f"Promise cannot be fulfilled: Recorded payments ({paid_since}) are less than promised amount ({promise.promised_amount})."
                )

    old_status = promise.status
    promise.status = new_status
    if failure_reason.strip():
        promise.failure_reason = failure_reason.strip()
    if notes.strip():
        promise.notes = f"{promise.notes}\n{notes}".strip() if promise.notes else notes.strip()

    if new_status in terminal_statuses:
        promise.completed_at = timezone.now()

    if new_status == PromiseToPay.Status.ACTIVE and not promise.approved_by:
        promise.approved_by = actor

    promise.save(
        update_fields=[
            "status",
            "failure_reason",
            "notes",
            "completed_at",
            "approved_by",
            "updated_at",
        ]
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="PROMISE_TO_PAY_STATUS_UPDATED",
        resource_type="PromiseToPay",
        resource_id=str(promise.id),
        metadata={
            "promise_number": promise.promise_number,
            "old_status": old_status,
            "new_status": new_status,
            "failure_reason": promise.failure_reason,
        },
    )

    return promise


@transaction.atomic
def cancel_invoice(
    *,
    organization: Organization,
    actor: User,
    invoice_id,
    cancellation_reason: str,
) -> Invoice:
    if not organization.is_active:
        raise BillingDomainError("Organization is inactive.")

    if not cancellation_reason or not cancellation_reason.strip():
        raise BillingDomainError("Cancellation reason is mandatory.")

    try:
        invoice = (
            Invoice.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=invoice_id)
        )
    except Invoice.DoesNotExist as exc:
        raise BillingDomainError("Invoice was not found for this organization.") from exc

    if invoice.status == Invoice.Status.CANCELLED:
        raise BillingDomainError("Invoice is already cancelled.")

    if invoice.allocations.exists():
        raise BillingDomainError("Cannot cancel invoice with recorded payments. Reverse payments first.")

    invoice.status = Invoice.Status.CANCELLED
    invoice.cancelled_at = timezone.now()
    invoice.cancellation_reason = cancellation_reason.strip()
    invoice.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="BILLING_INVOICE_CANCELLED",
        resource_type="Invoice",
        resource_id=invoice.id,
        metadata={
            "invoice_number": invoice.invoice_number,
            "cancellation_reason": invoice.cancellation_reason,
            "total_amount": str(invoice.total_amount),
        },
    )

    try:
        from accounting.services import post_invoice_cancellation_journal_entry
        post_invoice_cancellation_journal_entry(invoice=invoice, actor=actor)
    except Exception as exc:
        logger.exception("Error in accounting invoice cancellation hook for %s: %s", invoice.invoice_number, exc)

    return invoice


@transaction.atomic
def generate_custom_invoice(
    *,
    organization: Organization,
    actor: User,
    service_account_id,
    billing_period_start: date,
    billing_period_end: date,
    issue_date: date,
    due_date: date,
    line_items: list[dict],
    notes: str = "",
) -> Invoice:
    if not organization.is_active:
        raise BillingDomainError("Organization is inactive.")

    organization = _lock_organization_for_numbering(organization=organization)

    if billing_period_end < billing_period_start:
        raise BillingDomainError("Billing period end cannot be before billing period start.")

    if due_date < issue_date:
        raise BillingDomainError("Invoice due date cannot be before issue date.")

    if not line_items:
        raise BillingDomainError("At least one line item is required.")

    try:
        service_account = (
            ServiceAccount.objects
            .select_for_update()
            .select_related("customer")
            .for_organization(organization)
            .get(id=service_account_id)
        )
    except ServiceAccount.DoesNotExist as exc:
        raise BillingDomainError("Service account was not found for this organization.") from exc

    try:
        billing_profile = service_account.billing_profile
    except ServiceAccount.billing_profile.RelatedObjectDoesNotExist as exc:
        raise BillingDomainError("Active billing profile was not found for this service account.") from exc

    invoice = Invoice.objects.create(
        organization=organization,
        invoice_number=_build_invoice_number(organization=organization),
        service_account=service_account,
        billing_profile=billing_profile,
        billing_period_start=billing_period_start,
        billing_period_end=billing_period_end,
        issue_date=issue_date,
        due_date=due_date,
        status=Invoice.Status.UNPAID,
    )

    for item in line_items:
        desc = item.get("description", "").strip()
        if not desc:
            raise BillingDomainError("Line item description cannot be empty.")
        amount = _normalize_amount(
            amount=item.get("amount"),
            error_message=f"Invalid amount for line item: {desc}",
        )
        qty = int(item.get("quantity", 1))
        unit_price = item.get("unit_price")
        norm_unit_price = _normalize_amount(amount=unit_price, error_message="Invalid unit price") if unit_price is not None else None

        InvoiceLine.objects.create(
            organization=organization,
            invoice=invoice,
            description=desc,
            quantity=max(1, qty),
            unit_price=norm_unit_price,
            amount=amount,
        )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="BILLING_CUSTOM_INVOICE_GENERATED",
        resource_type="Invoice",
        resource_id=invoice.id,
        metadata={
            "invoice_number": invoice.invoice_number,
            "service_account_id": str(service_account.id),
            "line_items_count": len(line_items),
            "total_amount": str(invoice.total_amount),
            "notes": notes.strip(),
        },
    )

    try:
        from accounting.services import post_invoice_journal_entry
        post_invoice_journal_entry(invoice=invoice, actor=actor)
    except Exception as exc:
        logger.exception("Error in accounting custom invoice hook for %s: %s", invoice.invoice_number, exc)

    return invoice


@transaction.atomic
def record_payment_with_allocations(
    *,
    organization: Organization,
    actor: User,
    service_account_id,
    amount,
    payment_method: str,
    reference: str = "",
    notes: str = "",
    allocations: list[dict] | None = None,
    paid_at=None,
) -> Payment:
    if not organization.is_active:
        raise BillingDomainError("Organization is inactive.")

    organization = _lock_organization_for_numbering(organization=organization)

    normalized_amount = _normalize_amount(
        amount=amount,
        error_message="Payment amount must be greater than zero.",
    )

    valid_payment_methods = {choice for choice, _ in Payment.Method.choices}
    if payment_method not in valid_payment_methods:
        raise BillingDomainError("Invalid payment method.")

    try:
        service_account = (
            ServiceAccount.objects
            .select_for_update()
            .select_related("customer")
            .for_organization(organization)
            .get(id=service_account_id)
        )
    except ServiceAccount.DoesNotExist as exc:
        raise BillingDomainError("Service account was not found for this organization.") from exc

    payment = Payment.objects.create(
        organization=organization,
        payment_number=_build_payment_number(organization=organization),
        service_account=service_account,
        amount=normalized_amount,
        payment_method=payment_method,
        reference=reference.strip(),
        notes=notes.strip(),
        received_by=actor,
        paid_at=paid_at or timezone.now(),
    )

    allocated_sum = Decimal("0.00")

    if allocations:
        for alloc_item in allocations:
            inv_id = alloc_item.get("invoice_id")
            alloc_amt = _normalize_amount(
                amount=alloc_item.get("amount"),
                error_message="Allocation amount must be greater than zero.",
            )

            try:
                inv = (
                    Invoice.objects
                    .select_for_update()
                    .for_organization(organization)
                    .get(id=inv_id, service_account=service_account)
                )
            except Invoice.DoesNotExist as exc:
                raise BillingDomainError("Invoice not found for this service account.") from exc

            if inv.status == Invoice.Status.CANCELLED:
                raise BillingDomainError(f"Cannot allocate payment to cancelled invoice {inv.invoice_number}.")

            if alloc_amt > inv.outstanding_amount:
                raise BillingDomainError(
                    f"Allocation amount {alloc_amt} exceeds invoice {inv.invoice_number} outstanding balance of {inv.outstanding_amount}."
                )

            PaymentAllocation.objects.create(
                organization=organization,
                payment=payment,
                invoice=inv,
                amount=alloc_amt,
            )
            allocated_sum += alloc_amt
            _refresh_invoice_status(invoice=inv)

        if allocated_sum > normalized_amount:
            raise BillingDomainError("Total allocated amounts cannot exceed total payment amount.")

    else:
        unpaid_invoices = (
            Invoice.objects
            .select_for_update()
            .for_organization(organization)
            .filter(
                service_account=service_account,
                status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID],
            )
            .order_by("due_date", "created_at")
        )

        remaining_to_allocate = normalized_amount
        for inv in unpaid_invoices:
            if remaining_to_allocate <= Decimal("0.00"):
                break

            outstanding = inv.outstanding_amount
            if outstanding <= Decimal("0.00"):
                continue

            alloc_amt = min(remaining_to_allocate, outstanding)
            PaymentAllocation.objects.create(
                organization=organization,
                payment=payment,
                invoice=inv,
                amount=alloc_amt,
            )
            remaining_to_allocate -= alloc_amt
            _refresh_invoice_status(invoice=inv)

    record_audit_log(
        organization=organization,
        actor=actor,
        action="BILLING_PAYMENT_RECORDED",
        resource_type="Payment",
        resource_id=payment.id,
        metadata={
            "payment_number": payment.payment_number,
            "service_account_id": str(service_account.id),
            "amount": str(normalized_amount),
            "allocated_amount": str(payment.allocated_amount),
            "unallocated_amount": str(payment.unallocated_amount),
        },
    )

    # Check for automated service restoration if service is suspended
    try:
        from customers.suspension_services import (
            evaluate_restoration_eligibility,
            execute_service_restoration,
            get_or_create_suspension_policy,
        )
        policy = get_or_create_suspension_policy(organization)
        if policy.auto_restoration_enabled and service_account.status in [
            ServiceAccount.Status.SUSPENDED_NON_PAYMENT,
            ServiceAccount.Status.RESTORE_PENDING,
        ]:
            is_eligible, _, _ = evaluate_restoration_eligibility(service_account)
            if is_eligible:
                execute_service_restoration(
                    service_account=service_account,
                    trigger_type="PAYMENT_TRIGGERED",
                    reason=f"Automatic restoration upon verified payment {payment.payment_number}",
                    actor=actor,
                    linked_payment=payment,
                )
    except Exception as exc:
        logger.exception("Error checking auto-restoration for %s", service_account.service_number)

    # Dispatch payment confirmation notification
    try:
        from communications.notification_engine import (
            NotificationEvent,
            dispatch_notification_event,
        )
        from customers.suspension_services import calculate_service_outstanding
        rem_balance, _, _ = calculate_service_outstanding(service_account)
        event_type = (
            NotificationEvent.PAYMENT_PARTIAL_RECEIVED
            if rem_balance > Decimal("0.00")
            else NotificationEvent.PAYMENT_RECEIVED
        )
        dispatch_notification_event(
            organization=organization,
            customer=service_account.customer,
            event_type=event_type,
            context={
                "service_number": service_account.service_number,
                "paid_amount": normalized_amount,
                "payment_number": payment.payment_number,
                "outstanding_amount": rem_balance,
            },
        )
    except Exception as exc:
        logger.exception("Error dispatching payment notification for %s", payment.payment_number)

    try:
        from accounting.services import post_payment_journal_entry
        post_payment_journal_entry(payment=payment, actor=actor)
    except Exception as exc:
        logger.exception("Error in accounting payment allocation hook for %s: %s", payment.payment_number, exc)

    return payment


@transaction.atomic
def reverse_payment(
    *,
    organization: Organization,
    actor: User,
    payment_id,
    reversal_reason: str,
    reversal_reference: str = "",
) -> Payment:
    if not organization.is_active:
        raise BillingDomainError("Organization is inactive.")

    if not reversal_reason or not reversal_reason.strip():
        raise BillingDomainError("Reversal reason is mandatory.")

    try:
        payment = (
            Payment.objects
            .select_for_update()
            .select_related("service_account")
            .for_organization(organization)
            .get(id=payment_id)
        )
    except Payment.DoesNotExist as exc:
        raise BillingDomainError("Payment was not found for this organization.") from exc

    if payment.is_reversed:
        raise BillingDomainError("Payment has already been reversed.")

    allocations = PaymentAllocation.objects.for_organization(organization).filter(payment=payment).select_related("invoice")
    affected_invoices = []
    for alloc in allocations:
        inv = Invoice.objects.select_for_update().get(id=alloc.invoice_id)
        affected_invoices.append(inv)

    allocations.delete()

    for inv in affected_invoices:
        _refresh_invoice_status(invoice=inv)

    payment.is_reversed = True
    payment.reversed_at = timezone.now()
    payment.reversal_reason = reversal_reason.strip()
    payment.reversal_reference = reversal_reference.strip()
    payment.save(update_fields=["is_reversed", "reversed_at", "reversal_reason", "reversal_reference", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="BILLING_PAYMENT_REVERSED",
        resource_type="Payment",
        resource_id=payment.id,
        metadata={
            "payment_number": payment.payment_number,
            "reversal_reason": payment.reversal_reason,
            "reversal_reference": payment.reversal_reference,
            "amount": str(payment.amount),
        },
    )

    try:
        from accounting.services import post_payment_reversal_journal_entry
        post_payment_reversal_journal_entry(payment=payment, actor=actor)
    except Exception as exc:
        logger.exception("Error in accounting payment reversal hook for %s: %s", payment.payment_number, exc)

    return payment


def get_financial_ledger(
    *,
    organization: Organization,
    customer_id=None,
    service_account_id=None,
    start_date=None,
    end_date=None,
) -> dict:
    invoices_qs = (
        Invoice.objects
        .for_organization(organization)
        .select_related("service_account", "service_account__customer")
        .prefetch_related("lines")
        .exclude(status=Invoice.Status.CANCELLED)
    )

    payments_qs = (
        Payment.objects
        .for_organization(organization)
        .select_related("service_account", "service_account__customer", "received_by")
        .prefetch_related("allocations__invoice")
    )

    if customer_id:
        invoices_qs = invoices_qs.filter(service_account__customer_id=customer_id)
        payments_qs = payments_qs.filter(service_account__customer_id=customer_id)

    if service_account_id:
        invoices_qs = invoices_qs.filter(service_account_id=service_account_id)
        payments_qs = payments_qs.filter(service_account_id=service_account_id)

    if start_date:
        invoices_qs = invoices_qs.filter(issue_date__gte=start_date)
        payments_qs = payments_qs.filter(paid_at__date__gte=start_date)

    if end_date:
        invoices_qs = invoices_qs.filter(issue_date__lte=end_date)
        payments_qs = payments_qs.filter(paid_at__date__lte=end_date)

    entries = []

    for inv in invoices_qs:
        entries.append({
            "type": "INVOICE",
            "date": str(inv.issue_date),
            "timestamp": inv.created_at,
            "reference": inv.invoice_number,
            "description": f"Invoice ({inv.billing_period_start} to {inv.billing_period_end}) - {inv.service_account.service_number}",
            "debit": inv.total_amount,
            "credit": Decimal("0.00"),
            "status": inv.status,
            "service_number": inv.service_account.service_number,
            "customer_name": inv.service_account.customer.full_name,
            "customer_id": str(inv.service_account.customer_id),
            "service_account_id": str(inv.service_account_id),
            "object_id": str(inv.id),
        })

    for pay in payments_qs:
        if pay.is_reversed:
            entries.append({
                "type": "PAYMENT_REVERSED",
                "date": str(pay.paid_at.date()),
                "timestamp": pay.created_at,
                "reference": pay.payment_number,
                "description": f"Payment Reversed: {pay.reversal_reason or 'Reversed'} (Ref: {pay.payment_number})",
                "debit": Decimal("0.00"),
                "credit": Decimal("0.00"),
                "status": "REVERSED",
                "service_number": pay.service_account.service_number,
                "customer_name": pay.service_account.customer.full_name,
                "customer_id": str(pay.service_account.customer_id),
                "service_account_id": str(pay.service_account_id),
                "object_id": str(pay.id),
            })
        else:
            entries.append({
                "type": "PAYMENT",
                "date": str(pay.paid_at.date()),
                "timestamp": pay.paid_at,
                "reference": pay.payment_number,
                "description": f"Payment via {pay.payment_method} (Ref: {pay.reference or pay.payment_number})",
                "debit": Decimal("0.00"),
                "credit": pay.amount,
                "status": "ACTIVE",
                "service_number": pay.service_account.service_number,
                "customer_name": pay.service_account.customer.full_name,
                "customer_id": str(pay.service_account.customer_id),
                "service_account_id": str(pay.service_account_id),
                "object_id": str(pay.id),
            })

    entries.sort(key=lambda x: (x["date"], x["timestamp"]))

    running_balance = Decimal("0.00")
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for entry in entries:
        running_balance += (entry["debit"] - entry["credit"])
        total_debit += entry["debit"]
        total_credit += entry["credit"]
        entry["balance"] = running_balance

    return {
        "currency": organization.currency,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "closing_balance": running_balance,
        "entries": entries,
    }


def get_payment_receipt_data(*, organization: Organization, payment_id) -> dict:
    try:
        payment = (
            Payment.objects
            .for_organization(organization)
            .select_related("service_account", "service_account__customer", "received_by")
            .prefetch_related("allocations__invoice")
            .get(id=payment_id)
        )
    except Payment.DoesNotExist as exc:
        raise BillingDomainError("Payment was not found for this organization.") from exc

    cust = payment.service_account.customer

    unpaid_invoices = Invoice.objects.for_organization(organization).filter(
        service_account__customer=cust,
        status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID],
    )
    remaining_balance = sum((inv.outstanding_amount for inv in unpaid_invoices), Decimal("0.00"))

    allocations_data = []
    for alloc in payment.allocations.all():
        allocations_data.append({
            "invoice_number": alloc.invoice.invoice_number,
            "billing_period": f"{alloc.invoice.billing_period_start} to {alloc.invoice.billing_period_end}",
            "invoice_total": str(alloc.invoice.total_amount),
            "allocated_amount": str(alloc.amount),
            "invoice_remaining": str(alloc.invoice.outstanding_amount),
            "invoice_status": alloc.invoice.status,
        })

    return {
        "organization_name": organization.name,
        "organization_code": organization.code,
        "currency": organization.currency,
        "payment_number": payment.payment_number,
        "payment_id": str(payment.id),
        "payment_date": str(payment.paid_at),
        "payment_method": payment.payment_method,
        "reference": payment.reference,
        "amount": str(payment.amount),
        "is_reversed": payment.is_reversed,
        "reversed_at": str(payment.reversed_at) if payment.reversed_at else None,
        "reversal_reason": payment.reversal_reason,
        "notes": payment.notes,
        "received_by_name": payment.received_by.get_full_name() if payment.received_by else "System",
        "customer": {
            "id": str(cust.id),
            "customer_number": cust.customer_number,
            "full_name": cust.full_name,
            "phone": cust.phone,
            "address": cust.address_line,
            "city": cust.city,
            "area": cust.area,
        },
        "service_number": payment.service_account.service_number,
        "allocations": allocations_data,
        "customer_remaining_balance": str(remaining_balance),
    }


