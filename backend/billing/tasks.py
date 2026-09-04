import logging
from datetime import date
from decimal import Decimal
from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction

from billing.models import Invoice, PromiseToPay
from billing.services import BillingDomainError, generate_monthly_invoices
from tenancy.models import Organization
from tenancy.services import record_audit_log

logger = logging.getLogger("nexora.billing.tasks")
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_monthly_invoices_task(
    self,
    organization_id: str,
    billing_year: int,
    billing_month: int,
    actor_id: str | None = None,
):
    """
    Asynchronous background job for monthly invoice generation.
    Strictly tenant-scoped, idempotent, chunked, and reuses the authoritative
    billing service engine.
    """
    logger.info(
        f"Starting monthly billing task for Org={organization_id}, "
        f"Period={billing_year}-{billing_month:02d}"
    )

    try:
        organization = Organization.objects.get(id=organization_id, is_active=True)
    except Organization.DoesNotExist:
        logger.error(f"Monthly billing failed: Active organization {organization_id} not found.")
        return {"error": "Active organization not found."}

    actor = None
    if actor_id:
        actor = User.objects.filter(id=actor_id).first()

    try:
        result = generate_monthly_invoices(
            organization=organization,
            actor=actor,
            billing_year=billing_year,
            billing_month=billing_month,
        )

        record_audit_log(
            organization=organization,
            actor=actor,
            action="MONTHLY_BILLING_TASK_COMPLETED",
            resource_type="MonthlyBillingRun",
            resource_id=f"{billing_year}-{billing_month:02d}",
            metadata={
                "eligible_services": result.eligible_services,
                "generated_invoices": result.generated_invoices,
                "skipped_existing_invoices": result.skipped_existing_invoices,
                "failed_services": result.failed_services,
            },
        )

        return {
            "organization_id": str(organization.id),
            "billing_year": result.billing_year,
            "billing_month": result.billing_month,
            "eligible_services": result.eligible_services,
            "generated_invoices": result.generated_invoices,
            "skipped_existing_invoices": result.skipped_existing_invoices,
            "failed_services": result.failed_services,
        }
    except BillingDomainError as exc:
        logger.error(f"Monthly billing domain error for Org {organization_id}: {exc}")
        return {"error": str(exc)}
    except Exception as exc:
        logger.exception(f"Unexpected failure during monthly billing for Org {organization_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def scan_overdue_invoices_task(organization_id: str | None = None):
    """
    Scheduled task scanning for unpaid invoices past their due_date.
    Idempotent and strictly tenant-scoped.
    """
    today = date.today()
    org_queryset = Organization.objects.filter(is_active=True)
    if organization_id:
        org_queryset = org_queryset.filter(id=organization_id)

    total_scanned = 0
    total_overdue = 0

    for org in org_queryset:
        overdue_invoices = (
            Invoice.objects
            .filter(
                organization=org,
                due_date__lt=today,
            )
            .exclude(status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED])
        )

        count = overdue_invoices.count()
        total_scanned += count
        if count > 0:
            total_overdue += count
            logger.info(f"Org {org.code} has {count} overdue invoices as of {today}.")

    return {
        "scanned_organizations": org_queryset.count(),
        "total_overdue_invoices": total_overdue,
    }


@shared_task
def scan_ptp_breaches_task(organization_id: str | None = None):
    """
    Scheduled daily scanner evaluating active / pending PromiseToPay records.
    Transitions expired unpaid promises to BROKEN (breached) and fulfilled ones to FULFILLED.
    Idempotent and tenant-scoped.
    """
    today = date.today()
    org_queryset = Organization.objects.filter(is_active=True)
    if organization_id:
        org_queryset = org_queryset.filter(id=organization_id)

    fulfilled_count = 0
    broken_count = 0

    for org in org_queryset:
        active_promises = (
            PromiseToPay.objects
            .filter(
                organization=org,
                status=PromiseToPay.Status.PENDING,
            )
            .select_related("invoice")
        )

        for promise in active_promises:
            invoice = promise.invoice
            if invoice and invoice.status == Invoice.Status.PAID:
                with transaction.atomic():
                    promise.status = PromiseToPay.Status.FULFILLED
                    promise.notes = (promise.notes + "\nAuto-fulfilled by scheduled PTP scanner.").strip()
                    promise.save(update_fields=["status", "notes", "updated_at"])
                    fulfilled_count += 1

                    record_audit_log(
                        organization=org,
                        actor=None,
                        action="PTP_AUTO_FULFILLED",
                        resource_type="PromiseToPay",
                        resource_id=str(promise.id),
                        metadata={"promise_number": promise.promise_number},
                    )
            elif promise.deadline < today:
                with transaction.atomic():
                    promise.status = PromiseToPay.Status.BROKEN
                    promise.failure_reason = "Deadline passed without required payment."
                    promise.notes = (promise.notes + "\nAuto-breached by scheduled PTP scanner.").strip()
                    promise.save(update_fields=["status", "failure_reason", "notes", "updated_at"])
                    broken_count += 1

                    record_audit_log(
                        organization=org,
                        actor=None,
                        action="PTP_AUTO_BREACHED",
                        resource_type="PromiseToPay",
                        resource_id=str(promise.id),
                        metadata={
                            "promise_number": promise.promise_number,
                            "deadline": str(promise.deadline),
                        },
                    )

    logger.info(f"PTP breach scan complete: {fulfilled_count} fulfilled, {broken_count} broken.")
    return {
        "fulfilled_count": fulfilled_count,
        "broken_count": broken_count,
    }
