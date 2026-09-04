import logging
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from billing.models import Invoice, PromiseToPay
from communications.notification_engine import (
    NotificationEvent,
    dispatch_notification_event,
)
from customers.models import (
    Customer,
    ServiceAccount,
    ServiceSuspensionLog,
    SuspensionPolicy,
)
from network.models import NetworkAssignment, ProvisioningRequest
from tenancy.services import record_audit_log

logger = logging.getLogger(__name__)


def get_or_create_suspension_policy(organization) -> SuspensionPolicy:
    policy, _ = SuspensionPolicy.objects.get_or_create(
        organization=organization,
        defaults={
            "grace_period_days": 3,
            "suspension_threshold_days": 5,
            "minimum_outstanding_amount": Decimal("0.00"),
            "auto_suspension_enabled": True,
            "auto_restoration_enabled": True,
            "restore_on_partial_payment": False,
            "ptp_exemption_enabled": True,
            "warning_days_before_suspension": 2,
            "send_suspension_warning": True,
        },
    )
    return policy


@transaction.atomic
def update_suspension_policy(organization, data: dict, actor=None) -> SuspensionPolicy:
    policy = get_or_create_suspension_policy(organization)

    fields_to_update = [
        "grace_period_days",
        "suspension_threshold_days",
        "minimum_outstanding_amount",
        "auto_suspension_enabled",
        "auto_restoration_enabled",
        "restore_on_partial_payment",
        "ptp_exemption_enabled",
        "warning_days_before_suspension",
        "send_suspension_warning",
    ]

    for field in fields_to_update:
        if field in data:
            val = data[field]
            if field == "minimum_outstanding_amount" and val is not None:
                val = Decimal(str(val))
            setattr(policy, field, val)

    policy.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="SUSPENSION_POLICY_UPDATED",
        resource_type="SuspensionPolicy",
        resource_id=policy.id,
        metadata={"updated_fields": list(data.keys())},
    )

    return policy


def calculate_service_outstanding(service_account: ServiceAccount) -> tuple[Decimal, list[dict], date | None]:
    """
    Authoritative computation of outstanding balance for a service account.
    Returns (total_outstanding, list_of_unpaid_invoices, oldest_due_date).
    """
    unpaid_invoices = Invoice.objects.filter(
        organization=service_account.organization,
        service_account=service_account,
        status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID],
    ).order_by("due_date", "issue_date")

    total_outstanding = Decimal("0.00")
    invoices_snapshot = []
    oldest_due_date = None

    for inv in unpaid_invoices:
        inv_outstanding = Decimal(str(inv.total_amount)) - Decimal(str(inv.paid_amount))
        if inv_outstanding > Decimal("0.00"):
            total_outstanding += inv_outstanding
            if oldest_due_date is None or inv.due_date < oldest_due_date:
                oldest_due_date = inv.due_date
            invoices_snapshot.append({
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "due_date": inv.due_date.isoformat(),
                "total_amount": str(inv.total_amount),
                "paid_amount": str(inv.paid_amount),
                "outstanding_amount": str(inv_outstanding),
            })

    return total_outstanding, invoices_snapshot, oldest_due_date


def evaluate_suspension_eligibility(organization) -> list[dict]:
    """
    Evaluates all active/grace period services in the organization for suspension eligibility.
    Considers grace periods, overdue thresholds, minimum amounts, and active PTP exemptions.
    """
    policy = get_or_create_suspension_policy(organization)
    today = timezone.now().date()

    active_services = ServiceAccount.objects.filter(
        organization=organization,
        status__in=[
            ServiceAccount.Status.ACTIVE,
            ServiceAccount.Status.GRACE_PERIOD,
            ServiceAccount.Status.SUSPENSION_PENDING,
        ],
    ).select_related("customer", "internet_package")

    eligible_list = []

    for svc in active_services:
        total_outstanding, invoices_snapshot, oldest_due_date = calculate_service_outstanding(svc)

        if total_outstanding <= Decimal("0.00") or not oldest_due_date:
            continue

        days_past_due = (today - oldest_due_date).days if today > oldest_due_date else 0
        in_grace_period = days_past_due <= policy.grace_period_days
        days_overdue = max(0, days_past_due - policy.grace_period_days)

        # Check Promise-to-Pay exemption
        active_ptp = None
        is_ptp_exempt = False
        if policy.ptp_exemption_enabled:
            active_ptp = PromiseToPay.objects.filter(
                organization=organization,
                service_account=svc,
                status__in=[PromiseToPay.Status.PENDING, PromiseToPay.Status.ACTIVE],
                deadline__gte=today,
            ).order_by("-deadline").first()

            if active_ptp:
                is_ptp_exempt = True

        # Check eligibility
        is_eligible_for_suspension = (
            days_overdue >= policy.suspension_threshold_days
            and total_outstanding >= policy.minimum_outstanding_amount
            and not is_ptp_exempt
        )

        # Check warning eligibility
        warning_threshold = max(0, policy.suspension_threshold_days - policy.warning_days_before_suspension)
        is_warning_eligible = (
            days_overdue >= warning_threshold
            and not is_eligible_for_suspension
            and not is_ptp_exempt
            and policy.send_suspension_warning
        )

        expected_suspension_date = oldest_due_date + timedelta(
            days=policy.grace_period_days + policy.suspension_threshold_days
        )

        eligible_list.append({
            "service_account_id": str(svc.id),
            "service_number": svc.service_number,
            "customer_id": str(svc.customer.id),
            "customer_name": svc.customer.full_name,
            "customer_phone": svc.customer.phone,
            "package_name": svc.internet_package.name,
            "current_status": svc.status,
            "total_outstanding": str(total_outstanding),
            "oldest_due_date": oldest_due_date.isoformat(),
            "days_past_due": days_past_due,
            "days_overdue": days_overdue,
            "in_grace_period": in_grace_period,
            "is_ptp_exempt": is_ptp_exempt,
            "ptp_promise_number": active_ptp.promise_number if active_ptp else None,
            "ptp_deadline": active_ptp.deadline.isoformat() if active_ptp else None,
            "is_eligible_for_suspension": is_eligible_for_suspension,
            "is_warning_eligible": is_warning_eligible,
            "expected_suspension_date": expected_suspension_date.isoformat(),
            "invoices_count": len(invoices_snapshot),
            "invoices_snapshot": invoices_snapshot,
        })

    return eligible_list


@transaction.atomic
def execute_service_suspension(
    *,
    service_account: ServiceAccount,
    trigger_type: str,
    reason: str,
    actor=None,
    force: bool = False,
) -> ServiceSuspensionLog:
    """
    Authoritatively suspends a service account.
    Enforces idempotency, audit logging, provisioning action, and customer notification.
    """
    organization = service_account.organization

    # Idempotency check
    if service_account.status == ServiceAccount.Status.SUSPENDED_NON_PAYMENT:
        latest_log = ServiceSuspensionLog.objects.filter(
            organization=organization,
            service_account=service_account,
            event_type=ServiceSuspensionLog.EventType.SUSPENSION,
        ).first()
        if latest_log:
            return latest_log

    if not force and service_account.status not in [
        ServiceAccount.Status.ACTIVE,
        ServiceAccount.Status.GRACE_PERIOD,
        ServiceAccount.Status.SUSPENSION_PENDING,
    ]:
        raise ValidationError(f"Service account cannot be suspended from status {service_account.status}")

    total_outstanding, invoices_snapshot, _ = calculate_service_outstanding(service_account)
    prev_status = service_account.status

    # Transition state
    service_account.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
    service_account.save(update_fields=["status", "updated_at"])

    # Create network provisioning request if network assignment exists
    network_assignment = NetworkAssignment.objects.filter(
        organization=organization,
        service_account=service_account,
    ).first()

    if network_assignment:
        ProvisioningRequest.objects.create(
            organization=organization,
            service_account=service_account,
            network_assignment=network_assignment,
            action=ProvisioningRequest.Action.SUSPEND,
            status=ProvisioningRequest.Status.COMPLETED,
            requested_payload={"reason": reason, "trigger": trigger_type},
            executed_at=timezone.now(),
        )

    # Log suspension history
    suspension_log = ServiceSuspensionLog.objects.create(
        organization=organization,
        service_account=service_account,
        customer=service_account.customer,
        event_type=ServiceSuspensionLog.EventType.SUSPENSION,
        trigger_type=trigger_type,
        previous_status=prev_status,
        new_status=ServiceAccount.Status.SUSPENDED_NON_PAYMENT,
        outstanding_amount=total_outstanding,
        reason=reason,
        actor=actor,
        invoices_snapshot=invoices_snapshot,
    )

    # Audit log
    record_audit_log(
        organization=organization,
        actor=actor,
        action="SERVICE_SUSPENDED",
        resource_type="ServiceAccount",
        resource_id=service_account.id,
        metadata={
            "service_number": service_account.service_number,
            "trigger_type": trigger_type,
            "previous_status": prev_status,
            "outstanding_amount": str(total_outstanding),
            "reason": reason,
        },
    )

    # Customer notification
    try:
        dispatch_notification_event(
            organization=organization,
            customer=service_account.customer,
            event_type=NotificationEvent.SERVICE_SUSPENDED,
            context={
                "service_number": service_account.service_number,
                "package_name": service_account.internet_package.name,
                "outstanding_amount": total_outstanding,
                "reason": reason,
            },
        )
    except Exception as exc:
        logger.exception("Failed to dispatch suspension notification for %s", service_account.service_number)

    return suspension_log


def evaluate_restoration_eligibility(service_account: ServiceAccount) -> tuple[bool, Decimal, str]:
    """
    Evaluates whether a suspended service account is eligible for automatic restoration.
    Returns (is_eligible, outstanding_amount, reason).
    """
    policy = get_or_create_suspension_policy(service_account.organization)

    if service_account.status not in [
        ServiceAccount.Status.SUSPENDED_NON_PAYMENT,
        ServiceAccount.Status.RESTORE_PENDING,
    ]:
        return False, Decimal("0.00"), "Service is not suspended"

    total_outstanding, _, _ = calculate_service_outstanding(service_account)

    if policy.restore_on_partial_payment:
        return True, total_outstanding, "Eligible under partial payment restoration policy"

    if total_outstanding <= policy.minimum_outstanding_amount or total_outstanding <= Decimal("0.00"):
        return True, total_outstanding, "Outstanding balance fully cleared"

    return False, total_outstanding, f"Remaining balance of PKR {total_outstanding} exceeds threshold"


@transaction.atomic
def execute_service_restoration(
    *,
    service_account: ServiceAccount,
    trigger_type: str,
    reason: str,
    actor=None,
    linked_payment=None,
    force: bool = False,
) -> ServiceSuspensionLog:
    """
    Authoritatively restores a suspended service account.
    Enforces idempotency, audit logging, provisioning action, and customer notification.
    """
    organization = service_account.organization

    # Idempotency check
    if service_account.status == ServiceAccount.Status.ACTIVE:
        latest_log = ServiceSuspensionLog.objects.filter(
            organization=organization,
            service_account=service_account,
            event_type=ServiceSuspensionLog.EventType.RESTORATION,
        ).first()
        if latest_log:
            return latest_log

    if not force and service_account.status not in [
        ServiceAccount.Status.SUSPENDED_NON_PAYMENT,
        ServiceAccount.Status.RESTORE_PENDING,
        ServiceAccount.Status.GRACE_PERIOD,
    ]:
        raise ValidationError(f"Service account cannot be restored from status {service_account.status}")

    total_outstanding, _, _ = calculate_service_outstanding(service_account)
    prev_status = service_account.status

    # Transition state
    service_account.status = ServiceAccount.Status.ACTIVE
    service_account.save(update_fields=["status", "updated_at"])

    # Create network provisioning request if network assignment exists
    network_assignment = NetworkAssignment.objects.filter(
        organization=organization,
        service_account=service_account,
    ).first()

    if network_assignment:
        ProvisioningRequest.objects.create(
            organization=organization,
            service_account=service_account,
            network_assignment=network_assignment,
            action=ProvisioningRequest.Action.RESTORE,
            status=ProvisioningRequest.Status.COMPLETED,
            requested_payload={
                "reason": reason,
                "trigger": trigger_type,
                "payment_id": str(linked_payment.id) if linked_payment else None,
            },
            executed_at=timezone.now(),
        )

    # Log restoration history
    restoration_log = ServiceSuspensionLog.objects.create(
        organization=organization,
        service_account=service_account,
        customer=service_account.customer,
        event_type=ServiceSuspensionLog.EventType.RESTORATION,
        trigger_type=trigger_type,
        previous_status=prev_status,
        new_status=ServiceAccount.Status.ACTIVE,
        outstanding_amount=total_outstanding,
        reason=reason,
        actor=actor,
        linked_payment_id=linked_payment.id if linked_payment else None,
    )

    # Audit log
    record_audit_log(
        organization=organization,
        actor=actor,
        action="SERVICE_RESTORED",
        resource_type="ServiceAccount",
        resource_id=service_account.id,
        metadata={
            "service_number": service_account.service_number,
            "trigger_type": trigger_type,
            "previous_status": prev_status,
            "linked_payment_id": str(linked_payment.id) if linked_payment else None,
            "reason": reason,
        },
    )

    # Customer notification
    try:
        dispatch_notification_event(
            organization=organization,
            customer=service_account.customer,
            event_type=NotificationEvent.SERVICE_RESTORED,
            context={
                "service_number": service_account.service_number,
                "package_name": service_account.internet_package.name,
                "restoration_date": timezone.now().strftime("%Y-%m-%d %H:%M"),
            },
        )
    except Exception as exc:
        logger.exception("Failed to dispatch restoration notification for %s", service_account.service_number)

    return restoration_log


@transaction.atomic
def run_automated_suspension_engine(organization) -> dict:
    """
    Executes the automated suspension and warning run for an organization.
    Safe, idempotent, and non-blocking.
    """
    policy = get_or_create_suspension_policy(organization)

    if not policy.auto_suspension_enabled:
        return {
            "status": "SKIPPED",
            "message": "Automated suspension is disabled in organization policy.",
            "suspended_count": 0,
            "warning_count": 0,
            "exempt_count": 0,
        }

    evaluated_items = evaluate_suspension_eligibility(organization)
    today = timezone.now().date()

    suspended_count = 0
    warning_count = 0
    exempt_count = 0

    for item in evaluated_items:
        if item["is_ptp_exempt"]:
            exempt_count += 1
            continue

        service_account = ServiceAccount.objects.get(id=item["service_account_id"])

        if item["is_eligible_for_suspension"]:
            execute_service_suspension(
                service_account=service_account,
                trigger_type=ServiceSuspensionLog.TriggerType.SYSTEM_AUTOMATED,
                reason=(
                    f"Automated suspension: Overdue by {item['days_overdue']} days past grace period. "
                    f"Outstanding balance: PKR {item['total_outstanding']}"
                ),
                actor=None,
            )
            suspended_count += 1

        elif item["is_warning_eligible"]:
            # Check if warning already logged today to prevent duplicate spam
            existing_warning = ServiceSuspensionLog.objects.filter(
                organization=organization,
                service_account=service_account,
                event_type=ServiceSuspensionLog.EventType.WARNING,
                created_at__date=today,
            ).exists()

            if not existing_warning:
                ServiceSuspensionLog.objects.create(
                    organization=organization,
                    service_account=service_account,
                    customer=service_account.customer,
                    event_type=ServiceSuspensionLog.EventType.WARNING,
                    trigger_type=ServiceSuspensionLog.TriggerType.SYSTEM_AUTOMATED,
                    previous_status=service_account.status,
                    new_status=service_account.status,
                    outstanding_amount=Decimal(item["total_outstanding"]),
                    reason=f"Pre-suspension warning notice. Service will be suspended on {item['expected_suspension_date']}",
                )

                try:
                    dispatch_notification_event(
                        organization=organization,
                        customer=service_account.customer,
                        event_type=NotificationEvent.SUSPENSION_WARNING,
                        context={
                            "service_number": service_account.service_number,
                            "package_name": service_account.internet_package.name,
                            "outstanding_amount": item["total_outstanding"],
                            "suspension_date": item["expected_suspension_date"],
                        },
                    )
                except Exception as exc:
                    logger.exception("Failed to send suspension warning for %s", service_account.service_number)

                warning_count += 1

    return {
        "status": "COMPLETED",
        "total_evaluated": len(evaluated_items),
        "suspended_count": suspended_count,
        "warning_count": warning_count,
        "exempt_count": exempt_count,
    }


def get_suspension_dashboard_metrics(organization) -> dict:
    """
    Computes real-time KPI metrics for the Suspensions & Restorations dashboard.
    """
    policy = get_or_create_suspension_policy(organization)
    today = timezone.now().date()

    currently_suspended = ServiceAccount.objects.filter(
        organization=organization,
        status=ServiceAccount.Status.SUSPENDED_NON_PAYMENT,
    ).count()

    eligibility_list = evaluate_suspension_eligibility(organization)
    eligible_count = sum(1 for item in eligibility_list if item["is_eligible_for_suspension"])
    warning_eligible_count = sum(1 for item in eligibility_list if item["is_warning_eligible"])
    ptp_exempt_count = sum(1 for item in eligibility_list if item["is_ptp_exempt"])

    restored_today = ServiceSuspensionLog.objects.filter(
        organization=organization,
        event_type=ServiceSuspensionLog.EventType.RESTORATION,
        created_at__date=today,
    ).count()

    warnings_sent_today = ServiceSuspensionLog.objects.filter(
        organization=organization,
        event_type=ServiceSuspensionLog.EventType.WARNING,
        created_at__date=today,
    ).count()

    return {
        "currently_suspended": currently_suspended,
        "eligible_for_suspension": eligible_count,
        "warning_eligible": warning_eligible_count,
        "ptp_exempt_count": ptp_exempt_count,
        "restored_today": restored_today,
        "warnings_sent_today": warnings_sent_today,
        "auto_suspension_enabled": policy.auto_suspension_enabled,
        "auto_restoration_enabled": policy.auto_restoration_enabled,
        "restore_on_partial_payment": policy.restore_on_partial_payment,
        "grace_period_days": policy.grace_period_days,
        "suspension_threshold_days": policy.suspension_threshold_days,
        "minimum_outstanding_amount": str(policy.minimum_outstanding_amount),
    }
