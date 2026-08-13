import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from communications.models import CommunicationAutomation
from communications.automation_service import CommunicationAutomationService

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
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
        raise BillingDomainError(
            error_message
        ) from exc

    if normalized_amount <= Decimal("0.00"):
        raise BillingDomainError(
            error_message
        )

    return normalized_amount.quantize(
        Decimal("0.01")
    )


def _refresh_invoice_status(
    *,
    invoice: Invoice,
) -> Invoice:
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
        invoice.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return invoice


def _get_month_period(
    *,
    billing_year: int,
    billing_month: int,
) -> tuple[date, date]:
    if billing_year < 2000:
        raise BillingDomainError(
            "Billing year is invalid."
        )

    if billing_month < 1 or billing_month > 12:
        raise BillingDomainError(
            "Billing month must be between 1 and 12."
        )

    last_day = calendar.monthrange(
        billing_year,
        billing_month,
    )[1]

    return (
        date(
            billing_year,
            billing_month,
            1,
        ),
        date(
            billing_year,
            billing_month,
            last_day,
        ),
    )


def _resolve_billing_dates(
    *,
    billing_profile: BillingProfile,
    billing_year: int,
    billing_month: int,
) -> tuple[date, date]:
    last_day = calendar.monthrange(
        billing_year,
        billing_month,
    )[1]

    issue_day = min(
        billing_profile.billing_day,
        last_day,
    )

    due_day = min(
        billing_profile.due_day,
        last_day,
    )

    issue_date = date(
        billing_year,
        billing_month,
        issue_day,
    )

    due_date = date(
        billing_year,
        billing_month,
        due_day,
    )

    if due_date < issue_date:
        raise BillingDomainError(
            "Billing profile due day cannot produce "
            "a due date before the invoice issue date."
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
        raise BillingDomainError(
            "Organization is inactive."
        )

    if billing_period_end < billing_period_start:
        raise BillingDomainError(
            "Billing period end cannot be before "
            "billing period start."
        )

    if due_date < issue_date:
        raise BillingDomainError(
            "Invoice due date cannot be before issue date."
        )

    try:
        service_account = (
            ServiceAccount.objects
            .select_for_update()
            .select_related(
                "internet_package",
            )
            .for_organization(organization)
            .get(id=service_account_id)
        )
    except ServiceAccount.DoesNotExist as exc:
        raise BillingDomainError(
            "Service account was not found "
            "for this organization."
        ) from exc

    try:
        billing_profile = service_account.billing_profile
    except (
        ServiceAccount.billing_profile.RelatedObjectDoesNotExist
    ) as exc:
        raise BillingDomainError(
            "Active billing profile was not found "
            "for this service account."
        ) from exc

    if not billing_profile.is_active:
        raise BillingDomainError(
            "Billing profile is inactive."
        )

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
            "Invoice already exists for this service "
            "and billing period."
        )

    package_price = _normalize_amount(
        amount=(
            service_account
            .internet_package
            .monthly_price
        ),
        error_message=(
            "Internet package monthly price must be "
            "greater than zero."
        ),
    )

    invoice = Invoice.objects.create(
        organization=organization,
        invoice_number=_build_invoice_number(
            organization=organization,
        ),
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
            f"{service_account.internet_package.name} "
            f"monthly internet service"
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
            "service_account_id": str(
                service_account.id
            ),
            "service_number": (
                service_account.service_number
            ),
            "billing_period_start": (
                billing_period_start.isoformat()
            ),
            "billing_period_end": (
                billing_period_end.isoformat()
            ),
            "total_amount": str(
                invoice.total_amount
            ),
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

    return InvoiceGenerationResult(
        invoice=invoice,
        invoice_line=invoice_line,
    )


def generate_monthly_invoices(
    *,
    organization: Organization,
    actor: User | None,
    billing_year: int,
    billing_month: int,
) -> MonthlyBillingGenerationResult:
    if not organization.is_active:
        raise BillingDomainError(
            "Organization is inactive."
        )

    (
        billing_period_start,
        billing_period_end,
    ) = _get_month_period(
        billing_year=billing_year,
        billing_month=billing_month,
    )

    billing_profiles = (
        BillingProfile.objects
        .for_organization(organization)
        .filter(
            is_active=True,
            service_account__status__in=[
                "ACTIVE",
                "GRACE_PERIOD",
            ],
        )
        .select_related(
            "service_account",
            "service_account__internet_package",
        )
        .order_by(
            "service_account__service_number"
        )
    )

    eligible_services = billing_profiles.count()
    generated_invoices = 0
    skipped_existing_invoices = 0
    failed_services = 0

    for billing_profile in billing_profiles:
        service_account = (
            billing_profile.service_account
        )

        invoice_exists = (
            Invoice.objects
            .for_organization(organization)
            .filter(
                service_account=service_account,
                billing_period_start=(
                    billing_period_start
                ),
                billing_period_end=(
                    billing_period_end
                ),
            )
            .exists()
        )

        if invoice_exists:
            skipped_existing_invoices += 1
            continue

        try:
            issue_date, due_date = (
                _resolve_billing_dates(
                    billing_profile=billing_profile,
                    billing_year=billing_year,
                    billing_month=billing_month,
                )
            )

            generate_service_invoice(
                organization=organization,
                actor=actor,
                service_account_id=(
                    service_account.id
                ),
                billing_period_start=(
                    billing_period_start
                ),
                billing_period_end=(
                    billing_period_end
                ),
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
            "skipped_existing_invoices": (
                skipped_existing_invoices
            ),
            "failed_services": failed_services,
        },
    )

    return MonthlyBillingGenerationResult(
        organization=organization,
        billing_year=billing_year,
        billing_month=billing_month,
        eligible_services=eligible_services,
        generated_invoices=generated_invoices,
        skipped_existing_invoices=(
            skipped_existing_invoices
        ),
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
    normalized_amount = _normalize_amount(
        amount=amount,
        error_message=(
            "Payment amount must be greater than zero."
        ),
    )

    valid_payment_methods = {
        choice
        for choice, _ in Payment.Method.choices
    }

    if payment_method not in valid_payment_methods:
        raise BillingDomainError(
            "Invalid payment method."
        )

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
        raise BillingDomainError(
            "Invoice is already fully paid."
        )

    if normalized_amount > outstanding_amount:
        raise BillingDomainError(
            "Payment amount cannot exceed invoice "
            "outstanding amount."
        )

    previous_status = invoice.status

    payment = Payment.objects.create(
        organization=organization,
        payment_number=_build_payment_number(
            organization=organization,
        ),
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

    invoice = _refresh_invoice_status(
        invoice=invoice,
    )

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
            "service_account_id": str(
                invoice.service_account_id
            ),
            "service_number": (
                invoice.service_account.service_number
            ),
            "payment_amount": str(normalized_amount),
            "invoice_status": invoice.status,
            "invoice_outstanding_amount": str(
                invoice.outstanding_amount
            ),
        },
    )

    if (
        previous_status != Invoice.Status.PAID
        and invoice.status == Invoice.Status.PAID
    ):
        record_audit_log(
            organization=organization,
            actor=actor,
            action="BILLING_INVOICE_FULLY_PAID",
            resource_type="Invoice",
            resource_id=invoice.id,
            metadata={
                "invoice_number": (
                    invoice.invoice_number
                ),
                "payment_id": str(payment.id),
                "payment_number": (
                    payment.payment_number
                ),
                "total_amount": str(
                    invoice.total_amount
                ),
                "paid_amount": str(
                    invoice.paid_amount
                ),
                "outstanding_amount": str(
                    invoice.outstanding_amount
                ),
            },
        )

        process_fully_paid_invoice_lifecycle(
            organization=organization,
            invoice=invoice,
            actor=actor,
        )

    return PaymentRecordingResult(
        payment=payment,
        allocation=allocation,
        invoice=invoice,
    )