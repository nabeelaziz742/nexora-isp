"""Super admin view of the platform: ISP list, subscriptions, suspension.

The super admin sees each ISP's counts (customers, services, staff) but never
the ISP's customer records themselves.
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from customers.models import Customer, ServiceAccount
from onboarding.models import ISPRegistration, ISPSubscription, ISPSubscriptionPayment
from onboarding.services import get_or_create_payment_settings
from tenancy.models import Organization, OrganizationMembership

MAX_SUBSCRIPTION_MONTHS = 24
EXPIRING_SOON_DAYS = 7

# Platform status of an ISP, as shown to the super admin.
STATUS_ACTIVE = "ACTIVE"
STATUS_EXPIRING = "EXPIRING"  # active, paid-until within EXPIRING_SOON_DAYS
STATUS_OVERDUE = "OVERDUE"  # active, past paid-until but inside the grace period
STATUS_SUSPENDED = "SUSPENDED"
STATUS_PENDING = "PENDING"  # registration not approved yet
STATUS_REJECTED = "REJECTED"


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def get_or_create_subscription(organization: Organization) -> ISPSubscription:
    subscription, _ = ISPSubscription.objects.get_or_create(organization=organization)
    return subscription


def platform_status(*, organization: Organization, subscription: ISPSubscription | None,
                    registration: ISPRegistration | None, today: date) -> str:
    if registration is not None and registration.status in (
        ISPRegistration.Status.PENDING_PAYMENT,
        ISPRegistration.Status.PENDING_VERIFICATION,
    ):
        return STATUS_PENDING
    if registration is not None and registration.status == ISPRegistration.Status.REJECTED:
        return STATUS_REJECTED
    if not organization.is_active:
        return STATUS_SUSPENDED
    paid_until = subscription.paid_until if subscription else None
    if paid_until is None:
        return STATUS_ACTIVE
    if paid_until < today:
        return STATUS_OVERDUE
    if paid_until <= today + timedelta(days=EXPIRING_SOON_DAYS):
        return STATUS_EXPIRING
    return STATUS_ACTIVE


def _owner_of(organization: Organization):
    membership = (
        OrganizationMembership.objects.filter(
            organization=organization, role=OrganizationMembership.Role.OWNER
        )
        .select_related("user")
        .order_by("created_at")
        .first()
    )
    return membership.user if membership else None


def _count(queryset):
    """Correlated COUNT(*) subquery; avoids multiplying rows across joins."""
    return Subquery(
        queryset.filter(organization=OuterRef("pk"))
        .order_by()
        .values("organization")
        .annotate(total=Count("pk"))
        .values("total"),
        output_field=IntegerField(),
    )


def _isp_queryset():
    return Organization.objects.annotate(
        customer_count=Coalesce(_count(Customer.objects.all()), 0),
        active_service_count=Coalesce(
            _count(ServiceAccount.objects.filter(status=ServiceAccount.Status.ACTIVE)), 0
        ),
        staff_count=Coalesce(_count(OrganizationMembership.objects.filter(is_active=True)), 0),
    ).select_related("platform_subscription", "registration")


def _summary(org: Organization, today: date) -> dict:
    subscription = getattr(org, "platform_subscription", None)
    registration = getattr(org, "registration", None)
    owner = _owner_of(org)
    paid_until = subscription.paid_until if subscription else None
    return {
        "id": str(org.id),
        "name": org.name,
        "code": org.code,
        "city": org.city,
        "is_active": org.is_active,
        "status": platform_status(organization=org, subscription=subscription, registration=registration, today=today),
        "owner_name": owner.get_full_name() if owner else "",
        "owner_email": owner.email if owner else "",
        "customer_count": org.customer_count,
        "active_service_count": org.active_service_count,
        "staff_count": org.staff_count,
        "joined_at": org.created_at.isoformat(),
        "monthly_fee": str(subscription.monthly_fee) if subscription else "0.00",
        "paid_until": paid_until.isoformat() if paid_until else None,
        "days_left": (paid_until - today).days if paid_until else None,
        "suspension_kind": subscription.suspension_kind if subscription else "",
        "suspension_reason": subscription.suspension_reason if subscription else "",
        "registration_status": registration.status if registration else None,
    }


def list_isps(*, search: str = "", status: str = "", subscription_filter: str = "") -> list[dict]:
    today = timezone.localdate()
    queryset = _isp_queryset().order_by("name")
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search) | Q(city__icontains=search))
    items = [_summary(org, today) for org in queryset]
    if status:
        items = [item for item in items if item["status"] == status]
    if subscription_filter == "expiring":
        items = [item for item in items if item["days_left"] is not None and 0 <= item["days_left"] <= EXPIRING_SOON_DAYS]
    elif subscription_filter == "expired":
        items = [item for item in items if item["days_left"] is not None and item["days_left"] < 0]
    elif subscription_filter == "untracked":
        items = [item for item in items if item["paid_until"] is None and item["status"] not in (STATUS_PENDING, STATUS_REJECTED)]
    if subscription_filter:
        items.sort(key=lambda item: (item["paid_until"] is None, item["paid_until"] or ""))
    return items


def get_isp_detail(organization_id) -> dict:
    org = _isp_queryset().filter(id=organization_id).first()
    if org is None:
        raise ValidationError({"detail": "ISP not found."})
    today = timezone.localdate()
    detail = _summary(org, today)
    subscription = getattr(org, "platform_subscription", None)
    registration = getattr(org, "registration", None)
    month_start = today.replace(day=1)
    detail.update({
        "phone": org.phone,
        "email": org.email,
        "address": org.address,
        "notes": subscription.notes if subscription else "",
        "suspended_at": subscription.suspended_at.isoformat() if subscription and subscription.suspended_at else None,
        "new_customers_this_month": Customer.objects.filter(organization=org, created_at__date__gte=month_start).count(),
        "suspended_service_count": ServiceAccount.objects.filter(
            organization=org, status=ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        ).count(),
        "registration": {
            "status": registration.status,
            "amount_due": str(registration.amount_due),
            "verified_at": registration.verified_at.isoformat() if registration.verified_at else None,
        } if registration else None,
        "payments": [
            {
                "id": str(payment.id),
                "amount": str(payment.amount),
                "months": payment.months,
                "period_start": payment.period_start.isoformat(),
                "period_end": payment.period_end.isoformat(),
                "method": payment.method,
                "reference": payment.reference,
                "notes": payment.notes,
                "recorded_by": payment.recorded_by.get_full_name() or payment.recorded_by.email if payment.recorded_by else "",
                "created_at": payment.created_at.isoformat(),
            }
            for payment in ISPSubscriptionPayment.objects.filter(organization=org).select_related("recorded_by")[:50]
        ],
    })
    return detail


def get_platform_dashboard() -> dict:
    today = timezone.localdate()
    month_start = today.replace(day=1)
    items = list_isps()
    by_status: dict[str, int] = {}
    for item in items:
        by_status[item["status"]] = by_status.get(item["status"], 0) + 1

    live = [item for item in items if item["status"] not in (STATUS_PENDING, STATUS_REJECTED)]
    monthly_recurring = sum(
        (Decimal(item["monthly_fee"]) for item in live if item["is_active"]),
        Decimal("0.00"),
    )
    collected = ISPSubscriptionPayment.objects.filter(created_at__date__gte=month_start).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")

    return {
        "total_isps": len(live),
        "active_isps": sum(1 for item in live if item["is_active"]),
        "suspended_isps": by_status.get(STATUS_SUSPENDED, 0),
        "expiring_soon": by_status.get(STATUS_EXPIRING, 0),
        "overdue": by_status.get(STATUS_OVERDUE, 0),
        "pending_verification": ISPRegistration.objects.filter(status=ISPRegistration.Status.PENDING_VERIFICATION).count(),
        "pending_payment": ISPRegistration.objects.filter(status=ISPRegistration.Status.PENDING_PAYMENT).count(),
        "rejected": by_status.get(STATUS_REJECTED, 0),
        "new_isps_this_month": sum(1 for item in live if item["joined_at"][:10] >= month_start.isoformat()),
        "total_customers": sum(item["customer_count"] for item in live),
        "total_active_services": sum(item["active_service_count"] for item in live),
        "monthly_recurring_revenue": str(monthly_recurring),
        "collected_this_month": str(collected),
        "grace_days": get_or_create_payment_settings().subscription_grace_days,
        "attention": [
            item for item in items
            if item["status"] in (STATUS_OVERDUE, STATUS_EXPIRING)
        ][:10],
        "recent_isps": sorted(live, key=lambda item: item["joined_at"], reverse=True)[:5],
    }


@transaction.atomic
def suspend_isp(*, organization_id, actor, reason: str, kind: str = ISPSubscription.SuspensionKind.MANUAL) -> Organization:
    if not reason or not reason.strip():
        raise ValidationError({"reason": "A reason is required to suspend an ISP."})
    organization = Organization.objects.select_for_update().filter(id=organization_id).first()
    if organization is None:
        raise ValidationError({"detail": "ISP not found."})
    subscription = get_or_create_subscription(organization)
    organization.is_active = False
    organization.save(update_fields=["is_active", "updated_at"])
    subscription.suspension_kind = kind
    subscription.suspension_reason = reason.strip()
    subscription.suspended_at = timezone.now()
    subscription.suspended_by = actor
    subscription.save(update_fields=["suspension_kind", "suspension_reason", "suspended_at", "suspended_by", "updated_at"])
    return organization


@transaction.atomic
def activate_isp(*, organization_id) -> Organization:
    organization = Organization.objects.select_for_update().filter(id=organization_id).first()
    if organization is None:
        raise ValidationError({"detail": "ISP not found."})
    registration = getattr(organization, "registration", None)
    if registration is not None and registration.status != ISPRegistration.Status.ACTIVE:
        raise ValidationError({"detail": "Approve this ISP's registration payment first."})
    subscription = get_or_create_subscription(organization)
    organization.is_active = True
    organization.save(update_fields=["is_active", "updated_at"])
    subscription.suspension_kind = ISPSubscription.SuspensionKind.NONE
    subscription.suspension_reason = ""
    subscription.suspended_at = None
    subscription.suspended_by = None
    subscription.save(update_fields=["suspension_kind", "suspension_reason", "suspended_at", "suspended_by", "updated_at"])
    return organization


@transaction.atomic
def update_subscription(*, organization_id, monthly_fee=None, paid_until=None, notes=None,
                        clear_paid_until: bool = False) -> ISPSubscription:
    organization = Organization.objects.filter(id=organization_id).first()
    if organization is None:
        raise ValidationError({"detail": "ISP not found."})
    subscription = ISPSubscription.objects.select_for_update().get(pk=get_or_create_subscription(organization).pk)
    if monthly_fee is not None:
        subscription.monthly_fee = monthly_fee
    if clear_paid_until:
        subscription.paid_until = None
    elif paid_until is not None:
        subscription.paid_until = paid_until
    if notes is not None:
        subscription.notes = notes
    subscription.save()
    return subscription


@transaction.atomic
def record_subscription_payment(*, organization_id, actor, amount, months: int, method: str,
                                reference: str = "", notes: str = "") -> ISPSubscriptionPayment:
    if months < 1 or months > MAX_SUBSCRIPTION_MONTHS:
        raise ValidationError({"months": f"Months must be between 1 and {MAX_SUBSCRIPTION_MONTHS}."})
    if amount is None or Decimal(amount) < 0:
        raise ValidationError({"amount": "Amount cannot be negative."})
    organization = Organization.objects.select_for_update().filter(id=organization_id).first()
    if organization is None:
        raise ValidationError({"detail": "ISP not found."})
    registration = getattr(organization, "registration", None)
    if registration is not None and registration.status != ISPRegistration.Status.ACTIVE:
        raise ValidationError({"detail": "Approve this ISP's registration payment first."})

    subscription = ISPSubscription.objects.select_for_update().get(pk=get_or_create_subscription(organization).pk)
    today = timezone.localdate()
    # Paying early extends from the current paid-until; paying late starts today.
    if subscription.paid_until and subscription.paid_until >= today:
        period_start = subscription.paid_until + timedelta(days=1)
    else:
        period_start = today
    period_end = _add_months(period_start, months) - timedelta(days=1)

    payment = ISPSubscriptionPayment.objects.create(
        organization=organization,
        amount=amount,
        months=months,
        period_start=period_start,
        period_end=period_end,
        method=method,
        reference=reference.strip(),
        notes=notes.strip(),
        recorded_by=actor,
    )
    subscription.paid_until = period_end
    subscription.save(update_fields=["paid_until", "updated_at"])

    # A lock caused only by non-payment lifts once the ISP has paid.
    if not organization.is_active and subscription.suspension_kind == ISPSubscription.SuspensionKind.EXPIRED:
        activate_isp(organization_id=organization.id)
    return payment


def start_first_subscription(*, registration: ISPRegistration, actor) -> None:
    """On approval, the verified registration payment covers the first month."""
    subscription = get_or_create_subscription(registration.organization)
    if subscription.paid_until is not None:
        return
    if subscription.monthly_fee == 0:
        subscription.monthly_fee = registration.amount_due
        subscription.save(update_fields=["monthly_fee", "updated_at"])
    record_subscription_payment(
        organization_id=registration.organization_id,
        actor=actor,
        amount=registration.amount_due,
        months=1,
        method=ISPSubscriptionPayment.Method.BANK_TRANSFER,
        reference="Registration payment",
    )


def enforce_subscription_expiry(*, today: date | None = None) -> dict:
    """Lock ISPs whose paid-until date plus the grace period has passed.

    ISPs without a tracked paid-until date are never locked automatically.
    """
    today = today or timezone.localdate()
    grace_days = get_or_create_payment_settings().subscription_grace_days
    cutoff = today - timedelta(days=grace_days)
    due = ISPSubscription.objects.filter(
        paid_until__isnull=False,
        paid_until__lt=cutoff,
        organization__is_active=True,
    ).values_list("organization_id", flat=True)

    locked = []
    for organization_id in list(due):
        organization = suspend_isp(
            organization_id=organization_id,
            actor=None,
            reason=f"Subscription unpaid for more than {grace_days} days after its due date.",
            kind=ISPSubscription.SuspensionKind.EXPIRED,
        )
        locked.append(organization.code)
    return {"locked_count": len(locked), "locked": locked}
