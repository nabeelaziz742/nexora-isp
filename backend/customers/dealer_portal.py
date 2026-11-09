"""Dealer portal: a dealer signs in and works only with their own customers.

Access boundary (see also tenancy.authentication / tenancy.permissions):
a DEALER membership token is refused everywhere except /api/v1/dealer-portal/
and /api/v1/auth/, and every query here is filtered to customer.dealer = the
signed-in dealer.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import Payment
from billing.recharge_services import MAX_RECHARGE_MONTHS, recharge_service
from billing.services import BillingDomainError, record_payment_with_allocations
from customers.models import BillingProfile, Customer, Dealer, ServiceAccount
from customers.suspension_services import calculate_service_outstanding
from tenancy.models import OrganizationMembership
from tenancy.permissions import HasActiveTenantContext, IsOrganizationAdminOrOwner
from tenancy.services import record_audit_log

User = get_user_model()

DEALER_PAYMENT_METHODS = [
    Payment.Method.CASH,
    Payment.Method.MOBILE_WALLET,
    Payment.Method.BANK_TRANSFER,
]


# ---------------------------------------------------------------------------
# Owner side: give a dealer a login, reset it, or revoke it
# ---------------------------------------------------------------------------

def _get_dealer(organization, dealer_id) -> Dealer:
    dealer = (
        Dealer.objects.for_organization(organization)
        .select_related("portal_membership__user")
        .filter(id=dealer_id)
        .first()
    )
    if dealer is None:
        raise NotFound("Dealer was not found in this organization.")
    return dealer


def portal_access_state(dealer: Dealer) -> dict:
    membership = dealer.portal_membership
    return {
        "has_login": membership is not None,
        "is_enabled": bool(membership and membership.is_active and membership.user.is_active),
        "email": membership.user.email if membership else "",
    }


@transaction.atomic
def grant_portal_access(*, organization, actor, dealer_id, email: str, password: str) -> Dealer:
    dealer = Dealer.objects.select_for_update().get(pk=_get_dealer(organization, dealer_id).pk)
    email = email.strip().lower()
    membership = dealer.portal_membership

    try:
        validate_password(password)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)}) from exc

    if membership is not None:
        # Reset: same login user, new password (and email if changed).
        user = membership.user
        if email != user.email and User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            raise ValidationError({"email": "This email is already used by another account."})
        user.email = email
        user.username = email
        user.set_password(password)
        user.is_active = True
        user.save()
        membership.is_active = True
        membership.save(update_fields=["is_active", "updated_at"])
        action = "DEALER_PORTAL_LOGIN_RESET"
    else:
        # A fresh user only: never attach a dealer role to an existing account.
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({"email": "This email is already used by another account."})
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=dealer.name[:150],
            is_active=True,
        )
        membership = OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            role=OrganizationMembership.Role.DEALER,
            is_active=True,
        )
        dealer.portal_membership = membership
        dealer.save(update_fields=["portal_membership", "updated_at"])
        action = "DEALER_PORTAL_LOGIN_CREATED"

    record_audit_log(
        organization=organization,
        actor=actor,
        action=action,
        resource_type="Dealer",
        resource_id=dealer.id,
        metadata={"dealer_code": dealer.dealer_code, "email": email},
    )
    return dealer


@transaction.atomic
def revoke_portal_access(*, organization, actor, dealer_id) -> Dealer:
    dealer = _get_dealer(organization, dealer_id)
    membership = dealer.portal_membership
    if membership is not None and membership.is_active:
        membership.is_active = False
        membership.save(update_fields=["is_active", "updated_at"])
        record_audit_log(
            organization=organization,
            actor=actor,
            action="DEALER_PORTAL_LOGIN_DISABLED",
            resource_type="Dealer",
            resource_id=dealer.id,
            metadata={"dealer_code": dealer.dealer_code},
        )
    return dealer


class PortalAccessSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=8, max_length=128)


class DealerPortalAccessView(APIView):
    permission_classes = [IsOrganizationAdminOrOwner]

    def get(self, request, dealer_id):
        return Response(portal_access_state(_get_dealer(request.organization, dealer_id)))

    def post(self, request, dealer_id):
        serializer = PortalAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dealer = grant_portal_access(
            organization=request.organization,
            actor=request.user,
            dealer_id=dealer_id,
            **serializer.validated_data,
        )
        return Response(portal_access_state(dealer), status=status.HTTP_200_OK)

    def delete(self, request, dealer_id):
        dealer = revoke_portal_access(organization=request.organization, actor=request.user, dealer_id=dealer_id)
        return Response(portal_access_state(dealer), status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Dealer side: the portal itself
# ---------------------------------------------------------------------------

class IsActiveDealer(HasActiveTenantContext):
    message = "An active dealer account is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.organization_role != OrganizationMembership.Role.DEALER:
            return False
        dealer = (
            Dealer.objects.for_organization(request.organization)
            .filter(portal_membership=request.organization_membership)
            .first()
        )
        if dealer is None or dealer.status != Dealer.Status.ACTIVE:
            return False
        request.dealer = dealer
        return True


class DealerPortalView(APIView):
    allow_dealer = True
    permission_classes = [IsActiveDealer]


def _month_bounds(month: str | None) -> tuple[date, date]:
    today = timezone.localdate()
    if month:
        try:
            year, mon = (int(part) for part in month.split("-"))
            start = date(year, mon, 1)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"month": "Use YYYY-MM."}) from exc
    else:
        start = today.replace(day=1)
    end = date(start.year + (start.month // 12), start.month % 12 + 1, 1)
    return start, end


def _dealer_services(request):
    return (
        ServiceAccount.objects.for_organization(request.organization)
        .filter(customer__dealer=request.dealer)
        .select_related("customer", "internet_package", "billing_profile")
    )


def _get_dealer_service(request, service_id) -> ServiceAccount:
    service = _dealer_services(request).filter(id=service_id).first()
    if service is None:
        raise NotFound("This connection is not one of your customers.")
    return service


def _commission(dealer: Dealer, collected: Decimal, active_customers: int) -> Decimal:
    rate = dealer.commission_rate_percentage or Decimal("0.00")
    if dealer.commission_type == Dealer.CommissionType.PERCENTAGE:
        return (collected * rate / Decimal("100")).quantize(Decimal("0.01"))
    return (Decimal(active_customers) * rate).quantize(Decimal("0.01"))


def _service_row(service: ServiceAccount, today: date) -> dict:
    outstanding, _invoices, oldest_due = calculate_service_outstanding(service)
    profile = getattr(service, "billing_profile", None)
    is_prepaid = bool(profile and profile.billing_cycle == BillingProfile.BillingCycle.PREPAID)
    customer = service.customer
    return {
        "service_id": str(service.id),
        "service_number": service.service_number,
        "customer_number": customer.customer_number,
        "customer_name": customer.full_name,
        "phone": customer.phone,
        "area": customer.area,
        "package_name": service.internet_package.name,
        "monthly_price": str(service.internet_package.monthly_price),
        "status": service.status,
        "billing_mode": "PREPAID" if is_prepaid else "MONTHLY",
        "expiry_date": service.expiry_date.isoformat() if service.expiry_date else None,
        "days_to_expiry": (service.expiry_date - today).days if service.expiry_date else None,
        "outstanding": str(outstanding),
        "oldest_due_date": oldest_due.isoformat() if oldest_due else None,
    }


class DealerSummaryView(DealerPortalView):
    def get(self, request):
        dealer = request.dealer
        today = timezone.localdate()
        start, end = _month_bounds(None)
        services = list(_dealer_services(request))
        active = sum(1 for svc in services if svc.status == ServiceAccount.Status.ACTIVE)
        payments = Payment.objects.for_organization(request.organization).filter(
            service_account__customer__dealer=dealer,
            is_reversed=False,
            paid_at__date__gte=start,
            paid_at__date__lt=end,
        )
        collected = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        by_me = payments.filter(received_by=request.user).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        outstanding = Decimal("0.00")
        expiring = 0
        for svc in services:
            outstanding += calculate_service_outstanding(svc)[0]
            if svc.expiry_date and 0 <= (svc.expiry_date - today).days <= 3:
                expiring += 1
        return Response({
            "dealer": {
                "name": dealer.name,
                "company_name": dealer.company_name,
                "dealer_code": dealer.dealer_code,
                "commission_type": dealer.commission_type,
                "commission_rate": str(dealer.commission_rate_percentage),
            },
            "organization_name": request.organization.name,
            "month": start.strftime("%Y-%m"),
            "total_customers": Customer.objects.for_organization(request.organization).filter(dealer=dealer).count(),
            "active_connections": active,
            "suspended_connections": sum(1 for svc in services if svc.status.startswith("SUSPENDED")),
            "expiring_in_3_days": expiring,
            "total_outstanding": str(outstanding),
            "collected_this_month": str(collected),
            "collected_by_me_this_month": str(by_me),
            "commission_this_month": str(_commission(dealer, collected, active)),
        })


class DealerCustomerListView(DealerPortalView):
    def get(self, request):
        today = timezone.localdate()
        services = _dealer_services(request).order_by("customer__first_name", "service_number")
        search = request.query_params.get("search", "").strip()
        if search:
            services = services.filter(
                Q(customer__first_name__icontains=search)
                | Q(customer__last_name__icontains=search)
                | Q(customer__phone__icontains=search)
                | Q(customer__customer_number__icontains=search)
                | Q(service_number__icontains=search)
            )
        rows = [_service_row(svc, today) for svc in services[:500]]
        show = request.query_params.get("show", "").strip().lower()
        if show == "due":
            rows = [row for row in rows if Decimal(row["outstanding"]) > 0]
        elif show == "expiring":
            rows = [row for row in rows if row["days_to_expiry"] is not None and row["days_to_expiry"] <= 3]
        return Response({"count": len(rows), "results": rows})


class DealerPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1.00"))
    payment_method = serializers.ChoiceField(choices=[(m.value, m.label) for m in DEALER_PAYMENT_METHODS])
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class DealerRechargeSerializer(serializers.Serializer):
    months = serializers.IntegerField(min_value=1, max_value=MAX_RECHARGE_MONTHS)
    payment_method = serializers.ChoiceField(choices=[(m.value, m.label) for m in DEALER_PAYMENT_METHODS])
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")


def _receipt(payment: Payment) -> dict:
    return {
        "payment_id": str(payment.id),
        "payment_number": payment.payment_number,
        "amount": str(payment.amount),
        "payment_method": payment.payment_method,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }


class DealerCollectPaymentView(DealerPortalView):
    def post(self, request, service_id):
        service = _get_dealer_service(request, service_id)
        serializer = DealerPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        notes = f"Collected by dealer {request.dealer.dealer_code}. {data['notes']}".strip()
        try:
            payment = record_payment_with_allocations(
                organization=request.organization,
                actor=request.user,
                service_account_id=service.id,
                amount=data["amount"],
                payment_method=data["payment_method"],
                reference=data["reference"],
                notes=notes,
            )
        except BillingDomainError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        service.refresh_from_db()
        return Response(
            {"receipt": _receipt(payment), "service": _service_row(service, timezone.localdate())},
            status=status.HTTP_201_CREATED,
        )


class DealerRechargeView(DealerPortalView):
    def post(self, request, service_id):
        service = _get_dealer_service(request, service_id)
        profile = getattr(service, "billing_profile", None)
        if not profile or profile.billing_cycle != BillingProfile.BillingCycle.PREPAID:
            raise ValidationError({"detail": "Only prepaid connections can be recharged."})
        serializer = DealerRechargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = recharge_service(
                organization=request.organization,
                actor=request.user,
                service_account_id=service.id,
                months=data["months"],
                payment_method=data["payment_method"],
                reference=data["reference"],
                notes=f"Recharged by dealer {request.dealer.dealer_code}.",
            )
        except BillingDomainError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        service.refresh_from_db()
        return Response(
            {
                "receipt": _receipt(result.payment) if result.payment else None,
                "amount": str(result.amount),
                "new_expiry_date": result.new_expiry_date.isoformat(),
                "service": _service_row(service, timezone.localdate()),
            },
            status=status.HTTP_201_CREATED,
        )


class DealerCollectionsView(DealerPortalView):
    def get(self, request):
        start, end = _month_bounds(request.query_params.get("month"))
        payments = (
            Payment.objects.for_organization(request.organization)
            .filter(
                service_account__customer__dealer=request.dealer,
                paid_at__date__gte=start,
                paid_at__date__lt=end,
            )
            .select_related("service_account__customer", "received_by")
            .order_by("-paid_at")
        )
        rows = [
            {
                "payment_id": str(p.id),
                "payment_number": p.payment_number,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "customer_name": p.service_account.customer.full_name,
                "service_number": p.service_account.service_number,
                "amount": str(p.amount),
                "payment_method": p.payment_method,
                "reference": p.reference,
                "is_reversed": p.is_reversed,
                "collected_by_me": p.received_by_id == request.user.id,
            }
            for p in payments[:500]
        ]
        valid = [row for row in rows if not row["is_reversed"]]
        total = sum((Decimal(row["amount"]) for row in valid), Decimal("0.00"))
        mine = sum((Decimal(row["amount"]) for row in valid if row["collected_by_me"]), Decimal("0.00"))
        active = _dealer_services(request).filter(status=ServiceAccount.Status.ACTIVE).count()
        return Response({
            "month": start.strftime("%Y-%m"),
            "total_collected": str(total),
            "collected_by_me": str(mine),
            "commission": str(_commission(request.dealer, total, active)),
            "results": rows,
        })

