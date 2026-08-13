import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
)
from customers.models import (
    InternetPackage,
    ServiceAccount,
)
from tenancy.models import Organization


ZERO = Decimal("0.00")
MONEY_FIELD = DecimalField(
    max_digits=18,
    decimal_places=2,
)


@dataclass(frozen=True)
class RevenuePeriod:
    year: int
    month: int
    start: date
    end: date
    label: str


def _money(value) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))

    return Decimal(str(value)).quantize(
        Decimal("0.01")
    )


def _month_period(
    *,
    year: int,
    month: int,
) -> RevenuePeriod:
    last_day = calendar.monthrange(
        year,
        month,
    )[1]

    start = date(year, month, 1)
    end = date(year, month, last_day)

    return RevenuePeriod(
        year=year,
        month=month,
        start=start,
        end=end,
        label=start.strftime("%b"),
    )


def _shift_month(
    *,
    year: int,
    month: int,
    offset: int,
) -> RevenuePeriod:
    month_index = (
        (year * 12)
        + (month - 1)
        + offset
    )

    shifted_year = month_index // 12
    shifted_month = (month_index % 12) + 1

    return _month_period(
        year=shifted_year,
        month=shifted_month,
    )


def _invoice_totals_by_period(
    *,
    organization: Organization,
    period: RevenuePeriod,
) -> dict:
    invoice_lines = (
        InvoiceLine.objects
        .for_organization(organization)
        .filter(
            invoice__billing_period_start__gte=(
                period.start
            ),
            invoice__billing_period_start__lte=(
                period.end
            ),
        )
    )

    billed = _money(
        invoice_lines.aggregate(
            total=Coalesce(
                Sum("amount"),
                Value(ZERO),
                output_field=MONEY_FIELD,
            )
        )["total"]
    )

    allocations = (
        PaymentAllocation.objects
        .for_organization(organization)
        .filter(
            invoice__billing_period_start__gte=(
                period.start
            ),
            invoice__billing_period_start__lte=(
                period.end
            ),
        )
    )

    allocated = _money(
        allocations.aggregate(
            total=Coalesce(
                Sum("amount"),
                Value(ZERO),
                output_field=MONEY_FIELD,
            )
        )["total"]
    )

    return {
        "billed": billed,
        "outstanding": max(
            billed - allocated,
            ZERO,
        ),
    }


def _collections_by_period(
    *,
    organization: Organization,
    period: RevenuePeriod,
) -> Decimal:
    return _money(
        Payment.objects
        .for_organization(organization)
        .filter(
            paid_at__date__gte=period.start,
            paid_at__date__lte=period.end,
        )
        .aggregate(
            total=Coalesce(
                Sum("amount"),
                Value(ZERO),
                output_field=MONEY_FIELD,
            )
        )["total"]
    )


def _service_exposure(
    *,
    organization: Organization,
    statuses: list[str],
) -> dict:
    allocations = (
        PaymentAllocation.objects
        .for_organization(organization)
        .values("invoice_id")
        .annotate(
            allocated_amount=Coalesce(
                Sum("amount"),
                Value(ZERO),
                output_field=MONEY_FIELD,
            )
        )
    )

    allocation_map = {
        item["invoice_id"]: _money(
            item["allocated_amount"]
        )
        for item in allocations
    }

    invoices = (
        Invoice.objects
        .for_organization(organization)
        .filter(
            service_account__status__in=statuses,
        )
        .exclude(
            status=Invoice.Status.PAID,
        )
        .annotate(
            invoice_total=Coalesce(
                Sum("lines__amount"),
                Value(ZERO),
                output_field=MONEY_FIELD,
            )
        )
        .values(
            "id",
            "service_account_id",
            "invoice_total",
        )
    )

    exposure = ZERO
    service_ids = set()

    for invoice in invoices:
        invoice_total = _money(
            invoice["invoice_total"]
        )
        allocated_amount = allocation_map.get(
            invoice["id"],
            ZERO,
        )
        outstanding = max(
            invoice_total - allocated_amount,
            ZERO,
        )

        if outstanding > ZERO:
            exposure += outstanding
            service_ids.add(
                invoice["service_account_id"]
            )

    return {
        "exposure": _money(exposure),
        "service_count": len(service_ids),
    }


def _upgrade_opportunity(
    *,
    organization: Organization,
) -> dict:
    packages = list(
        InternetPackage.objects
        .for_organization(organization)
        .filter(is_active=True)
        .order_by(
            "monthly_price",
            "download_speed_mbps",
            "name",
        )
        .values(
            "id",
            "name",
            "monthly_price",
        )
    )

    if len(packages) < 2:
        return {
            "impact": ZERO,
            "candidate_count": 0,
            "segment": "No eligible package ladder",
        }

    next_package_by_id = {}

    for index, package in enumerate(packages):
        current_price = _money(
            package["monthly_price"]
        )

        next_package = next(
            (
                candidate
                for candidate in packages[
                    index + 1:
                ]
                if _money(
                    candidate["monthly_price"]
                ) > current_price
            ),
            None,
        )

        if next_package is not None:
            next_package_by_id[
                package["id"]
            ] = next_package

    services = (
        ServiceAccount.objects
        .for_organization(organization)
        .filter(
            status=ServiceAccount.Status.ACTIVE,
            internet_package_id__in=(
                next_package_by_id.keys()
            ),
        )
        .select_related("internet_package")
    )

    impact = ZERO
    candidate_count = 0
    package_counts = {}

    for service in services:
        next_package = next_package_by_id[
            service.internet_package_id
        ]

        price_difference = (
            _money(next_package["monthly_price"])
            - _money(
                service.internet_package.monthly_price
            )
        )

        if price_difference <= ZERO:
            continue

        impact += price_difference
        candidate_count += 1

        package_name = (
            service.internet_package.name
        )

        package_counts[package_name] = (
            package_counts.get(
                package_name,
                0,
            )
            + 1
        )

    if not package_counts:
        segment = "No eligible active services"
    else:
        segment = max(
            package_counts,
            key=package_counts.get,
        )

    return {
        "impact": _money(impact),
        "candidate_count": candidate_count,
        "segment": segment,
    }


def _revenue_health_score(
    *,
    billed: Decimal,
    collected: Decimal,
    outstanding: Decimal,
    suspension_exposure: Decimal,
) -> int:
    if billed <= ZERO:
        return 0

    collection_rate = min(
        collected / billed,
        Decimal("1.00"),
    )

    outstanding_rate = min(
        outstanding / billed,
        Decimal("1.00"),
    )

    suspension_rate = min(
        suspension_exposure / billed,
        Decimal("1.00"),
    )

    score = (
        (collection_rate * Decimal("70"))
        + (
            (
                Decimal("1.00")
                - outstanding_rate
            )
            * Decimal("20")
        )
        + (
            (
                Decimal("1.00")
                - suspension_rate
            )
            * Decimal("10")
        )
    )

    return max(
        0,
        min(
            100,
            int(
                score.quantize(
                    Decimal("1")
                )
            ),
        ),
    )


def build_revenue_intelligence(
    *,
    organization: Organization,
    as_of: date | None = None,
) -> dict:
    today = as_of or date.today()

    current_period = _month_period(
        year=today.year,
        month=today.month,
    )

    previous_period = _shift_month(
        year=today.year,
        month=today.month,
        offset=-1,
    )

    current_totals = (
        _invoice_totals_by_period(
            organization=organization,
            period=current_period,
        )
    )

    previous_totals = (
        _invoice_totals_by_period(
            organization=organization,
            period=previous_period,
        )
    )

    collected = _collections_by_period(
        organization=organization,
        period=current_period,
    )

    previous_collected = _collections_by_period(
        organization=organization,
        period=previous_period,
    )

    suspension_risk = _service_exposure(
        organization=organization,
        statuses=[
            ServiceAccount.Status.SUSPENSION_PENDING,
            ServiceAccount.Status.SUSPENDED_NON_PAYMENT,
        ],
    )

    grace_period_risk = _service_exposure(
        organization=organization,
        statuses=[
            ServiceAccount.Status.GRACE_PERIOD,
        ],
    )

    upgrade = _upgrade_opportunity(
        organization=organization,
    )

    billed = current_totals["billed"]
    outstanding = current_totals["outstanding"]

    collection_rate = (
        (collected / billed) * Decimal("100")
        if billed > ZERO
        else ZERO
    )

    previous_billed = previous_totals["billed"]

    billed_change = (
        (
            (billed - previous_billed)
            / previous_billed
        )
        * Decimal("100")
        if previous_billed > ZERO
        else None
    )

    health_score = _revenue_health_score(
        billed=billed,
        collected=collected,
        outstanding=outstanding,
        suspension_exposure=(
            suspension_risk["exposure"]
        ),
    )

    history = []

    for offset in range(-5, 1):
        period = _shift_month(
            year=today.year,
            month=today.month,
            offset=offset,
        )

        period_totals = (
            _invoice_totals_by_period(
                organization=organization,
                period=period,
            )
        )

        period_collected = _collections_by_period(
            organization=organization,
            period=period,
        )

        history.append(
            {
                "month": period.label,
                "year": period.year,
                "billed": period_totals["billed"],
                "collected": period_collected,
            }
        )

    risk_signals = []

    if suspension_risk["exposure"] > ZERO:
        risk_signals.append(
            {
                "id": "suspension-risk",
                "title": (
                    f"{suspension_risk['service_count']} "
                    "customer services carry "
                    "non-payment suspension exposure"
                ),
                "description": (
                    "Outstanding invoice value is "
                    "concentrated in services currently "
                    "marked suspension pending or "
                    "suspended for non-payment."
                ),
                "severity": "CRITICAL",
                "exposure_amount": (
                    suspension_risk["exposure"]
                ),
                "affected_customers": (
                    suspension_risk["service_count"]
                ),
                "confidence": 100,
                "action_label": (
                    "Review Suspension Risk"
                ),
            }
        )

    if grace_period_risk["exposure"] > ZERO:
        risk_signals.append(
            {
                "id": "grace-period-risk",
                "title": (
                    f"{grace_period_risk['service_count']} "
                    "services have grace period "
                    "collection exposure"
                ),
                "description": (
                    "Outstanding invoice value belongs "
                    "to services currently in the actual "
                    "grace period lifecycle state."
                ),
                "severity": "WARNING",
                "exposure_amount": (
                    grace_period_risk["exposure"]
                ),
                "affected_customers": (
                    grace_period_risk["service_count"]
                ),
                "confidence": 100,
                "action_label": (
                    "Review Grace Period"
                ),
            }
        )

    opportunities = []

    if upgrade["impact"] > ZERO:
        opportunities.append(
            {
                "id": "package-upgrade",
                "title": (
                    "Active package ladder upgrade "
                    "candidates"
                ),
                "description": (
                    "Active services with a higher-priced "
                    "active package available are grouped "
                    "using the nearest package price tier. "
                    "This is a deterministic package "
                    "ladder signal, not a usage prediction."
                ),
                "type": "PACKAGE_UPGRADE",
                "estimated_monthly_impact": (
                    upgrade["impact"]
                ),
                "customer_segment": upgrade["segment"],
                "customer_count": (
                    upgrade["candidate_count"]
                ),
                "confidence": 100,
            }
        )

    if grace_period_risk["exposure"] > ZERO:
        opportunities.append(
            {
                "id": "collection-recovery",
                "title": (
                    "Recoverable grace period revenue"
                ),
                "description": (
                    "Current outstanding value attached "
                    "to services in grace period can be "
                    "prioritized for collection activity."
                ),
                "type": "COLLECTION_RECOVERY",
                "estimated_monthly_impact": (
                    grace_period_risk["exposure"]
                ),
                "customer_segment": (
                    "Grace Period Services"
                ),
                "customer_count": (
                    grace_period_risk["service_count"]
                ),
                "confidence": 100,
            }
        )

    return {
        "currency": organization.currency,
        "period": {
            "year": current_period.year,
            "month": current_period.month,
            "start": current_period.start,
            "end": current_period.end,
        },
        "metrics": {
            "monthly_billed": billed,
            "collected_revenue": collected,
            "outstanding_exposure": outstanding,
            "suspension_risk_revenue": (
                suspension_risk["exposure"]
            ),
            "upgrade_potential": upgrade["impact"],
            "revenue_health": health_score,
            "collection_rate": (
                collection_rate.quantize(
                    Decimal("0.01")
                )
            ),
            "billed_change_percent": (
                billed_change.quantize(
                    Decimal("0.01")
                )
                if billed_change is not None
                else None
            ),
            "previous_collected_revenue": (
                previous_collected
            ),
            "outstanding_service_count": (
                Invoice.objects
                .for_organization(organization)
                .filter(
                    billing_period_start__gte=(
                        current_period.start
                    ),
                    billing_period_start__lte=(
                        current_period.end
                    ),
                )
                .exclude(
                    status=Invoice.Status.PAID,
                )
                .values("service_account_id")
                .distinct()
                .count()
            ),
            "suspension_risk_service_count": (
                suspension_risk["service_count"]
            ),
            "upgrade_candidate_count": (
                upgrade["candidate_count"]
            ),
        },
        "performance": history,
        "risk_signals": risk_signals,
        "opportunities": opportunities,
        "health_formula": {
            "collection_rate_weight": 70,
            "outstanding_control_weight": 20,
            "suspension_exposure_control_weight": 10,
            "description": (
                "Revenue Health = 70% collection rate "
                "+ 20% outstanding control "
                "+ 10% suspension exposure control. "
                "Each ratio is capped between 0 and 1."
            ),
        },
    }