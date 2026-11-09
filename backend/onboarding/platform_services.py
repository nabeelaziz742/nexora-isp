"""Super admin view of the platform: ISP list, subscriptions, suspension.

The super admin sees each ISP's counts (customers, services, staff) but never
the ISP's customer records themselves.
"""
import calendar
import secrets
from datetime import date, timedelta
from decimal import Decimal

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.formats import date_format
from rest_framework.exceptions import ValidationError

from customers.models import Customer, ServiceAccount
from onboarding.models import ISPRegistration, ISPSubscription, ISPSubscriptionPayment
from onboarding.receipts import email_receipt, next_receipt_number
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
        staff_count=Coalesce(_count(
            OrganizationMembership.objects.filter(is_active=True).exclude(role=OrganizationMembership.Role.DEALER)
        ), 0),
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
        "reminder_stage": subscription.reminder_stage if subscription else "",
        "reminder_sent_at": subscription.reminder_sent_at.isoformat() if subscription and subscription.reminder_sent_at else None,
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
                "receipt_number": payment.receipt_number or "",
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
        receipt_number=next_receipt_number(),
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
    # Mail the receipt only once the payment is really saved.
    transaction.on_commit(lambda: email_receipt(payment))
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


# ---------------------------------------------------------------------------
# Fee reminders and the owner's own view of their subscription
# ---------------------------------------------------------------------------

REMINDER_DUE_SOON = "DUE_SOON"  # 3 days or fewer before paid-until
REMINDER_DUE_TODAY = "DUE_TODAY"
REMINDER_OVERDUE = "OVERDUE"
REMINDER_ORDER = {REMINDER_DUE_SOON: 1, REMINDER_DUE_TODAY: 2, REMINDER_OVERDUE: 3}
REMINDER_DAYS_BEFORE = 3


def _reminder_stage(days_left: int) -> str:
    if days_left < 0:
        return REMINDER_OVERDUE
    if days_left == 0:
        return REMINDER_DUE_TODAY
    if days_left <= REMINDER_DAYS_BEFORE:
        return REMINDER_DUE_SOON
    return ""


def subscription_status_for_owner(organization: Organization) -> dict:
    """What an ISP owner sees about their own Nexora subscription."""
    subscription = getattr(organization, "platform_subscription", None)
    settings_obj = get_or_create_payment_settings()
    today = timezone.localdate()
    paid_until = subscription.paid_until if subscription else None
    days_left = (paid_until - today).days if paid_until else None
    lock_date = paid_until + timedelta(days=settings_obj.subscription_grace_days) if paid_until else None
    return {
        "tracked": paid_until is not None,
        "monthly_fee": str(subscription.monthly_fee) if subscription else "0.00",
        "paid_until": paid_until.isoformat() if paid_until else None,
        "days_left": days_left,
        "lock_date": lock_date.isoformat() if lock_date else None,
        "show_notice": days_left is not None and days_left <= EXPIRING_SOON_DAYS,
        "payment": {
            "bank_name": settings_obj.bank_name,
            "account_title": settings_obj.account_title,
            "account_number": settings_obj.account_number,
            "iban": settings_obj.iban,
        },
        "payments": [
            {
                "id": str(payment.id),
                "receipt_number": payment.receipt_number or "",
                "amount": str(payment.amount),
                "months": payment.months,
                "period_start": payment.period_start.isoformat(),
                "period_end": payment.period_end.isoformat(),
                "method": payment.get_method_display(),
                "created_at": payment.created_at.isoformat(),
            }
            for payment in ISPSubscriptionPayment.objects.filter(organization=organization)[:24]
        ],
    }


def _reminder_email(subscription: ISPSubscription, stage: str, owner, today: date) -> tuple[str, str]:
    org = subscription.organization
    settings_obj = get_or_create_payment_settings()
    paid_until = subscription.paid_until
    lock_date = paid_until + timedelta(days=settings_obj.subscription_grace_days)
    fee = f"PKR {subscription.monthly_fee:,.0f}"
    paid_text = date_format(paid_until, "j M Y")
    lock_text = date_format(lock_date, "j M Y")
    if stage == REMINDER_DUE_SOON:
        subject = f"Nexora subscription for {org.name} is due on {paid_text}"
        opening = f"Your Nexora ISP subscription is paid until {paid_text}."
    elif stage == REMINDER_DUE_TODAY:
        subject = f"Nexora subscription for {org.name} is due today"
        opening = "Your Nexora ISP subscription is due today."
    else:
        subject = f"Nexora subscription for {org.name} is overdue"
        opening = f"Your Nexora ISP subscription was due on {paid_text} and is now overdue."
    body = (
        f"Hello {owner.first_name or ''},\n\n"
        f"{opening}\n"
        f"Monthly fee: {fee}\n\n"
        "Please pay to:\n"
        f"  {settings_obj.bank_name}\n"
        f"  Account title: {settings_obj.account_title}\n"
        f"  Account number: {settings_obj.account_number}\n"
        + (f"  IBAN: {settings_obj.iban}\n" if settings_obj.iban else "")
        + f"\nIf payment is not received, the {org.name} workspace will be locked on {lock_text}. "
        "Send your payment receipt to Nexora support so it can be recorded.\n\n"
        "If you have already paid, please ignore this email.\n"
    )
    return subject, body


def send_subscription_reminders(*, today: date | None = None) -> dict:
    """Email ISP owners before, on and after their paid-until date (each stage once)."""
    today = today or timezone.localdate()
    window_end = today + timedelta(days=REMINDER_DAYS_BEFORE)
    subscriptions = ISPSubscription.objects.filter(
        paid_until__isnull=False,
        paid_until__lte=window_end,
        organization__is_active=True,
    ).select_related("organization")

    sent, failed = [], []
    for subscription in subscriptions:
        stage = _reminder_stage((subscription.paid_until - today).days)
        if not stage:
            continue
        already = (
            subscription.reminder_for == subscription.paid_until
            and REMINDER_ORDER.get(subscription.reminder_stage, 0) >= REMINDER_ORDER[stage]
        )
        if already:
            continue
        owner = _owner_of(subscription.organization)
        if owner is None or not owner.email:
            continue
        subject, body = _reminder_email(subscription, stage, owner, today)
        try:
            send_mail(subject=subject, message=body, from_email=None, recipient_list=[owner.email], fail_silently=False)
        except Exception:  # noqa: BLE001 - one bad mailbox must not stop the others
            failed.append(subscription.organization.code)
            continue
        subscription.reminder_stage = stage
        subscription.reminder_for = subscription.paid_until
        subscription.reminder_sent_at = timezone.now()
        subscription.save(update_fields=["reminder_stage", "reminder_for", "reminder_sent_at", "updated_at"])
        sent.append(subscription.organization.code)
    return {"sent_count": len(sent), "sent": sent, "failed": failed}


def reset_owner_password(*, organization_id) -> tuple[str, str]:
    """Super admin fallback when an owner cannot receive the reset email.

    Returns (owner email, new temporary password); the password is shown once.
    """
    organization = Organization.objects.filter(id=organization_id).first()
    if organization is None:
        raise ValidationError({"detail": "ISP not found."})
    owner = _owner_of(organization)
    if owner is None:
        raise ValidationError({"detail": "This ISP has no owner account."})
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    password = "Nx-" + "".join(secrets.choice(alphabet) for _ in range(12))
    owner.set_password(password)
    owner.save(update_fields=["password"])
    return owner.email, password
