import calendar
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from billing.models import Invoice, Payment
from billing.services import (
    BillingDomainError,
    _lock_organization_for_numbering,
    generate_custom_invoice,
    record_payment_with_allocations,
)
from customers.models import BillingProfile, ServiceAccount, ServiceSuspensionLog
from tenancy.services import record_audit_log

logger = logging.getLogger(__name__)

MAX_RECHARGE_MONTHS = 12

SUSPENDED_STATUSES = [
    ServiceAccount.Status.SUSPENDED_NON_PAYMENT,
    ServiceAccount.Status.RESTORE_PENDING,
]


@dataclass(frozen=True)
class RechargeResult:
    service_account: ServiceAccount
    invoice: Invoice
    payment: Payment | None
    months: int
    amount: Decimal
    previous_expiry_date: date | None
    new_expiry_date: date
    restored: bool


def _add_months(*, start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calculate_recharge_period(*, expiry_date: date | None, months: int, today: date) -> tuple[date, date]:
    """Return (period_start, new_expiry_date) for a recharge of `months`.

    An active service extends from the day after its current expiry, so early
    recharges never lose paid days. An expired or new service starts today.
    """
    if expiry_date and expiry_date >= today:
        period_start = expiry_date + timedelta(days=1)
    else:
        period_start = today

    new_expiry_date = _add_months(start=period_start, months=months) - timedelta(days=1)
    return period_start, new_expiry_date


def _get_prepaid_service(*, organization, service_account_id) -> ServiceAccount:
    try:
        service_account = (
            ServiceAccount.objects
            .select_for_update(of=("self",))
            .select_related("customer", "internet_package", "billing_profile")
            .for_organization(organization)
            .get(id=service_account_id)
        )
    except ServiceAccount.DoesNotExist as exc:
        raise BillingDomainError("Service account was not found for this organization.") from exc

    try:
        billing_profile = service_account.billing_profile
    except ServiceAccount.billing_profile.RelatedObjectDoesNotExist as exc:
        raise BillingDomainError("Active billing profile was not found for this service account.") from exc

    if billing_profile.billing_cycle != BillingProfile.BillingCycle.PREPAID:
        raise BillingDomainError("Recharge is only available for prepaid services.")

    return service_account


@transaction.atomic
def recharge_service(
    *,
    organization,
    actor,
    service_account_id,
    months: int,
    payment_method: str,
    reference: str = "",
    notes: str = "",
) -> RechargeResult:
    if not organization.is_active:
        raise BillingDomainError("Organization is inactive.")

    if months < 1 or months > MAX_RECHARGE_MONTHS:
        raise BillingDomainError(f"Recharge months must be between 1 and {MAX_RECHARGE_MONTHS}.")

    # Organization first, then service: the same lock order as invoice and
    # payment numbering.
    organization = _lock_organization_for_numbering(organization=organization)
    service_account = _get_prepaid_service(
        organization=organization,
        service_account_id=service_account_id,
    )

    package = service_account.internet_package
    amount = (package.monthly_price * months).quantize(Decimal("0.01"))
    if amount <= Decimal("0.00"):
        raise BillingDomainError("Package price must be greater than zero to recharge.")

    today = timezone.localdate()
    previous_expiry_date = service_account.expiry_date
    period_start, new_expiry_date = calculate_recharge_period(
        expiry_date=previous_expiry_date,
        months=months,
        today=today,
    )

    month_label = "month" if months == 1 else "months"
    invoice = generate_custom_invoice(
        organization=organization,
        actor=actor,
        service_account_id=service_account.id,
        billing_period_start=period_start,
        billing_period_end=new_expiry_date,
        issue_date=today,
        due_date=today,
        line_items=[
            {
                "description": f"Recharge: {package.name} ({months} {month_label})",
                "quantity": months,
                "unit_price": package.monthly_price,
                "amount": amount,
            }
        ],
        notes=notes,
    )

    # Customer advance may already cover part or all of the recharge.
    invoice.refresh_from_db()
    payment = None
    if invoice.outstanding_amount > Decimal("0.00"):
        payment = record_payment_with_allocations(
            organization=organization,
            actor=actor,
            service_account_id=service_account.id,
            amount=invoice.outstanding_amount,
            payment_method=payment_method,
            reference=reference,
            notes=notes or f"Prepaid recharge {invoice.invoice_number}",
            allocations=[
                {"invoice_id": invoice.id, "amount": invoice.outstanding_amount},
            ],
        )
        invoice.refresh_from_db()

    service_account.refresh_from_db()
    service_account.expiry_date = new_expiry_date
    service_account.save(update_fields=["expiry_date", "updated_at"])

    restored = False
    if service_account.status in SUSPENDED_STATUSES:
        from customers.suspension_services import (
            calculate_service_outstanding,
            execute_service_restoration,
        )

        outstanding, _, _ = calculate_service_outstanding(service_account)
        if outstanding <= Decimal("0.00"):
            execute_service_restoration(
                service_account=service_account,
                trigger_type=ServiceSuspensionLog.TriggerType.PAYMENT_TRIGGERED,
                reason=f"Prepaid recharge {invoice.invoice_number} until {new_expiry_date.isoformat()}",
                actor=actor,
                linked_payment=payment,
            )
            restored = True

    record_audit_log(
        organization=organization,
        actor=actor,
        action="PREPAID_SERVICE_RECHARGED",
        resource_type="ServiceAccount",
        resource_id=service_account.id,
        metadata={
            "service_number": service_account.service_number,
            "invoice_number": invoice.invoice_number,
            "payment_number": payment.payment_number if payment else None,
            "months": months,
            "amount": str(amount),
            "previous_expiry_date": previous_expiry_date.isoformat() if previous_expiry_date else None,
            "new_expiry_date": new_expiry_date.isoformat(),
            "restored": restored,
        },
    )

    return RechargeResult(
        service_account=service_account,
        invoice=invoice,
        payment=payment,
        months=months,
        amount=amount,
        previous_expiry_date=previous_expiry_date,
        new_expiry_date=new_expiry_date,
        restored=restored,
    )


@transaction.atomic
def change_billing_mode(
    *,
    organization,
    actor,
    service_account_id,
    billing_cycle: str,
    expiry_date: date | None = None,
) -> ServiceAccount:
    """Switch a service between monthly invoicing and prepaid recharge."""
    valid_cycles = {choice for choice, _ in BillingProfile.BillingCycle.choices}
    if billing_cycle not in valid_cycles:
        raise BillingDomainError("Invalid billing mode.")

    try:
        service_account = (
            ServiceAccount.objects
            .select_for_update(of=("self",))
            .select_related("billing_profile")
            .for_organization(organization)
            .get(id=service_account_id)
        )
        billing_profile = service_account.billing_profile
    except ServiceAccount.DoesNotExist as exc:
        raise BillingDomainError("Service account was not found for this organization.") from exc
    except ServiceAccount.billing_profile.RelatedObjectDoesNotExist as exc:
        raise BillingDomainError("Active billing profile was not found for this service account.") from exc

    previous_cycle = billing_profile.billing_cycle
    previous_expiry_date = service_account.expiry_date

    billing_profile.billing_cycle = billing_cycle
    billing_profile.save(update_fields=["billing_cycle", "updated_at"])

    if billing_cycle == BillingProfile.BillingCycle.PREPAID:
        # Without a stated expiry the service stays usable until the end of
        # today, then the nightly expiry run suspends it unless recharged.
        service_account.expiry_date = expiry_date or previous_expiry_date or timezone.localdate()
    else:
        service_account.expiry_date = None
    service_account.save(update_fields=["expiry_date", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="SERVICE_BILLING_MODE_CHANGED",
        resource_type="ServiceAccount",
        resource_id=service_account.id,
        metadata={
            "service_number": service_account.service_number,
            "previous_billing_cycle": previous_cycle,
            "billing_cycle": billing_cycle,
            "previous_expiry_date": previous_expiry_date.isoformat() if previous_expiry_date else None,
            "expiry_date": service_account.expiry_date.isoformat() if service_account.expiry_date else None,
        },
    )

    return service_account


def _prepaid_services(*, organization):
    return (
        ServiceAccount.objects
        .for_organization(organization)
        .filter(
            billing_profile__billing_cycle=BillingProfile.BillingCycle.PREPAID,
            billing_profile__is_active=True,
            expiry_date__isnull=False,
        )
        .select_related("customer", "internet_package")
    )


def get_expiring_services(*, organization, days: int = 3) -> list[dict]:
    """Prepaid services that expired already or expire within `days`."""
    today = timezone.localdate()
    services = (
        _prepaid_services(organization=organization)
        .filter(expiry_date__lte=today + timedelta(days=days))
        .order_by("expiry_date", "service_number")
    )

    return [
        {
            "service_account_id": str(service.id),
            "service_number": service.service_number,
            "customer_id": str(service.customer_id),
            "customer_name": service.customer.full_name,
            "customer_phone": service.customer.phone,
            "package_name": service.internet_package.name,
            "monthly_price": str(service.internet_package.monthly_price),
            "status": service.status,
            "expiry_date": service.expiry_date.isoformat(),
            "days_left": (service.expiry_date - today).days,
        }
        for service in services
    ]


def expire_prepaid_services(*, organization) -> dict:
    """Suspend prepaid services whose last paid day has passed."""
    from customers.suspension_services import execute_service_suspension

    today = timezone.localdate()
    expired_services = (
        _prepaid_services(organization=organization)
        .filter(
            expiry_date__lt=today,
            # SUSPENSION_PENDING is already on its way to the router.
            status__in=[
                ServiceAccount.Status.ACTIVE,
                ServiceAccount.Status.GRACE_PERIOD,
            ],
        )
        .order_by("expiry_date", "service_number")
    )

    suspended_count = 0
    failed_count = 0

    for service_account in expired_services:
        try:
            with transaction.atomic():
                locked_service = (
                    ServiceAccount.objects
                    .select_for_update()
                    .get(id=service_account.id)
                )
                # A recharge may have landed after the query ran.
                if not locked_service.expiry_date or locked_service.expiry_date >= today:
                    continue

                execute_service_suspension(
                    service_account=locked_service,
                    trigger_type=ServiceSuspensionLog.TriggerType.PREPAID_EXPIRY,
                    reason=f"Prepaid package expired on {locked_service.expiry_date.isoformat()}",
                    actor=None,
                )
            suspended_count += 1
        except Exception:
            failed_count += 1
            logger.exception("Failed to suspend expired prepaid service %s", service_account.service_number)

    return {
        "suspended_count": suspended_count,
        "failed_count": failed_count,
    }
