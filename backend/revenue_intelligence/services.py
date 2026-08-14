from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
)
from tenancy.models import Organization


def get_revenue_overview(
    *,
    organization: Organization,
):
    invoiced_amount = (
        InvoiceLine.objects
        .for_organization(organization)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    collected_amount = (
        PaymentAllocation.objects
        .for_organization(organization)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    recorded_payments = (
        Payment.objects
        .for_organization(organization)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    unallocated_payments = (
        recorded_payments - collected_amount
    )

    return {
        "invoiced_amount": invoiced_amount,
        "collected_amount": collected_amount,
        "outstanding_receivables": (
            invoiced_amount - collected_amount
        ),
        "recorded_payments": recorded_payments,
        "allocated_payments": collected_amount,
        "unallocated_payments": unallocated_payments,
    }


def get_collections_by_period(
    *,
    organization: Organization,
):
    payment_intake = (
        Payment.objects
        .for_organization(organization)
        .annotate(period=TruncMonth("paid_at"))
        .values("period")
        .annotate(
            amount=Sum("amount"),
            payment_count=Count("id"),
        )
        .order_by("period")
    )

    allocated_collections = (
        PaymentAllocation.objects
        .for_organization(organization)
        .annotate(period=TruncMonth("payment__paid_at"))
        .values("period")
        .annotate(
            amount=Sum("amount"),
            allocation_count=Count("id"),
        )
        .order_by("period")
    )

    intake_by_period = {
        item["period"]: item
        for item in payment_intake
    }

    allocated_by_period = {
        item["period"]: item
        for item in allocated_collections
    }

    periods = sorted(
        set(intake_by_period) | set(allocated_by_period)
    )

    return [
        {
            "period": period,
            "payment_intake_amount": (
                intake_by_period.get(
                    period,
                    {},
                ).get(
                    "amount",
                    Decimal("0.00"),
                )
            ),
            "payment_count": (
                intake_by_period.get(
                    period,
                    {},
                ).get(
                    "payment_count",
                    0,
                )
            ),
            "allocated_collection_amount": (
                allocated_by_period.get(
                    period,
                    {},
                ).get(
                    "amount",
                    Decimal("0.00"),
                )
            ),
            "allocation_count": (
                allocated_by_period.get(
                    period,
                    {},
                ).get(
                    "allocation_count",
                    0,
                )
            ),
        }
        for period in periods
    ]


def get_payment_method_mix(
    *,
    organization: Organization,
):
    payment_rows = (
        Payment.objects
        .for_organization(organization)
        .values("payment_method")
        .annotate(
            amount=Sum("amount"),
            payment_count=Count("id"),
        )
        .order_by("payment_method")
    )

    return list(payment_rows)


def get_outstanding_receivables(
    *,
    organization: Organization,
):
    invoices = (
        Invoice.objects
        .for_organization(organization)
        .select_related(
            "service_account",
            "service_account__customer",
        )
        .prefetch_related(
            "lines",
            "allocations",
        )
        .order_by("due_date", "issue_date")
    )

    receivables = []

    for invoice in invoices:
        total_amount = invoice.total_amount
        paid_amount = invoice.paid_amount
        outstanding_amount = total_amount - paid_amount

        if outstanding_amount <= Decimal("0.00"):
            continue

        customer = invoice.service_account.customer

        receivables.append(
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "service_account_id": invoice.service_account.id,
                "service_number": (
                    invoice.service_account.service_number
                ),
                "customer_id": customer.id,
                "customer_number": customer.customer_number,
                "customer_name": (
                    f"{customer.first_name} "
                    f"{customer.last_name}"
                ).strip(),
                "status": invoice.status,
                "issue_date": invoice.issue_date,
                "due_date": invoice.due_date,
                "total_amount": total_amount,
                "paid_amount": paid_amount,
                "outstanding_amount": outstanding_amount,
            }
        )

    return receivables