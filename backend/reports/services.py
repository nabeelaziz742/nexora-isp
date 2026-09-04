import csv
import io
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import (
    Avg,
    Case,
    Count,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from accounting.models import (
    Account,
    DealerSettlement,
    DirectIncome,
    Expense,
    FinancialPeriod,
    FundTransfer,
    JournalEntry,
    JournalLine,
)
from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
    PromiseToPay,
    RecoveryAllocation,
)
from customers.models import (
    Area,
    City,
    Customer,
    Dealer,
    InternetPackage,
    ServiceAccount,
)
from inventory.models import DeviceAssignment, InventoryDevice
from support.models import Complaint, Incident
from tenancy.models import Organization


def _normalize_decimal(val) -> Decimal:
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"))
    try:
        return Decimal(str(val)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


# =========================================================================
# PRESERVED EXISTING DATA CLASSES & SERVICES (100% Backward Compatible)
# =========================================================================

@dataclass(frozen=True)
class SubscriberOverview:
    total_customers: int
    active_customers: int
    inactive_customers: int
    total_services: int
    active_services: int
    non_active_services: int
    customers_with_services: int
    customers_without_services: int
    total_packages: int
    active_packages: int


@dataclass(frozen=True)
class ServiceStatusDistributionItem:
    status: str
    service_count: int


@dataclass(frozen=True)
class PackageContributionItem:
    package_id: str
    package_code: str
    package_name: str
    download_speed_mbps: int
    upload_speed_mbps: int
    monthly_price: Decimal
    is_active: bool
    service_count: int
    active_service_count: int


@dataclass(frozen=True)
class PackageRevenueContextItem:
    package_id: str
    package_code: str
    package_name: str
    service_count: int
    invoiced_amount: Decimal
    collected_amount: Decimal
    outstanding_amount: Decimal


def get_subscriber_overview(*, organization: Organization) -> SubscriberOverview:
    customers = Customer.objects.for_organization(organization)
    services = ServiceAccount.objects.for_organization(organization)
    packages = InternetPackage.objects.for_organization(organization)

    total_customers = customers.count()
    active_customers = customers.filter(is_active=True).count()
    total_services = services.count()
    active_services = services.filter(status=ServiceAccount.Status.ACTIVE).count()
    customers_with_services = customers.filter(service_accounts__organization=organization).distinct().count()

    return SubscriberOverview(
        total_customers=total_customers,
        active_customers=active_customers,
        inactive_customers=(total_customers - active_customers),
        total_services=total_services,
        active_services=active_services,
        non_active_services=(total_services - active_services),
        customers_with_services=customers_with_services,
        customers_without_services=(total_customers - customers_with_services),
        total_packages=packages.count(),
        active_packages=packages.filter(is_active=True).count(),
    )


def get_service_status_distribution(*, organization: Organization) -> list[ServiceStatusDistributionItem]:
    services = ServiceAccount.objects.for_organization(organization)
    status_counts = {
        row["status"]: row["service_count"]
        for row in services.values("status").annotate(service_count=Count("id"))
    }
    return [
        ServiceStatusDistributionItem(status=status, service_count=status_counts.get(status, 0))
        for status, _label in ServiceAccount.Status.choices
    ]


def get_package_contribution(*, organization: Organization) -> list[PackageContributionItem]:
    packages = (
        InternetPackage.objects
        .for_organization(organization)
        .annotate(
            service_count=Count("service_accounts", distinct=True),
            active_service_count=Count(
                "service_accounts",
                filter=models.Q(
                    service_accounts__status=ServiceAccount.Status.ACTIVE,
                    service_accounts__organization=organization,
                ),
                distinct=True,
            ),
        )
        .order_by("-service_count", "monthly_price", "name")
    )
    return [
        PackageContributionItem(
            package_id=str(package.id),
            package_code=package.code,
            package_name=package.name,
            download_speed_mbps=package.download_speed_mbps,
            upload_speed_mbps=package.upload_speed_mbps,
            monthly_price=package.monthly_price,
            is_active=package.is_active,
            service_count=package.service_count,
            active_service_count=package.active_service_count,
        )
        for package in packages
    ]


def get_package_revenue_context(*, organization: Organization) -> list[PackageRevenueContextItem]:
    packages = (
        InternetPackage.objects
        .for_organization(organization)
        .annotate(service_count=Count("service_accounts", distinct=True))
        .order_by("name")
    )
    invoice_totals = {
        str(row["invoice__service_account__internet_package_id"]): (row["invoiced_amount"] or Decimal("0.00"))
        for row in InvoiceLine.objects.for_organization(organization)
        .values("invoice__service_account__internet_package_id")
        .annotate(invoiced_amount=Sum("amount"))
    }
    collection_totals = {
        str(row["invoice__service_account__internet_package_id"]): (row["collected_amount"] or Decimal("0.00"))
        for row in PaymentAllocation.objects.for_organization(organization)
        .values("invoice__service_account__internet_package_id")
        .annotate(collected_amount=Sum("amount"))
    }
    result = []
    for package in packages:
        package_id = str(package.id)
        invoiced_amount = invoice_totals.get(package_id, Decimal("0.00"))
        collected_amount = collection_totals.get(package_id, Decimal("0.00"))
        result.append(
            PackageRevenueContextItem(
                package_id=package_id,
                package_code=package.code,
                package_name=package.name,
                service_count=package.service_count,
                invoiced_amount=invoiced_amount,
                collected_amount=collected_amount,
                outstanding_amount=(invoiced_amount - collected_amount),
            )
        )
    return sorted(result, key=lambda item: (-item.invoiced_amount, item.package_name))


# =========================================================================
# PHASE 2: CUSTOMER, BILLING & COLLECTIONS REPORTS
# =========================================================================

def get_customer_collections_report(
    *,
    organization: Organization,
    start_date: date | None = None,
    end_date: date | None = None,
    collector_id: str | None = None,
    payment_method: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    """
    Authoritative Collections Register:
    Source: billing.Payment & billing.PaymentAllocation
    Formula: Total Collections = Sum(Payment.amount where is_reversed=False)
    """
    qs = (
        Payment.objects
        .for_organization(organization)
        .filter(is_reversed=False)
        .select_related(
            "service_account",
            "service_account__customer",
            "service_account__internet_package",
            "received_by",
        )
        .order_by("-paid_at")
    )

    if start_date:
        qs = qs.filter(paid_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(paid_at__date__lte=end_date)
    if collector_id:
        qs = qs.filter(received_by_id=collector_id)
    if payment_method and payment_method != "ALL":
        qs = qs.filter(payment_method=payment_method)
    if search:
        s = search.strip()
        qs = qs.filter(
            Q(payment_number__icontains=s)
            | Q(service_account__service_number__icontains=s)
            | Q(service_account__customer__customer_number__icontains=s)
            | Q(service_account__customer__first_name__icontains=s)
            | Q(service_account__customer__last_name__icontains=s)
            | Q(reference__icontains=s)
        )

    totals = qs.aggregate(
        total_collected=Coalesce(Sum("amount"), Decimal("0.00")),
        payment_count=Count("id"),
    )

    # Method breakdown
    method_mix = list(
        qs.values("payment_method")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("payment_method")
    )

    total_records = totals["payment_count"]
    total_pages = max(1, math.ceil(total_records / page_size))
    offset = (page - 1) * page_size
    page_items = qs[offset : offset + page_size]

    records = [
        {
            "id": str(p.id),
            "payment_number": p.payment_number,
            "paid_at": p.paid_at.isoformat(),
            "customer_number": p.service_account.customer.customer_number,
            "customer_name": p.service_account.customer.full_name,
            "service_number": p.service_account.service_number,
            "package_name": p.service_account.internet_package.name,
            "payment_method": p.payment_method,
            "amount": str(_normalize_decimal(p.amount)),
            "reference": p.reference or "-",
            "received_by_name": p.received_by.get_full_name() if p.received_by else "System / Online",
        }
        for p in page_items
    ]

    return {
        "summary": {
            "total_collected": str(_normalize_decimal(totals["total_collected"])),
            "payment_count": total_records,
            "method_breakdown": [
                {
                    "method": row["payment_method"],
                    "total": str(_normalize_decimal(row["total"])),
                    "count": row["count"],
                }
                for row in method_mix
            ],
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
        },
        "records": records,
    }


def get_defaulters_aging_report(
    *,
    organization: Organization,
    aging_bucket: str | None = None,
    area_id: str | None = None,
    package_id: str | None = None,
    dealer_id: str | None = None,
    page: int = 1,
    page_size: int = 25,
    as_of_date: date | None = None,
) -> dict:
    """
    Authoritative Defaulters & Receivables Aging:
    Source: billing.Invoice & billing.PaymentAllocation
    Formula: Outstanding = Invoice.total_amount - Sum(Allocations) where status != CANCELLED
    Aging Buckets relative to due_date: 0-30, 31-60, 61-90, 90+ days
    """
    as_of = as_of_date or timezone.now().date()

    qs = (
        Invoice.objects
        .for_organization(organization)
        .filter(status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID])
        .select_related(
            "service_account",
            "service_account__customer",
            "service_account__customer__dealer",
            "service_account__internet_package",
        )
        .order_by("due_date")
    )

    if area_id and area_id != "ALL":
        qs = qs.filter(service_account__customer__area=area_id)
    if package_id and package_id != "ALL":
        qs = qs.filter(service_account__internet_package_id=package_id)
    if dealer_id and dealer_id != "ALL":
        qs = qs.filter(service_account__customer__dealer_id=dealer_id)

    # Calculate aging per invoice
    records_all = []
    bucket_sums = {
        "0-30": Decimal("0.00"),
        "31-60": Decimal("0.00"),
        "61-90": Decimal("0.00"),
        "90+": Decimal("0.00"),
    }
    total_exposure = Decimal("0.00")

    for inv in qs:
        outstanding = inv.outstanding_amount
        if outstanding <= Decimal("0.00"):
            continue

        days_overdue = max(0, (as_of - inv.due_date).days)
        if days_overdue <= 30:
            bucket = "0-30"
        elif days_overdue <= 60:
            bucket = "31-60"
        elif days_overdue <= 90:
            bucket = "61-90"
        else:
            bucket = "90+"

        bucket_sums[bucket] += outstanding
        total_exposure += outstanding

        if aging_bucket and aging_bucket != "ALL" and bucket != aging_bucket:
            continue

        records_all.append({
            "invoice_id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "due_date": inv.due_date.isoformat(),
            "days_overdue": days_overdue,
            "aging_bucket": bucket,
            "customer_id": str(inv.service_account.customer.id),
            "customer_number": inv.service_account.customer.customer_number,
            "customer_name": inv.service_account.customer.full_name,
            "phone": inv.service_account.customer.phone,
            "area": inv.service_account.customer.area or "-",
            "service_number": inv.service_account.service_number,
            "package_name": inv.service_account.internet_package.name,
            "dealer_name": inv.service_account.customer.dealer.name if inv.service_account.customer.dealer else "Direct",
            "total_invoiced": str(_normalize_decimal(inv.total_amount)),
            "paid_amount": str(_normalize_decimal(inv.paid_amount)),
            "outstanding_amount": str(_normalize_decimal(outstanding)),
        })

    total_records = len(records_all)
    total_pages = max(1, math.ceil(total_records / page_size))
    offset = (page - 1) * page_size
    paged_records = records_all[offset : offset + page_size]

    return {
        "summary": {
            "total_exposure": str(_normalize_decimal(total_exposure)),
            "total_defaulters_count": total_records,
            "aging_buckets": {
                k: str(_normalize_decimal(v)) for k, v in bucket_sums.items()
            },
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
        },
        "records": paged_records,
    }


def get_customer_master_report(
    *,
    organization: Organization,
    status: str | None = None,
    area_id: str | None = None,
    package_id: str | None = None,
    dealer_id: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    """
    Authoritative Subscriber Master Directory:
    Source: customers.Customer & customers.ServiceAccount & customers.InternetPackage
    """
    qs = (
        ServiceAccount.objects
        .for_organization(organization)
        .select_related(
            "customer",
            "customer__dealer",
            "internet_package",
            "network_assignment",
            "network_assignment__network_node",
        )
        .order_by("customer__customer_number")
    )

    if status and status != "ALL":
        qs = qs.filter(status=status)
    if area_id and area_id != "ALL":
        qs = qs.filter(customer__area=area_id)
    if package_id and package_id != "ALL":
        qs = qs.filter(internet_package_id=package_id)
    if dealer_id and dealer_id != "ALL":
        qs = qs.filter(customer__dealer_id=dealer_id)
    if search:
        s = search.strip()
        qs = qs.filter(
            Q(customer__customer_number__icontains=s)
            | Q(customer__first_name__icontains=s)
            | Q(customer__last_name__icontains=s)
            | Q(customer__phone__icontains=s)
            | Q(service_number__icontains=s)
        )

    total_records = qs.count()
    total_pages = max(1, math.ceil(total_records / page_size))
    offset = (page - 1) * page_size
    page_items = qs[offset : offset + page_size]

    records = []
    for srv in page_items:
        net = getattr(srv, "network_assignment", None)
        records.append({
            "service_id": str(srv.id),
            "service_number": srv.service_number,
            "customer_number": srv.customer.customer_number,
            "customer_name": srv.customer.full_name,
            "phone": srv.customer.phone,
            "address": srv.customer.address_line,
            "area": srv.customer.area or "-",
            "city": srv.customer.city or "-",
            "package_name": srv.internet_package.name,
            "speed_mbps": f"{srv.internet_package.download_speed_mbps} / {srv.internet_package.upload_speed_mbps}",
            "monthly_price": str(_normalize_decimal(srv.internet_package.monthly_price)),
            "status": srv.status,
            "dealer_name": srv.customer.dealer.name if srv.customer.dealer else "Direct",
            "ip_address": net.ip_address if net and net.ip_address else "-",
            "node_name": net.network_node.name if net and net.network_node else "-",
            "created_at": srv.created_at.strftime("%Y-%m-%d"),
        })

    return {
        "summary": {
            "total_subscribers": total_records,
            "active_count": qs.filter(status=ServiceAccount.Status.ACTIVE).count(),
            "suspended_count": qs.filter(status=ServiceAccount.Status.SUSPENDED_NON_PAYMENT).count(),
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
        },
        "records": records,
    }


def get_customer_growth_churn_report(
    *,
    organization: Organization,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """
    Subscriber Growth & Churn Analysis:
    Formula:
      Net Growth = New Activations - Deactivations
      Churn Rate % = (Deactivations / Base) * 100
    """
    now = timezone.now().date()
    s_date = start_date or (now - timedelta(days=180))
    e_date = end_date or now

    services = ServiceAccount.objects.for_organization(organization)

    # Monthly intervals
    intervals = []
    curr = s_date.replace(day=1)
    while curr <= e_date:
        import calendar
        last_day = calendar.monthrange(curr.year, curr.month)[1]
        m_start = curr
        m_end = date(curr.year, curr.month, last_day)

        new_count = services.filter(created_at__date__gte=m_start, created_at__date__lte=m_end).count()
        deact_count = services.filter(
            status=ServiceAccount.Status.SUSPENDED_NON_PAYMENT,
            updated_at__date__gte=m_start,
            updated_at__date__lte=m_end,
        ).count()
        active_at_end = services.filter(created_at__date__lte=m_end, status=ServiceAccount.Status.ACTIVE).count()

        base = max(1, active_at_end + deact_count)
        churn_pct = round((deact_count / base) * 100, 2)
        net_growth = new_count - deact_count

        intervals.append({
            "period": curr.strftime("%Y-%m"),
            "new_activations": new_count,
            "deactivations": deact_count,
            "net_growth": net_growth,
            "churn_rate_percent": churn_pct,
            "active_subscribers_end": active_at_end,
        })

        if curr.month == 12:
            curr = date(curr.year + 1, 1, 1)
        else:
            curr = date(curr.year, curr.month + 1, 1)

    return {
        "intervals": intervals,
        "total_new": sum(i["new_activations"] for i in intervals),
        "total_churned": sum(i["deactivations"] for i in intervals),
        "net_overall_growth": sum(i["net_growth"] for i in intervals),
    }


def get_area_revenue_density_report(*, organization: Organization) -> list[dict]:
    """
    Area-wise subscriber density and revenue collection efficiency.
    Formula: Collection Rate % = (Collected / Invoiced) * 100
    """
    areas = Area.objects.for_organization(organization).select_related("city")
    result = []

    for area in areas:
        active_subs = ServiceAccount.objects.for_organization(organization).filter(
            customer__area=area.name,
            status=ServiceAccount.Status.ACTIVE,
        ).count()

        invoiced = (
            InvoiceLine.objects.for_organization(organization)
            .filter(invoice__service_account__customer__area=area.name)
            .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        )

        collected = (
            PaymentAllocation.objects.for_organization(organization)
            .filter(invoice__service_account__customer__area=area.name)
            .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        )

        eff = round((float(collected) / float(invoiced) * 100), 1) if invoiced > 0 else 100.0

        result.append({
            "city_name": area.city.name if area.city else "Default",
            "area_name": area.name,
            "active_subscribers": active_subs,
            "invoiced_amount": str(_normalize_decimal(invoiced)),
            "collected_amount": str(_normalize_decimal(collected)),
            "outstanding_amount": str(_normalize_decimal(invoiced - collected)),
            "collection_rate_percent": eff,
        })

    return sorted(result, key=lambda x: -float(x["invoiced_amount"]))


def get_cashier_shift_close_report(
    *,
    organization: Organization,
    collector_id: str,
    shift_date: date | None = None,
) -> dict:
    """
    Daily Cashier / Collector Shift Reconciliation.
    """
    target_date = shift_date or timezone.now().date()

    payments = (
        Payment.objects
        .for_organization(organization)
        .filter(received_by_id=collector_id, paid_at__date=target_date, is_reversed=False)
        .select_related("service_account", "service_account__customer")
        .order_by("paid_at")
    )

    by_method = {}
    total_intake = Decimal("0.00")

    for p in payments:
        amt = p.amount
        total_intake += amt
        by_method[p.payment_method] = by_method.get(p.payment_method, Decimal("0.00")) + amt

    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        cashier = User.objects.get(id=collector_id)
        cashier_name = cashier.get_full_name() or cashier.username
    except Exception:
        cashier_name = "Unknown Cashier"

    return {
        "cashier_name": cashier_name,
        "shift_date": target_date.isoformat(),
        "total_intake": str(_normalize_decimal(total_intake)),
        "transaction_count": payments.count(),
        "method_breakdown": {
            k: str(_normalize_decimal(v)) for k, v in by_method.items()
        },
        "transactions": [
            {
                "payment_number": p.payment_number,
                "time": p.paid_at.strftime("%H:%M:%S"),
                "customer": p.service_account.customer.full_name,
                "service_number": p.service_account.service_number,
                "amount": str(_normalize_decimal(p.amount)),
                "method": p.payment_method,
                "reference": p.reference or "-",
            }
            for p in payments
        ],
    }


def get_invoice_register_report(
    *,
    organization: Organization,
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    """
    Authoritative Invoice Register:
    Source: billing.Invoice & billing.InvoiceLine
    """
    qs = (
        Invoice.objects
        .for_organization(organization)
        .select_related(
            "service_account",
            "service_account__customer",
            "service_account__internet_package",
        )
        .prefetch_related("lines", "allocations")
        .order_by("-issue_date", "-created_at")
    )

    if status and status != "ALL":
        qs = qs.filter(status=status)
    if start_date:
        qs = qs.filter(issue_date__gte=start_date)
    if end_date:
        qs = qs.filter(issue_date__lte=end_date)
    if search:
        s = search.strip()
        qs = qs.filter(
            Q(invoice_number__icontains=s)
            | Q(service_account__service_number__icontains=s)
            | Q(service_account__customer__customer_number__icontains=s)
            | Q(service_account__customer__first_name__icontains=s)
            | Q(service_account__customer__last_name__icontains=s)
        )

    total_records = qs.count()
    total_pages = max(1, math.ceil(total_records / page_size))
    offset = (page - 1) * page_size
    paged_items = qs[offset : offset + page_size]

    records = []
    for inv in paged_items:
        records.append({
            "id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "issue_date": inv.issue_date.isoformat(),
            "due_date": inv.due_date.isoformat(),
            "period": f"{inv.billing_period_start} to {inv.billing_period_end}",
            "customer_number": inv.service_account.customer.customer_number,
            "customer_name": inv.service_account.customer.full_name,
            "service_number": inv.service_account.service_number,
            "package_name": inv.service_account.internet_package.name,
            "total_amount": str(_normalize_decimal(inv.total_amount)),
            "paid_amount": str(_normalize_decimal(inv.paid_amount)),
            "outstanding_amount": str(_normalize_decimal(inv.outstanding_amount)),
            "status": inv.status,
        })

    return {
        "summary": {
            "total_invoices_count": total_records,
            "total_billed": str(_normalize_decimal(qs.aggregate(total=Coalesce(Sum("lines__amount"), Decimal("0.00")))["total"])),
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
        },
        "records": records,
    }


# =========================================================================
# PHASE 3: RECOVERY, PROMISES & DEALER 360 REPORTS
# =========================================================================

def get_promise_to_pay_report(
    *,
    organization: Organization,
    start_date: date | None = None,
    end_date: date | None = None,
    status: str | None = None,
    staff_id: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    """
    Promise to Pay Performance:
    Formula: Fulfillment Rate % = (Fulfilled / Total Matured) * 100
    """
    qs = (
        PromiseToPay.objects
        .for_organization(organization)
        .select_related("customer", "service_account", "created_by", "approved_by")
        .order_by("-deadline")
    )

    if start_date:
        qs = qs.filter(promise_date__gte=start_date)
    if end_date:
        qs = qs.filter(promise_date__lte=end_date)
    if status and status != "ALL":
        qs = qs.filter(status=status)
    if staff_id:
        qs = qs.filter(created_by_id=staff_id)

    total_records = qs.count()
    fulfilled_count = qs.filter(status=PromiseToPay.Status.FULFILLED).count()
    broken_count = qs.filter(status=PromiseToPay.Status.BROKEN).count()
    active_count = qs.filter(status=PromiseToPay.Status.ACTIVE).count()

    total_promised = qs.aggregate(t=Coalesce(Sum("promised_amount"), Decimal("0.00")))["t"]

    total_pages = max(1, math.ceil(total_records / page_size))
    offset = (page - 1) * page_size
    paged_items = qs[offset : offset + page_size]

    records = [
        {
            "id": str(p.id),
            "promise_number": p.promise_number,
            "customer_name": p.customer.full_name,
            "service_number": p.service_account.service_number,
            "promised_amount": str(_normalize_decimal(p.promised_amount)),
            "outstanding_amount": str(_normalize_decimal(p.outstanding_amount)),
            "promise_date": p.promise_date.isoformat(),
            "deadline": p.deadline.isoformat(),
            "status": p.status,
            "created_by": p.created_by.get_full_name() if p.created_by else "Staff",
            "completed_at": p.completed_at.isoformat() if p.completed_at else "-",
        }
        for p in paged_items
    ]

    matured = fulfilled_count + broken_count
    fulfillment_rate = round((fulfilled_count / matured * 100), 1) if matured > 0 else 100.0

    return {
        "summary": {
            "total_promises": total_records,
            "fulfilled_count": fulfilled_count,
            "broken_count": broken_count,
            "active_count": active_count,
            "fulfillment_rate_percent": fulfillment_rate,
            "total_promised_amount": str(_normalize_decimal(total_promised)),
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
        },
        "records": records,
    }


def get_field_recovery_scorecard_report(
    *,
    organization: Organization,
    start_date: date | None = None,
    end_date: date | None = None,
    staff_id: str | None = None,
) -> list[dict]:
    """
    Field Recovery Officer Scorecard:
    Formula: Recovery Rate % = (Recovered Amount / Allocated Amount) * 100
    """
    qs = (
        RecoveryAllocation.objects
        .for_organization(organization)
        .select_related("assigned_staff", "customer")
    )

    if start_date:
        qs = qs.filter(assigned_date__gte=start_date)
    if end_date:
        qs = qs.filter(assigned_date__lte=end_date)
    if staff_id:
        qs = qs.filter(assigned_staff_id=staff_id)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    officers = (
        User.objects.filter(assigned_recoveries__organization=organization)
        .distinct()
    )

    result = []
    for officer in officers:
        o_qs = qs.filter(assigned_staff=officer)
        total_allocations = o_qs.count()
        if total_allocations == 0:
            continue

        allocated_amount = o_qs.aggregate(t=Coalesce(Sum("outstanding_amount"), Decimal("0.00")))["t"]
        completed_qs = o_qs.filter(status__in=[RecoveryAllocation.Status.COMPLETED, RecoveryAllocation.Status.PAYMENT_COLLECTED])
        completed_count = completed_qs.count()
        recovered_amount = completed_qs.aggregate(t=Coalesce(Sum("outstanding_amount"), Decimal("0.00")))["t"]

        rec_rate = round((float(recovered_amount) / float(allocated_amount) * 100), 1) if allocated_amount > 0 else 0.0

        result.append({
            "officer_id": str(officer.id),
            "officer_name": officer.get_full_name() or officer.username,
            "total_allocations": total_allocations,
            "completed_allocations": completed_count,
            "in_progress_count": o_qs.filter(status=RecoveryAllocation.Status.IN_PROGRESS).count(),
            "allocated_amount": str(_normalize_decimal(allocated_amount)),
            "recovered_amount": str(_normalize_decimal(recovered_amount)),
            "recovery_rate_percent": rec_rate,
        })

    return sorted(result, key=lambda x: -float(x["recovered_amount"]))


def get_dealer_360_performance_report(
    *,
    organization: Organization,
    start_date: date | None = None,
    end_date: date | None = None,
    dealer_id: str | None = None,
) -> list[dict]:
    """
    Dealer 360 Performance & Settlement Statement:
    Formula:
      Commission = Percentage of Collections OR Flat Rate * Active Subscribers
      Net ISP Margin = Subscriber Collections - Accrued Commission
    """
    dealers = Dealer.objects.for_organization(organization).select_related("assigned_area")
    if dealer_id and dealer_id != "ALL":
        dealers = dealers.filter(id=dealer_id)

    result = []
    for d in dealers:
        subscribers_qs = Customer.objects.filter(organization=organization, dealer=d)
        total_subscribers = subscribers_qs.count()
        active_subscribers = ServiceAccount.objects.filter(
            organization=organization,
            customer__dealer=d,
            status=ServiceAccount.Status.ACTIVE,
        ).count()

        invoices_qs = Invoice.objects.filter(organization=organization, service_account__customer__dealer=d)
        payments_qs = Payment.objects.filter(organization=organization, service_account__customer__dealer=d, is_reversed=False)
        settlements_qs = DealerSettlement.objects.filter(organization=organization, dealer=d)

        if start_date:
            invoices_qs = invoices_qs.filter(issue_date__gte=start_date)
            payments_qs = payments_qs.filter(paid_at__date__gte=start_date)
            settlements_qs = settlements_qs.filter(settlement_date__gte=start_date)
        if end_date:
            invoices_qs = invoices_qs.filter(issue_date__lte=end_date)
            payments_qs = payments_qs.filter(paid_at__date__lte=end_date)
            settlements_qs = settlements_qs.filter(settlement_date__lte=end_date)

        invoiced = invoices_qs.aggregate(t=Coalesce(Sum("lines__amount"), Decimal("0.00")))["t"]
        collected = payments_qs.aggregate(t=Coalesce(Sum("amount"), Decimal("0.00")))["t"]

        # Commission Calculation
        if d.commission_type == Dealer.CommissionType.PERCENTAGE:
            rate = d.commission_rate_percentage or Decimal("0.00")
            commission_accrued = (rate / Decimal("100.00")) * collected
        else:
            flat_rate = d.commission_rate_percentage or Decimal("0.00")
            commission_accrued = flat_rate * Decimal(str(active_subscribers))

        commission_settled = settlements_qs.aggregate(t=Coalesce(Sum("amount"), Decimal("0.00")))["t"]
        net_isp_margin = collected - commission_accrued

        result.append({
            "dealer_id": str(d.id),
            "dealer_code": d.dealer_code,
            "dealer_name": d.name,
            "area_name": d.assigned_area.name if d.assigned_area else (d.area or "-"),
            "commission_type": d.commission_type,
            "commission_rate": str(d.commission_rate_percentage),
            "total_subscribers": total_subscribers,
            "active_subscribers": active_subscribers,
            "invoiced_amount": str(_normalize_decimal(invoiced)),
            "collected_amount": str(_normalize_decimal(collected)),
            "commission_accrued": str(_normalize_decimal(commission_accrued)),
            "commission_settled": str(_normalize_decimal(commission_settled)),
            "commission_outstanding": str(_normalize_decimal(max(Decimal("0.00"), commission_accrued - commission_settled))),
            "net_isp_margin": str(_normalize_decimal(net_isp_margin)),
        })

    return sorted(result, key=lambda x: -float(x["collected_amount"]))


# =========================================================================
# PHASE 4: FORMAL FINANCIAL STATEMENTS (Consuming Batch 10 GL)
# =========================================================================

def get_profit_and_loss_statement(
    *,
    organization: Organization,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """
    Formal Income Statement (Profit & Loss):
    Source: accounting.Account & accounting.JournalLine
    Formula:
      Operating Revenue (4000s) = Sum(Credits - Debits)
      Operating Expenses (5000s) = Sum(Debits - Credits)
      Net Operating Profit = Total Revenue - Total Expenses
    """
    s_date = start_date or date(timezone.now().year, 1, 1)
    e_date = end_date or timezone.now().date()

    lines = (
        JournalLine.objects
        .for_organization(organization)
        .filter(
            journal_entry__status=JournalEntry.Status.POSTED,
            journal_entry__date__gte=s_date,
            journal_entry__date__lte=e_date,
        )
        .select_related("account")
    )

    revenue_accounts = (
        Account.objects
        .for_organization(organization)
        .filter(category=Account.Category.REVENUE, is_active=True)
        .order_by("code")
    )
    expense_accounts = (
        Account.objects
        .for_organization(organization)
        .filter(category=Account.Category.EXPENSE, is_active=True)
        .order_by("code")
    )

    total_revenue = Decimal("0.00")
    rev_items = []
    for acc in revenue_accounts:
        acc_lines = lines.filter(account=acc)
        cr = acc_lines.aggregate(t=Coalesce(Sum("credit"), Decimal("0.00")))["t"]
        dr = acc_lines.aggregate(t=Coalesce(Sum("debit"), Decimal("0.00")))["t"]
        net = cr - dr
        total_revenue += net
        rev_items.append({
            "code": acc.code,
            "name": acc.name,
            "amount": str(_normalize_decimal(net)),
        })

    total_expenses = Decimal("0.00")
    exp_items = []
    for acc in expense_accounts:
        acc_lines = lines.filter(account=acc)
        dr = acc_lines.aggregate(t=Coalesce(Sum("debit"), Decimal("0.00")))["t"]
        cr = acc_lines.aggregate(t=Coalesce(Sum("credit"), Decimal("0.00")))["t"]
        net = dr - cr
        total_expenses += net
        exp_items.append({
            "code": acc.code,
            "name": acc.name,
            "amount": str(_normalize_decimal(net)),
        })

    net_profit = total_revenue - total_expenses
    profit_margin_pct = round((float(net_profit) / float(total_revenue) * 100), 2) if total_revenue > 0 else 0.0

    return {
        "period": {
            "start_date": s_date.isoformat(),
            "end_date": e_date.isoformat(),
        },
        "currency": organization.currency,
        "revenue_statement": {
            "accounts": rev_items,
            "total_revenue": str(_normalize_decimal(total_revenue)),
        },
        "expense_statement": {
            "accounts": exp_items,
            "total_expenses": str(_normalize_decimal(total_expenses)),
        },
        "net_income": {
            "net_profit_amount": str(_normalize_decimal(net_profit)),
            "profit_margin_percent": profit_margin_pct,
            "is_profitable": net_profit >= 0,
        },
    }


def get_balance_sheet_statement(
    *,
    organization: Organization,
    as_of_date: date | None = None,
) -> dict:
    """
    Formal Balance Sheet Statement:
    Source: accounting.Account & accounting.JournalLine
    Formula: Assets = Liabilities + Equity
    """
    as_of = as_of_date or timezone.now().date()

    lines = (
        JournalLine.objects
        .for_organization(organization)
        .filter(
            journal_entry__status=JournalEntry.Status.POSTED,
            journal_entry__date__lte=as_of,
        )
        .select_related("account")
    )

    accounts = Account.objects.for_organization(organization).filter(is_active=True).order_by("code")

    assets = []
    liabilities = []
    equity = []

    total_assets = Decimal("0.00")
    total_liabilities = Decimal("0.00")
    total_equity = Decimal("0.00")

    for acc in accounts:
        acc_lines = lines.filter(account=acc)
        dr = acc_lines.aggregate(t=Coalesce(Sum("debit"), Decimal("0.00")))["t"]
        cr = acc_lines.aggregate(t=Coalesce(Sum("credit"), Decimal("0.00")))["t"]

        if acc.category == Account.Category.ASSET:
            bal = dr - cr
            total_assets += bal
            assets.append({"code": acc.code, "name": acc.name, "amount": str(_normalize_decimal(bal))})
        elif acc.category == Account.Category.LIABILITY:
            bal = cr - dr
            total_liabilities += bal
            liabilities.append({"code": acc.code, "name": acc.name, "amount": str(_normalize_decimal(bal))})
        elif acc.category == Account.Category.EQUITY:
            bal = cr - dr
            total_equity += bal
            equity.append({"code": acc.code, "name": acc.name, "amount": str(_normalize_decimal(bal))})

    # Net Income up to date flows into Retained Earnings
    rev_dr = lines.filter(account__category=Account.Category.REVENUE).aggregate(t=Coalesce(Sum("debit"), Decimal("0.00")))["t"]
    rev_cr = lines.filter(account__category=Account.Category.REVENUE).aggregate(t=Coalesce(Sum("credit"), Decimal("0.00")))["t"]
    exp_dr = lines.filter(account__category=Account.Category.EXPENSE).aggregate(t=Coalesce(Sum("debit"), Decimal("0.00")))["t"]
    exp_cr = lines.filter(account__category=Account.Category.EXPENSE).aggregate(t=Coalesce(Sum("credit"), Decimal("0.00")))["t"]

    retained_earnings = (rev_cr - rev_dr) - (exp_dr - exp_cr)
    total_equity_with_earnings = total_equity + retained_earnings

    is_balanced = total_assets == (total_liabilities + total_equity_with_earnings)

    return {
        "as_of_date": as_of.isoformat(),
        "currency": organization.currency,
        "assets": {
            "accounts": assets,
            "total_assets": str(_normalize_decimal(total_assets)),
        },
        "liabilities": {
            "accounts": liabilities,
            "total_liabilities": str(_normalize_decimal(total_liabilities)),
        },
        "equity": {
            "accounts": equity,
            "retained_earnings": str(_normalize_decimal(retained_earnings)),
            "total_equity": str(_normalize_decimal(total_equity_with_earnings)),
        },
        "total_liabilities_and_equity": str(_normalize_decimal(total_liabilities + total_equity_with_earnings)),
        "is_balanced": is_balanced,
    }


def get_cash_and_bank_position_report(
    *,
    organization: Organization,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """
    Cash & Bank Position Statement:
    Source: Accounts 1000, 1010, 1020 + JournalLine
    """
    s_date = start_date or date(timezone.now().year, timezone.now().month, 1)
    e_date = end_date or timezone.now().date()

    liquid_accounts = (
        Account.objects
        .for_organization(organization)
        .filter(code__in=["1000", "1010", "1020"], is_active=True)
        .order_by("code")
    )

    accounts_data = []
    total_liquid = Decimal("0.00")

    for acc in liquid_accounts:
        # Opening before start_date
        op_lines = JournalLine.objects.for_organization(organization).filter(
            account=acc,
            journal_entry__status=JournalEntry.Status.POSTED,
            journal_entry__date__lt=s_date,
        )
        op_dr = op_lines.aggregate(t=Coalesce(Sum("debit"), Decimal("0.00")))["t"]
        op_cr = op_lines.aggregate(t=Coalesce(Sum("credit"), Decimal("0.00")))["t"]
        opening = op_dr - op_cr

        # Period lines
        p_lines = JournalLine.objects.for_organization(organization).filter(
            account=acc,
            journal_entry__status=JournalEntry.Status.POSTED,
            journal_entry__date__gte=s_date,
            journal_entry__date__lte=e_date,
        )
        inflow = p_lines.aggregate(t=Coalesce(Sum("debit"), Decimal("0.00")))["t"]
        outflow = p_lines.aggregate(t=Coalesce(Sum("credit"), Decimal("0.00")))["t"]
        closing = opening + inflow - outflow

        total_liquid += closing

        accounts_data.append({
            "code": acc.code,
            "name": acc.name,
            "account_type": acc.account_type,
            "opening_balance": str(_normalize_decimal(opening)),
            "inflows": str(_normalize_decimal(inflow)),
            "outflows": str(_normalize_decimal(outflow)),
            "closing_balance": str(_normalize_decimal(closing)),
        })

    return {
        "period": {"start_date": s_date.isoformat(), "end_date": e_date.isoformat()},
        "total_liquid_funds": str(_normalize_decimal(total_liquid)),
        "accounts": accounts_data,
    }


# =========================================================================
# PHASE 5: SUPPORT, SLA & OPERATIONS REPORTS
# =========================================================================

def get_complaint_sla_mttr_report(
    *,
    organization: Organization,
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = None,
    priority: str | None = None,
) -> dict:
    """
    Complaint SLA & Mean Time to Resolve (MTTR):
    Formula: MTTR (hrs) = Sum(resolved_at - created_at) / Total Resolved
    """
    qs = Complaint.objects.for_organization(organization)

    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)
    if category and category != "ALL":
        qs = qs.filter(category=category)
    if priority and priority != "ALL":
        qs = qs.filter(priority=priority)

    total_complaints = qs.count()
    breached_count = qs.filter(sla_status=Complaint.SLAStatus.BREACHED).count()
    resolved_count = qs.filter(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.CUSTOMER_CONFIRMED]).count()

    # Category breakdown
    cat_counts = list(
        qs.values("category")
        .annotate(total=Count("id"), breached=Count("id", filter=Q(sla_status=Complaint.SLAStatus.BREACHED)))
        .order_by("-total")
    )

    breach_rate = round((breached_count / total_complaints * 100), 1) if total_complaints > 0 else 0.0

    return {
        "summary": {
            "total_complaints": total_complaints,
            "resolved_count": resolved_count,
            "breached_count": breached_count,
            "sla_breach_rate_percent": breach_rate,
            "sla_compliance_rate_percent": round(100.0 - breach_rate, 1),
        },
        "category_breakdown": [
            {
                "category": row["category"],
                "total_count": row["total"],
                "breached_count": row["breached"],
                "breach_rate_percent": round((row["breached"] / row["total"] * 100), 1) if row["total"] > 0 else 0.0,
            }
            for row in cat_counts
        ],
    }


# =========================================================================
# PHASE 6: INQUIRY & SALES FUNNEL REPORTS
# =========================================================================

def get_lead_conversion_funnel_report(
    *,
    organization: Organization,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """
    Sales Inquiry & Conversion Funnel.
    """
    from customers.models import Inquiry

    qs = Inquiry.objects.for_organization(organization)

    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    total_inquiries = qs.count()
    contacted_count = qs.filter(status__in=[Inquiry.Status.CONTACTED, Inquiry.Status.FEASIBLE, Inquiry.Status.CONVERTED]).count()
    feasible_count = qs.filter(status__in=[Inquiry.Status.FEASIBLE, Inquiry.Status.CONVERTED]).count()
    converted_count = qs.filter(status=Inquiry.Status.CONVERTED).count()
    lost_count = qs.filter(status=Inquiry.Status.LOST).count()

    conv_rate = round((converted_count / total_inquiries * 100), 1) if total_inquiries > 0 else 0.0

    sources = list(
        qs.values("source")
        .annotate(total=Count("id"), converted=Count("id", filter=Q(status=Inquiry.Status.CONVERTED)))
        .order_by("-total")
    )

    return {
        "summary": {
            "total_inquiries": total_inquiries,
            "contacted_count": contacted_count,
            "feasible_count": feasible_count,
            "converted_count": converted_count,
            "lost_count": lost_count,
            "conversion_rate_percent": conv_rate,
        },
        "funnel_stages": [
            {"stage": "1. Inquiries Received", "count": total_inquiries, "dropoff_percent": 0.0},
            {"stage": "2. Contacted", "count": contacted_count, "dropoff_percent": round(((total_inquiries - contacted_count) / total_inquiries * 100), 1) if total_inquiries > 0 else 0.0},
            {"stage": "3. Feasible", "count": feasible_count, "dropoff_percent": round(((contacted_count - feasible_count) / contacted_count * 100), 1) if contacted_count > 0 else 0.0},
            {"stage": "4. Activated Subscriber", "count": converted_count, "dropoff_percent": round(((feasible_count - converted_count) / feasible_count * 100), 1) if feasible_count > 0 else 0.0},
        ],
        "source_breakdown": [
            {
                "source": row["source"],
                "total": row["total"],
                "converted": row["converted"],
                "conversion_rate": round((row["converted"] / row["total"] * 100), 1) if row["total"] > 0 else 0.0,
            }
            for row in sources
        ],
    }


# =========================================================================
# PHASE 7: INVENTORY & DEVICE CUSTODY REPORTS
# =========================================================================

def get_device_custody_report(
    *,
    organization: Organization,
    device_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    """
    CPE Device Custody & Deployment Register.
    """
    qs = (
        InventoryDevice.objects
        .for_organization(organization)
        .prefetch_related(
            "assignments",
            "assignments__service_account",
            "assignments__service_account__customer",
        )
        .order_by("asset_tag")
    )

    if device_type and device_type != "ALL":
        qs = qs.filter(device_type=device_type)
    if status and status != "ALL":
        qs = qs.filter(status=status)

    total_records = qs.count()
    total_pages = max(1, math.ceil(total_records / page_size))
    offset = (page - 1) * page_size
    paged_items = qs[offset : offset + page_size]

    records = []
    for d in paged_items:
        active_assign = d.assignments.filter(returned_at__isnull=True).first()
        records.append({
            "id": str(d.id),
            "asset_tag": d.asset_tag,
            "device_type": d.device_type,
            "manufacturer": d.manufacturer or "-",
            "model_name": d.model_name or "-",
            "serial_number": d.serial_number or "-",
            "mac_address": d.mac_address or "-",
            "status": d.status,
            "assigned_customer": active_assign.service_account.customer.full_name if active_assign else "In Warehouse",
            "assigned_service": active_assign.service_account.service_number if active_assign else "-",
            "assigned_date": active_assign.assigned_at.strftime("%Y-%m-%d") if active_assign else "-",
        })

    return {
        "summary": {
            "total_devices": total_records,
            "assigned_count": InventoryDevice.objects.for_organization(organization).filter(status=InventoryDevice.Status.ASSIGNED).count(),
            "available_count": InventoryDevice.objects.for_organization(organization).filter(status=InventoryDevice.Status.AVAILABLE).count(),
            "faulty_count": InventoryDevice.objects.for_organization(organization).filter(status=InventoryDevice.Status.FAULTY).count(),
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
        },
        "records": records,
    }


# =========================================================================
# PHASE 8: CSV STREAMING EXPORT HELPER
# =========================================================================

def generate_csv_response(filename: str, headers: list[str], rows: list[list]) -> str:
    """Generates standard CSV content string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return output.getvalue()