from dataclasses import dataclass
from datetime import date

from customers.models import (
    NotificationPreference,
    ServiceAccount,
)
from network.services import (
    ServiceLifecycleError,
    request_service_restore,
    request_service_suspension,
)
from notifications.models import NotificationJob
from notifications.services import (
    NotificationDomainError,
    queue_customer_notification,
)
from tenancy.models import Organization

from billing.models import Invoice


@dataclass(frozen=True)
class InvoiceNotificationAutomationResult:
    queued: bool
    notification_job: NotificationJob | None
    reason: str


@dataclass(frozen=True)
class PaymentLifecycleAutomationResult:
    restore_requested: bool
    provisioning_request_id: object | None
    reason: str


@dataclass(frozen=True)
class InvoiceCollectionAutomationResult:
    invoice: Invoice
    action: str
    notification_job: NotificationJob | None
    provisioning_request_id: object | None
    reason: str


@dataclass(frozen=True)
class CollectionAutomationSummary:
    organization: Organization
    evaluated_invoices: int
    overdue_reminders: int
    final_warnings: int
    suspension_requests: int
    skipped_invoices: int
    failed_invoices: int


def _resolve_customer_notification_channel(
    *,
    organization: Organization,
    customer_id,
) -> str | None:
    try:
        preference = (
            NotificationPreference.objects
            .for_organization(organization)
            .get(customer_id=customer_id)
        )
    except NotificationPreference.DoesNotExist:
        return None

    if preference.whatsapp_enabled:
        return NotificationJob.Channel.WHATSAPP

    if preference.sms_enabled:
        return NotificationJob.Channel.SMS

    return None


def _notification_exists(
    *,
    organization: Organization,
    invoice: Invoice,
    event_type: str,
) -> bool:
    return (
        NotificationJob.objects
        .for_organization(organization)
        .filter(
            customer=invoice.service_account.customer,
            service_account=invoice.service_account,
            event_type=event_type,
            context__invoice_id=str(invoice.id),
        )
        .exists()
    )


def _queue_invoice_notification(
    *,
    organization: Organization,
    invoice: Invoice,
    event_type: str,
    subject: str,
    message: str,
    actor=None,
) -> InvoiceNotificationAutomationResult:
    if invoice.organization_id != organization.id:
        return InvoiceNotificationAutomationResult(
            queued=False,
            notification_job=None,
            reason="INVOICE_ORGANIZATION_MISMATCH",
        )

    service_account = invoice.service_account
    customer = service_account.customer

    channel = _resolve_customer_notification_channel(
        organization=organization,
        customer_id=customer.id,
    )

    if channel is None:
        return InvoiceNotificationAutomationResult(
            queued=False,
            notification_job=None,
            reason="NO_ENABLED_NOTIFICATION_CHANNEL",
        )

    if _notification_exists(
        organization=organization,
        invoice=invoice,
        event_type=event_type,
    ):
        return InvoiceNotificationAutomationResult(
            queued=False,
            notification_job=None,
            reason="NOTIFICATION_ALREADY_QUEUED",
        )

    try:
        result = queue_customer_notification(
            organization=organization,
            customer_id=customer.id,
            service_account_id=service_account.id,
            channel=channel,
            event_type=event_type,
            subject=subject,
            message=message,
            context={
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "billing_period_start": (
                    invoice.billing_period_start.isoformat()
                ),
                "billing_period_end": (
                    invoice.billing_period_end.isoformat()
                ),
                "due_date": invoice.due_date.isoformat(),
                "total_amount": str(invoice.total_amount),
                "paid_amount": str(invoice.paid_amount),
                "outstanding_amount": str(
                    invoice.outstanding_amount
                ),
            },
            actor=actor,
        )
    except NotificationDomainError as exc:
        return InvoiceNotificationAutomationResult(
            queued=False,
            notification_job=None,
            reason=str(exc),
        )

    return InvoiceNotificationAutomationResult(
        queued=True,
        notification_job=result.notification_job,
        reason="QUEUED",
    )


def queue_invoice_generated_notification(
    *,
    organization: Organization,
    invoice: Invoice,
    actor=None,
) -> InvoiceNotificationAutomationResult:
    return _queue_invoice_notification(
        organization=organization,
        invoice=invoice,
        event_type="BILL_GENERATED",
        subject=f"Invoice {invoice.invoice_number}",
        message=(
            f"Your NEXORA internet invoice "
            f"{invoice.invoice_number} has been generated. "
            f"Total amount is PKR "
            f"{invoice.total_amount:.2f} and due date is "
            f"{invoice.due_date.isoformat()}."
        ),
        actor=actor,
    )


def process_fully_paid_invoice_lifecycle(
    *,
    organization: Organization,
    invoice: Invoice,
    actor=None,
) -> PaymentLifecycleAutomationResult:
    if invoice.organization_id != organization.id:
        return PaymentLifecycleAutomationResult(
            restore_requested=False,
            provisioning_request_id=None,
            reason="INVOICE_ORGANIZATION_MISMATCH",
        )

    if invoice.status != Invoice.Status.PAID:
        return PaymentLifecycleAutomationResult(
            restore_requested=False,
            provisioning_request_id=None,
            reason="INVOICE_NOT_PAID",
        )

    service_account = invoice.service_account

    if (
        service_account.status
        != ServiceAccount.Status.SUSPENDED_NON_PAYMENT
    ):
        return PaymentLifecycleAutomationResult(
            restore_requested=False,
            provisioning_request_id=None,
            reason="SERVICE_NOT_SUSPENDED_NON_PAYMENT",
        )

    try:
        result = request_service_restore(
            organization=organization,
            service_account_id=service_account.id,
            requested_by=actor,
        )
    except ServiceLifecycleError as exc:
        return PaymentLifecycleAutomationResult(
            restore_requested=False,
            provisioning_request_id=None,
            reason=str(exc),
        )

    return PaymentLifecycleAutomationResult(
        restore_requested=True,
        provisioning_request_id=(
            result.provisioning_request.id
        ),
        reason="RESTORE_REQUESTED",
    )


def process_invoice_collection(
    *,
    organization: Organization,
    invoice: Invoice,
    as_of_date: date,
    overdue_reminder_days: int,
    final_warning_days: int,
    suspension_days: int,
    actor=None,
) -> InvoiceCollectionAutomationResult:
    if invoice.organization_id != organization.id:
        return InvoiceCollectionAutomationResult(
            invoice=invoice,
            action="SKIPPED",
            notification_job=None,
            provisioning_request_id=None,
            reason="INVOICE_ORGANIZATION_MISMATCH",
        )

    if invoice.status == Invoice.Status.PAID:
        return InvoiceCollectionAutomationResult(
            invoice=invoice,
            action="SKIPPED",
            notification_job=None,
            provisioning_request_id=None,
            reason="INVOICE_ALREADY_PAID",
        )

    days_overdue = (
        as_of_date - invoice.due_date
    ).days

    if days_overdue < overdue_reminder_days:
        return InvoiceCollectionAutomationResult(
            invoice=invoice,
            action="SKIPPED",
            notification_job=None,
            provisioning_request_id=None,
            reason="NOT_YET_OVERDUE_FOR_ACTION",
        )

    service_account = invoice.service_account

    if days_overdue >= suspension_days:
        final_warning_exists = _notification_exists(
            organization=organization,
            invoice=invoice,
            event_type="FINAL_WARNING",
        )

        if not final_warning_exists:
            warning_result = _queue_invoice_notification(
                organization=organization,
                invoice=invoice,
                event_type="FINAL_WARNING",
                subject=(
                    f"Final Warning "
                    f"{invoice.invoice_number}"
                ),
                message=(
                    f"Final payment warning for invoice "
                    f"{invoice.invoice_number}. Outstanding "
                    f"amount is PKR "
                    f"{invoice.outstanding_amount:.2f}. "
                    f"Please clear the balance to avoid "
                    f"service suspension."
                ),
                actor=actor,
            )

            return InvoiceCollectionAutomationResult(
                invoice=invoice,
                action=(
                    "FINAL_WARNING"
                    if warning_result.queued
                    else "SKIPPED"
                ),
                notification_job=(
                    warning_result.notification_job
                ),
                provisioning_request_id=None,
                reason=warning_result.reason,
            )

        if service_account.status not in [
            ServiceAccount.Status.ACTIVE,
            ServiceAccount.Status.GRACE_PERIOD,
        ]:
            return InvoiceCollectionAutomationResult(
                invoice=invoice,
                action="SKIPPED",
                notification_job=None,
                provisioning_request_id=None,
                reason=(
                    "SERVICE_NOT_ELIGIBLE_FOR_SUSPENSION"
                ),
            )

        try:
            suspension_result = request_service_suspension(
                organization=organization,
                service_account_id=service_account.id,
                requested_by=actor,
            )
        except ServiceLifecycleError as exc:
            return InvoiceCollectionAutomationResult(
                invoice=invoice,
                action="FAILED",
                notification_job=None,
                provisioning_request_id=None,
                reason=str(exc),
            )

        return InvoiceCollectionAutomationResult(
            invoice=invoice,
            action="SUSPENSION_REQUESTED",
            notification_job=None,
            provisioning_request_id=(
                suspension_result.provisioning_request.id
            ),
            reason="SUSPENSION_REQUESTED",
        )

    if days_overdue >= final_warning_days:
        warning_result = _queue_invoice_notification(
            organization=organization,
            invoice=invoice,
            event_type="FINAL_WARNING",
            subject=(
                f"Final Warning {invoice.invoice_number}"
            ),
            message=(
                f"Final payment warning for invoice "
                f"{invoice.invoice_number}. Outstanding "
                f"amount is PKR "
                f"{invoice.outstanding_amount:.2f}. "
                f"Please clear the balance to avoid "
                f"service suspension."
            ),
            actor=actor,
        )

        return InvoiceCollectionAutomationResult(
            invoice=invoice,
            action=(
                "FINAL_WARNING"
                if warning_result.queued
                else "SKIPPED"
            ),
            notification_job=warning_result.notification_job,
            provisioning_request_id=None,
            reason=warning_result.reason,
        )

    reminder_result = _queue_invoice_notification(
        organization=organization,
        invoice=invoice,
        event_type="OVERDUE_REMINDER",
        subject=(
            f"Payment Reminder {invoice.invoice_number}"
        ),
        message=(
            f"Invoice {invoice.invoice_number} is overdue. "
            f"Outstanding amount is PKR "
            f"{invoice.outstanding_amount:.2f}. "
            f"Please clear the outstanding balance."
        ),
        actor=actor,
    )

    return InvoiceCollectionAutomationResult(
        invoice=invoice,
        action=(
            "OVERDUE_REMINDER"
            if reminder_result.queued
            else "SKIPPED"
        ),
        notification_job=reminder_result.notification_job,
        provisioning_request_id=None,
        reason=reminder_result.reason,
    )


def run_collection_automation(
    *,
    organization: Organization,
    as_of_date: date,
    overdue_reminder_days: int,
    final_warning_days: int,
    suspension_days: int,
    actor=None,
) -> CollectionAutomationSummary:
    if not organization.is_active:
        raise ValueError("Organization is not active.")

    if overdue_reminder_days < 1:
        raise ValueError(
            "Overdue reminder days must be greater than zero."
        )

    if not (
        overdue_reminder_days
        < final_warning_days
        < suspension_days
    ):
        raise ValueError(
            "Collection thresholds must satisfy: "
            "overdue reminder < final warning < suspension."
        )

    invoices = (
        Invoice.objects
        .for_organization(organization)
        .exclude(status=Invoice.Status.PAID)
        .filter(due_date__lt=as_of_date)
        .select_related(
            "service_account",
            "service_account__customer",
        )
        .order_by("due_date", "invoice_number")
    )

    evaluated_invoices = 0
    overdue_reminders = 0
    final_warnings = 0
    suspension_requests = 0
    skipped_invoices = 0
    failed_invoices = 0

    for invoice in invoices:
        evaluated_invoices += 1

        result = process_invoice_collection(
            organization=organization,
            invoice=invoice,
            as_of_date=as_of_date,
            overdue_reminder_days=overdue_reminder_days,
            final_warning_days=final_warning_days,
            suspension_days=suspension_days,
            actor=actor,
        )

        if result.action == "OVERDUE_REMINDER":
            overdue_reminders += 1
        elif result.action == "FINAL_WARNING":
            final_warnings += 1
        elif result.action == "SUSPENSION_REQUESTED":
            suspension_requests += 1
        elif result.action == "FAILED":
            failed_invoices += 1
        else:
            skipped_invoices += 1

    return CollectionAutomationSummary(
        organization=organization,
        evaluated_invoices=evaluated_invoices,
        overdue_reminders=overdue_reminders,
        final_warnings=final_warnings,
        suspension_requests=suspension_requests,
        skipped_invoices=skipped_invoices,
        failed_invoices=failed_invoices,
    )