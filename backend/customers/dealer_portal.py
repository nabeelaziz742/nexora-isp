"""Dealer portal: a dealer signs in and works only with their own customers.

Access boundary (see also tenancy.authentication / tenancy.permissions):
a DEALER membership token is refused everywhere except /api/v1/dealer-portal/
and /api/v1/auth/, and every query here is filtered to customer.dealer = the
signed-in dealer.
"""
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import Payment
from billing.recharge_services import MAX_RECHARGE_MONTHS, recharge_service
from billing.services import BillingDomainError, record_payment_with_allocations, reverse_payment
from customers.dealer_payout import dealer_payout, payout_json
from customers.models import (
    BillingProfile,
    Customer,
    Dealer,
    DealerArea,
    DealerEmployee,
    Inquiry,
    InternetPackage,
    ServiceAccount,
)
from customers.services import (
    OPEN_INQUIRY_STATUSES,
    _lock_organization_for_numbering,
    generate_inquiry_number,
)
from customers.suspension_services import calculate_service_outstanding
from support.models import Complaint
from support.services import SupportDomainError, create_complaint
from tenancy.models import OrganizationMembership
from tenancy.permissions import HasActiveTenantContext, IsOrganizationAdminOrOwner, IsOrganizationOwner
from tenancy.services import record_audit_log, set_impersonation_context

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
    # Only the email: the password is made by the system and sent on WhatsApp.
    email = serializers.EmailField(required=False, allow_blank=True, default="")


class DealerPortalAccessView(APIView):
    permission_classes = [IsOrganizationAdminOrOwner]

    def get(self, request, dealer_id):
        return Response(portal_access_state(_get_dealer(request.organization, dealer_id)))

    def post(self, request, dealer_id):
        """Create the login, or resend: a new password goes to the dealer's WhatsApp."""
        from customers.dealer_login_whatsapp import send_dealer_login

        serializer = PortalAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = send_dealer_login(
            organization=request.organization,
            actor=request.user,
            dealer_id=dealer_id,
            email=serializer.validated_data["email"],
        )
        return Response(
            {**portal_access_state(result["dealer"]), "sent_to": result["sent_to"]},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, dealer_id):
        dealer = revoke_portal_access(organization=request.organization, actor=request.user, dealer_id=dealer_id)
        return Response(portal_access_state(dealer), status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Dealer side: the portal itself
# ---------------------------------------------------------------------------

class IsActiveDealer(HasActiveTenantContext):
    """The dealer's own login, or one of the dealer's employees.

    Sets request.dealer, and request.dealer_employee (None for the dealer).
    Views list the rights they need in required_rights (any one is enough);
    the dealer always has all of them. dealer_owner_only views refuse employees.
    """

    message = "An active dealer account is required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.organization_role != OrganizationMembership.Role.DEALER:
            return False
        membership = request.organization_membership
        employee = None
        dealer = (
            Dealer.objects.for_organization(request.organization)
            .filter(portal_membership=membership)
            .first()
        )
        if dealer is None:
            employee = (
                DealerEmployee.objects.for_organization(request.organization)
                .select_related("dealer__portal_membership")
                .filter(membership=membership)
                .first()
            )
            if employee is None:
                return False
            dealer = employee.dealer
            # Turning off the dealer's own login also locks out their employees.
            owner_login = dealer.portal_membership
            if owner_login is None or not owner_login.is_active:
                return False
        if dealer.status != Dealer.Status.ACTIVE:
            return False
        request.dealer = dealer
        request.dealer_employee = employee
        if employee is None:
            return True

        if not employee.can_web_login:
            self.message = "Web login is disabled for your account. Ask your dealer."
            return False

        if getattr(view, "dealer_owner_only", False):
            self.message = "Only the dealer can do this."
            return False
        required = (
            view.get_required_rights(request)
            if hasattr(view, "get_required_rights")
            else getattr(view, "required_rights", ())
        )
        if required and not any(getattr(employee, right) for right in required):
            self.message = "You do not have permission for this. Ask your dealer."
            return False
        return True


class DealerPortalView(APIView):
    allow_dealer = True
    permission_classes = [IsActiveDealer]
    required_rights: tuple[str, ...] = ()
    required_rights_by_method: dict[str, tuple[str, ...]] = {}

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        auth = getattr(request, "auth", None)
        set_impersonation_context(auth.get("impersonated_by") if auth else None)

    def finalize_response(self, request, response, *args, **kwargs):
        set_impersonation_context(None)
        return super().finalize_response(request, response, *args, **kwargs)

    def get_required_rights(self, request) -> tuple[str, ...]:
        if self.required_rights_by_method:
            return self.required_rights_by_method.get(request.method, self.required_rights)
        return self.required_rights


def dealer_rights(request) -> dict:
    employee = getattr(request, "dealer_employee", None)
    return {right: True if employee is None else getattr(employee, right) for right in DealerEmployee.RIGHTS}


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
    qs = (
        ServiceAccount.objects.for_organization(request.organization)
        .filter(customer__dealer=request.dealer)
        .select_related(
            "customer",
            "customer__assigned_dealer_employee__membership__user",
            "internet_package",
            "billing_profile",
        )
    )
    employee = getattr(request, "dealer_employee", None)
    if employee is not None and not employee.can_view_all_customers:
        qs = qs.filter(customer__assigned_dealer_employee=employee)
    return qs


def _get_dealer_service(request, service_id) -> ServiceAccount:
    service = _dealer_services(request).filter(id=service_id).first()
    if service is None:
        raise NotFound("This connection is not one of your customers.")
    return service


def _commission(dealer: Dealer, collected: Decimal, active_customers: int) -> Decimal:
    return dealer_payout(dealer, collected=collected, own_active=active_customers)["amount"]


def _service_row(service: ServiceAccount, today: date) -> dict:
    outstanding, _invoices, oldest_due = calculate_service_outstanding(service)
    profile = getattr(service, "billing_profile", None)
    is_prepaid = bool(profile and profile.billing_cycle == BillingProfile.BillingCycle.PREPAID)
    customer = service.customer
    emp = customer.assigned_dealer_employee
    emp_user = emp.membership.user if emp else None
    return {
        "service_id": str(service.id),
        "customer_id": str(customer.id),
        "service_number": service.service_number,
        "customer_number": customer.customer_number,
        "customer_name": customer.full_name,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "phone": customer.phone,
        "alternate_phone": customer.alternate_phone,
        "cnic": customer.cnic,
        "address_line": customer.address_line,
        "city": customer.city,
        "area": customer.area,
        "package_name": service.internet_package.name,
        "monthly_price": str(service.internet_package.monthly_price),
        "status": service.status,
        "customer_is_active": customer.is_active,
        "billing_mode": "PREPAID" if is_prepaid else "MONTHLY",
        "expiry_date": service.expiry_date.isoformat() if service.expiry_date else None,
        "days_to_expiry": (service.expiry_date - today).days if service.expiry_date else None,
        "outstanding": str(outstanding),
        "oldest_due_date": oldest_due.isoformat() if oldest_due else None,
        "assigned_employee_id": str(emp.id) if emp else None,
        "assigned_employee_name": (emp_user.get_full_name() or emp_user.email) if emp_user else "",
    }


class DealerSummaryView(DealerPortalView):
    def get(self, request):
        dealer = request.dealer
        employee = request.dealer_employee
        rights = dealer_rights(request)
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
        payout = dealer_payout(dealer, collected=collected, own_active=active)
        customer_qs = Customer.objects.for_organization(request.organization).filter(dealer=dealer)
        if employee is not None and not employee.can_view_all_customers:
            customer_qs = customer_qs.filter(assigned_dealer_employee=employee)
        data = {
            "me": {
                "is_dealer": employee is None,
                "employee_id": str(employee.id) if employee is not None else None,
                "name": request.user.get_full_name() or request.user.email,
                "impersonated_by": request.auth.get("impersonated_by") if getattr(request, "auth", None) else None,
                "impersonated_by_name": (
                    request.auth.get("impersonated_by_name") if getattr(request, "auth", None) else None
                ),
                "jump_kind": request.auth.get("jump_kind") if getattr(request, "auth", None) else None,
                "rights": rights,
                "right_groups": DealerEmployee.right_groups_schema(),
            },
            "dealer": {
                "name": dealer.name,
                "company_name": dealer.company_name,
                "dealer_code": dealer.dealer_code,
                "commission_type": dealer.commission_type,
                "commission_rate": str(dealer.commission_rate_percentage),
            },
            "organization_name": request.organization.name,
            "month": start.strftime("%Y-%m"),
            "show_dashboard": True if employee is None else rights["can_view_dashboard"],
            "total_customers": customer_qs.count(),
            "active_connections": active,
            "suspended_connections": sum(1 for svc in services if svc.status.startswith("SUSPENDED")),
            "expiring_in_3_days": expiring,
            "total_outstanding": str(outstanding),
            "collected_this_month": str(collected),
            "collected_by_me_this_month": str(by_me),
            "commission_this_month": str(payout["amount"]),
            "payout": payout_json(payout),
            "parent_dealer_name": dealer.parent_dealer.name if dealer.parent_dealer_id else None,
        }
        # Commission is the dealer's own business; money totals need the collections right.
        if employee is not None:
            from customers.dealer_cash import employee_cash_in_hand, handover_history

            data["me"]["cash_in_hand"] = str(employee_cash_in_hand(employee))
            last = handover_history(employee)[:1]
            data["me"]["last_cash_handover"] = last[0] if last else None
            data["dealer"].pop("commission_rate")
            data["dealer"].pop("commission_type")
            data.pop("commission_this_month")
            data.pop("payout")
            if not (rights["can_view_collections"] or rights["can_view_all_collections"]):
                data.pop("total_outstanding", None)
                data.pop("collected_this_month", None)
            elif not rights["can_view_all_collections"]:
                data["collected_this_month"] = str(by_me)
            if not rights["can_view_dashboard"]:
                for key in (
                    "total_customers",
                    "active_connections",
                    "suspended_connections",
                    "expiring_in_3_days",
                    "total_outstanding",
                    "collected_this_month",
                    "collected_by_me_this_month",
                ):
                    data.pop(key, None)
        return Response(data)


class DealerCustomerListView(DealerPortalView):
    # Collecting, recharging, editing, deactivating, ledger or export need the list.
    required_rights = (
        "can_view_customers",
        "can_view_all_customers",
        "can_collect_payments",
        "can_recharge",
        "can_edit_customers",
        "can_deactivate_customers",
        "can_view_ledger",
        "can_export_customers",
    )

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
    paid_at = serializers.CharField(max_length=40, required=False, allow_blank=True, allow_null=True, default=None)


class DealerRechargeSerializer(serializers.Serializer):
    months = serializers.IntegerField(min_value=1, max_value=MAX_RECHARGE_MONTHS)
    payment_method = serializers.ChoiceField(choices=[(m.value, m.label) for m in DEALER_PAYMENT_METHODS])
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    paid_at = serializers.CharField(max_length=40, required=False, allow_blank=True, allow_null=True, default=None)


def _resolve_dealer_paid_at(request, raw_paid_at: str | None) -> tuple[datetime | None, date | None]:
    """Validate optional payment date (up to 7 days back, never future) when permitted."""
    if raw_paid_at is None or not str(raw_paid_at).strip():
        return None, None
    if request.dealer_employee is not None and not request.dealer_employee.can_change_payment_date:
        raise PermissionDenied("You do not have permission to change the payment date.")
    text = str(raw_paid_at).strip()
    tz = timezone.get_current_timezone()
    try:
        if len(text) == 10:
            parsed_date = date.fromisoformat(text)
            dt = timezone.make_aware(datetime.combine(parsed_date, timezone.localtime().time().replace(microsecond=0)), tz)
        else:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, tz)
    except ValueError as exc:
        raise ValidationError({"paid_at": "Use YYYY-MM-DD format for payment date."}) from exc

    target_date = timezone.localtime(dt).date()
    today = timezone.localdate()
    if target_date > today:
        raise ValidationError({"paid_at": "Payment date cannot be in the future."})
    if (today - target_date).days > 7:
        raise ValidationError({"paid_at": "Payment date cannot be more than 7 days in the past."})
    return dt, target_date


def _audit_backdated_payment(request, payment: Payment, target_date: date | None) -> None:
    if target_date is not None and target_date < timezone.localdate():
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_PAYMENT_BACKDATED",
            resource_type="Payment",
            resource_id=str(payment.id),
            metadata={
                "dealer_code": request.dealer.dealer_code,
                "payment_number": payment.payment_number,
                "paid_at": target_date.isoformat(),
                "amount": str(payment.amount),
            },
        )


def _receipt(payment: Payment) -> dict:
    return {
        "payment_id": str(payment.id),
        "payment_number": payment.payment_number,
        "amount": str(payment.amount),
        "payment_method": payment.payment_method,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }


def _collector_label(request) -> str:
    base = (
        f"dealer {request.dealer.dealer_code}"
        if request.dealer_employee is None
        else f"{request.user.get_full_name() or request.user.email} for dealer {request.dealer.dealer_code}"
    )
    auth = getattr(request, "auth", None)
    imp_name = auth.get("impersonated_by_name") if auth else None
    return f"{base} (via {imp_name})" if imp_name else base


class DealerCollectPaymentView(DealerPortalView):
    required_rights = ("can_collect_payments",)

    def post(self, request, service_id):
        service = _get_dealer_service(request, service_id)
        serializer = DealerPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        paid_at_dt, target_date = _resolve_dealer_paid_at(request, data.get("paid_at"))
        notes = f"Collected by {_collector_label(request)}. {data['notes']}".strip()
        try:
            payment = record_payment_with_allocations(
                organization=request.organization,
                actor=request.user,
                service_account_id=service.id,
                amount=data["amount"],
                payment_method=data["payment_method"],
                reference=data["reference"],
                notes=notes,
                paid_at=paid_at_dt,
            )
        except BillingDomainError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        _audit_backdated_payment(request, payment, target_date)
        service.refresh_from_db()
        return Response(
            {"receipt": _receipt(payment), "service": _service_row(service, timezone.localdate())},
            status=status.HTTP_201_CREATED,
        )


class DealerRechargeView(DealerPortalView):
    required_rights = ("can_recharge",)

    def post(self, request, service_id):
        service = _get_dealer_service(request, service_id)
        profile = getattr(service, "billing_profile", None)
        if not profile or profile.billing_cycle != BillingProfile.BillingCycle.PREPAID:
            raise ValidationError({"detail": "Only prepaid connections can be recharged."})
        serializer = DealerRechargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        paid_at_dt, target_date = _resolve_dealer_paid_at(request, data.get("paid_at"))
        try:
            result = recharge_service(
                organization=request.organization,
                actor=request.user,
                service_account_id=service.id,
                months=data["months"],
                payment_method=data["payment_method"],
                reference=data["reference"],
                notes=f"Recharged by {_collector_label(request)}.",
                paid_at=paid_at_dt,
            )
        except BillingDomainError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        if result.payment:
            _audit_backdated_payment(request, result.payment, target_date)
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


class DealerPaymentReverseSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

    def validate_reason(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Reason is required.")
        return cleaned


class DealerPaymentReverseView(DealerPortalView):
    required_rights = ("can_reverse_payments",)

    def post(self, request, payment_id):
        qs = (
            Payment.objects.for_organization(request.organization)
            .filter(id=payment_id, service_account__customer__dealer=request.dealer)
            .select_related("service_account__customer")
        )
        employee = request.dealer_employee
        if employee is not None and not employee.can_view_all_customers:
            qs = qs.filter(service_account__customer__assigned_dealer_employee=employee)
        payment = qs.first()
        if payment is None:
            raise NotFound("Payment was not found for your account.")
        if payment.is_reversed:
            raise ValidationError({"detail": "This payment is already reversed."})

        paid_date = timezone.localtime(payment.paid_at).date() if payment.paid_at else timezone.localdate()
        if (timezone.localdate() - paid_date).days > 7:
            raise ValidationError({"detail": "Only payments from the last 7 days can be reversed."})

        serializer = DealerPaymentReverseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]
        reference = serializer.validated_data["reference"]
        try:
            reversed_payment = reverse_payment(
                organization=request.organization,
                actor=request.user,
                payment_id=payment.id,
                reversal_reason=f"Dealer reversal ({request.dealer.dealer_code}): {reason}",
                reversal_reference=reference,
            )
        except BillingDomainError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(
            _receipt(reversed_payment)
            | {
                "is_reversed": reversed_payment.is_reversed,
                "reversal_reason": reversed_payment.reversal_reason,
                "reversed_at": reversed_payment.reversed_at.isoformat() if reversed_payment.reversed_at else None,
            }
        )


class DealerCollectionsView(DealerPortalView):
    required_rights = ("can_view_collections", "can_view_all_collections")

    def get(self, request):
        start, end = _month_bounds(request.query_params.get("month"))
        employee = request.dealer_employee
        can_see_all_collections = employee is None or employee.can_view_all_collections
        can_reverse_right = employee is None or employee.can_reverse_payments
        can_see_all_customers = employee is None or employee.can_view_all_customers
        today = timezone.localdate()

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
        if not can_see_all_collections:
            payments = payments.filter(received_by=request.user)

        rows = []
        for p in payments[:500]:
            customer = p.service_account.customer
            paid_date = timezone.localtime(p.paid_at).date() if p.paid_at else today
            customer_in_scope = can_see_all_customers or (
                employee is not None and customer.assigned_dealer_employee_id == employee.id
            )
            rows.append({
                "payment_id": str(p.id),
                "payment_number": p.payment_number,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "customer_name": customer.full_name,
                "service_number": p.service_account.service_number,
                "amount": str(p.amount),
                "payment_method": p.payment_method,
                "reference": p.reference,
                "is_reversed": p.is_reversed,
                "reversal_reason": p.reversal_reason,
                "reversed_at": p.reversed_at.isoformat() if p.reversed_at else None,
                "can_reverse": bool(
                    can_reverse_right
                    and customer_in_scope
                    and not p.is_reversed
                    and (today - paid_date).days <= 7
                ),
                "collected_by_me": p.received_by_id == request.user.id,
                "collected_by": (p.received_by.get_full_name() or p.received_by.email) if p.received_by else "Office",
            })

        valid = [row for row in rows if not row["is_reversed"]]
        total = sum((Decimal(row["amount"]) for row in valid), Decimal("0.00"))
        mine = sum((Decimal(row["amount"]) for row in valid if row["collected_by_me"]), Decimal("0.00"))

        by_person_list = []
        if can_see_all_collections:
            by_person: dict[str, Decimal] = {}
            for row in valid:
                by_person[row["collected_by"]] = by_person.get(row["collected_by"], Decimal("0.00")) + Decimal(row["amount"])
            by_person_list = [
                {"name": name, "total": str(amount)}
                for name, amount in sorted(by_person.items(), key=lambda item: -item[1])
            ]

        payload = {
            "month": start.strftime("%Y-%m"),
            "total_collected": str(total),
            "collected_by_me": str(mine),
            "can_view_all_collections": can_see_all_collections,
            "by_person": by_person_list,
            "results": rows,
        }
        if employee is None:
            active = _dealer_services(request).filter(status=ServiceAccount.Status.ACTIVE).count()
            payload["commission"] = str(_commission(request.dealer, total, active))
        return Response(payload)



# ---------------------------------------------------------------------------
# Dealer adds a new customer: it reaches the office as a dealer inquiry
# ---------------------------------------------------------------------------
# The office still checks feasibility and creates the PPPoE account, so a
# dealer request becomes an Inquiry (source DEALER, linked to the dealer).
# Converting it keeps the dealer on the new customer.

@transaction.atomic
def create_dealer_customer_request(*, organization, dealer: Dealer, actor, data: dict) -> Inquiry:
    organization = _lock_organization_for_numbering(organization=organization)
    phone = data["phone"].strip()
    open_duplicate = (
        Inquiry.objects.for_organization(organization)
        .filter(phone=phone, status__in=OPEN_INQUIRY_STATUSES)
        .exists()
    )
    if open_duplicate or Customer.objects.for_organization(organization).filter(phone=phone).exists():
        raise ValidationError({"phone": "A customer or open request with this phone number already exists."})

    package = None
    if data.get("preferred_package"):
        package = (
            InternetPackage.objects.for_organization(organization)
            .filter(id=data["preferred_package"], is_active=True)
            .first()
        )
        if package is None:
            raise ValidationError({"preferred_package": "Selected package is not available."})

    inquiry = Inquiry.objects.create(
        organization=organization,
        inquiry_number=generate_inquiry_number(organization=organization),
        full_name=data["full_name"].strip(),
        phone=phone,
        alternate_phone=data.get("alternate_phone", "").strip(),
        email=data.get("email", "").strip().lower(),
        cnic=data.get("cnic", "").strip(),
        address_line=data["address_line"].strip(),
        city=data["city"].strip(),
        area=data.get("area", "").strip(),
        preferred_package=package,
        connection_type=data.get("connection_type") or Inquiry.ConnectionType.FIBER,
        source=Inquiry.Source.DEALER,
        dealer=dealer,
        status=Inquiry.Status.NEW,
        notes=f"Submitted by dealer {dealer.dealer_code} ({dealer.name}). {data.get('notes', '').strip()}".strip(),
        created_by=actor,
    )
    record_audit_log(
        organization=organization,
        actor=actor,
        action="DEALER_CUSTOMER_REQUESTED",
        resource_type="Inquiry",
        resource_id=str(inquiry.id),
        metadata={"inquiry_number": inquiry.inquiry_number, "dealer_code": dealer.dealer_code},
    )
    return inquiry


class DealerCustomerRequestSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=30)
    alternate_phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    cnic = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    address_line = serializers.CharField(max_length=500)
    city = serializers.CharField(max_length=100)
    area = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    preferred_package = serializers.UUIDField(required=False, allow_null=True)
    connection_type = serializers.ChoiceField(choices=Inquiry.ConnectionType.choices, required=False)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


REQUEST_STATUS_LABELS = {
    Inquiry.Status.CONVERTED: "Connected",
    Inquiry.Status.LOST: "Not proceeding",
    Inquiry.Status.CANCELLED: "Cancelled",
    Inquiry.Status.NOT_FEASIBLE: "Not possible at this address",
}


def _request_row(inquiry: Inquiry) -> dict:
    return {
        "id": str(inquiry.id),
        "inquiry_number": inquiry.inquiry_number,
        "full_name": inquiry.full_name,
        "phone": inquiry.phone,
        "area": inquiry.area,
        "package_name": inquiry.preferred_package.name if inquiry.preferred_package else "",
        "status": inquiry.status,
        "status_label": REQUEST_STATUS_LABELS.get(inquiry.status, "Pending with office"),
        "created_at": inquiry.created_at.isoformat(),
    }


class DealerCustomerRequestView(DealerPortalView):
    required_rights = ("can_request_customers",)

    def get(self, request):
        inquiries = (
            Inquiry.objects.for_organization(request.organization)
            .filter(dealer=request.dealer)
            .select_related("preferred_package")
            .order_by("-created_at")[:200]
        )
        packages = InternetPackage.objects.for_organization(request.organization).filter(is_active=True).order_by("monthly_price")
        areas = (
            DealerArea.objects.for_organization(request.organization)
            .filter(dealer=request.dealer, is_active=True)
            .order_by("name")
        )
        return Response({
            "results": [_request_row(inquiry) for inquiry in inquiries],
            "packages": [
                {"id": str(p.id), "name": p.name, "monthly_price": str(p.monthly_price)} for p in packages
            ],
            "areas": [
                {"id": str(a.id), "name": a.name, "city": a.city} for a in areas
            ],
            "default_city": request.dealer.city or request.organization.city,
        })

    def post(self, request):
        serializer = DealerCustomerRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = create_dealer_customer_request(
            organization=request.organization,
            dealer=request.dealer,
            actor=request.user,
            data=serializer.validated_data,
        )
        return Response(_request_row(inquiry), status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Dealer areas (separate from ISP areas) & active ISP packages (read-only)
# ---------------------------------------------------------------------------

def _area_row(area: DealerArea) -> dict:
    return {
        "id": str(area.id),
        "name": area.name,
        "city": area.city,
        "notes": area.notes,
        "is_active": area.is_active,
        "created_at": area.created_at.isoformat(),
        "updated_at": area.updated_at.isoformat(),
    }


class DealerAreaSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    city = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Area name cannot be blank.")
        return cleaned


def _get_dealer_area(request, area_id) -> DealerArea:
    area = (
        DealerArea.objects.for_organization(request.organization)
        .filter(id=area_id, dealer=request.dealer)
        .first()
    )
    if area is None:
        raise NotFound("Area was not found.")
    return area


class DealerAreaListCreateView(DealerPortalView):
    required_rights_by_method = {
        "GET": ("can_view_areas", "can_manage_areas"),
        "POST": ("can_manage_areas",),
    }

    def get(self, request):
        areas = (
            DealerArea.objects.for_organization(request.organization)
            .filter(dealer=request.dealer)
            .order_by("name")
        )
        status_filter = request.query_params.get("status", "").strip().lower()
        if status_filter == "active":
            areas = areas.filter(is_active=True)
        elif status_filter == "inactive":
            areas = areas.filter(is_active=False)
        return Response({"results": [_area_row(a) for a in areas]})

    def post(self, request):
        serializer = DealerAreaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if (
            DealerArea.objects.for_organization(request.organization)
            .filter(dealer=request.dealer, name__iexact=data["name"])
            .exists()
        ):
            raise ValidationError({"name": "An area with this name already exists."})
        area = DealerArea.objects.create(
            organization=request.organization,
            dealer=request.dealer,
            name=data["name"],
            city=data["city"].strip(),
            notes=data["notes"].strip(),
            is_active=data.get("is_active", True),
        )
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_AREA_CREATED",
            resource_type="DealerArea",
            resource_id=str(area.id),
            metadata={"dealer_code": request.dealer.dealer_code, "name": area.name},
        )
        return Response(_area_row(area), status=status.HTTP_201_CREATED)


class DealerAreaDetailView(DealerPortalView):
    required_rights = ("can_manage_areas",)

    def patch(self, request, area_id):
        area = _get_dealer_area(request, area_id)
        serializer = DealerAreaSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "name" in data:
            if (
                DealerArea.objects.for_organization(request.organization)
                .filter(dealer=request.dealer, name__iexact=data["name"])
                .exclude(pk=area.pk)
                .exists()
            ):
                raise ValidationError({"name": "An area with this name already exists."})
            area.name = data["name"]
        if "city" in data:
            area.city = data["city"].strip()
        if "notes" in data:
            area.notes = data["notes"].strip()
        if "is_active" in data:
            area.is_active = data["is_active"]
        area.save()
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_AREA_UPDATED",
            resource_type="DealerArea",
            resource_id=str(area.id),
            metadata={"dealer_code": request.dealer.dealer_code, "name": area.name, "is_active": area.is_active},
        )
        return Response(_area_row(area))


class DealerAreaStatusToggleView(DealerPortalView):
    required_rights = ("can_manage_areas",)

    def post(self, request, area_id):
        area = _get_dealer_area(request, area_id)
        area.is_active = not area.is_active
        area.save(update_fields=["is_active", "updated_at"])
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_AREA_STATUS_CHANGED",
            resource_type="DealerArea",
            resource_id=str(area.id),
            metadata={"dealer_code": request.dealer.dealer_code, "name": area.name, "is_active": area.is_active},
        )
        return Response(_area_row(area))

    def patch(self, request, area_id):
        return self.post(request, area_id)


class DealerPackageListView(DealerPortalView):
    required_rights = ("can_view_packages",)

    def get(self, request):
        packages = (
            InternetPackage.objects.for_organization(request.organization)
            .filter(is_active=True)
            .order_by("monthly_price", "name")
        )
        return Response({
            "results": [
                {
                    "id": str(pkg.id),
                    "name": pkg.name,
                    "code": pkg.code,
                    "download_speed_mbps": pkg.download_speed_mbps,
                    "upload_speed_mbps": pkg.upload_speed_mbps,
                    "monthly_price": str(pkg.monthly_price),
                    "description": pkg.description,
                }
                for pkg in packages
            ]
        })


# ---------------------------------------------------------------------------
# Dealer complaints (logged into ISP Support; status read-only in dealer portal)
# ---------------------------------------------------------------------------

def _complaint_row(complaint: Complaint) -> dict:
    return {
        "id": str(complaint.id),
        "complaint_number": complaint.complaint_number,
        "customer_id": str(complaint.customer_id),
        "customer_name": complaint.customer.full_name,
        "customer_phone": complaint.customer.phone,
        "service_id": str(complaint.service_account_id) if complaint.service_account_id else None,
        "service_number": complaint.service_account.service_number if complaint.service_account else "",
        "category": complaint.category,
        "category_label": complaint.get_category_display(),
        "priority": complaint.priority,
        "priority_label": complaint.get_priority_display(),
        "status": complaint.status,
        "status_label": complaint.get_status_display(),
        "source": complaint.source,
        "subject": complaint.subject,
        "description": complaint.description,
        "resolution_summary": complaint.resolution_summary,
        "created_at": complaint.created_at.isoformat(),
        "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
        "closed_at": complaint.closed_at.isoformat() if complaint.closed_at else None,
    }


class DealerComplaintCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    service_account_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    category = serializers.ChoiceField(choices=Complaint.Category.choices, default=Complaint.Category.CONNECTIVITY)
    priority = serializers.ChoiceField(choices=Complaint.Priority.choices, default=Complaint.Priority.MEDIUM)
    subject = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=2000)

    def validate_subject(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Subject is required.")
        return cleaned

    def validate_description(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Description is required.")
        return cleaned


class DealerComplaintListCreateView(DealerPortalView):
    required_rights = ("can_manage_complaints",)

    def get(self, request):
        employee = request.dealer_employee
        complaints = (
            Complaint.objects.for_organization(request.organization)
            .filter(customer__dealer=request.dealer)
            .select_related("customer", "service_account")
            .order_by("-created_at")
        )
        if employee is not None and not employee.can_view_all_customers:
            complaints = complaints.filter(customer__assigned_dealer_employee=employee)

        status_filter = request.query_params.get("status", "").strip()
        if status_filter:
            complaints = complaints.filter(status=status_filter)

        services = list(_dealer_services(request).order_by("customer__first_name", "service_number")[:500])
        return Response({
            "results": [_complaint_row(c) for c in complaints[:200]],
            "customers": [
                {
                    "customer_id": str(svc.customer_id),
                    "service_id": str(svc.id),
                    "customer_name": svc.customer.full_name,
                    "service_number": svc.service_number,
                    "phone": svc.customer.phone,
                }
                for svc in services
            ],
            "categories": [{"value": v, "label": label} for v, label in Complaint.Category.choices],
            "priorities": [{"value": v, "label": label} for v, label in Complaint.Priority.choices],
        })

    def post(self, request):
        serializer = DealerComplaintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer_qs = Customer.objects.for_organization(request.organization).filter(
            id=data["customer_id"],
            dealer=request.dealer,
        )
        employee = request.dealer_employee
        if employee is not None and not employee.can_view_all_customers:
            customer_qs = customer_qs.filter(assigned_dealer_employee=employee)
        customer = customer_qs.first()
        if customer is None:
            raise NotFound("Customer was not found for your account.")

        service_id = data.get("service_account_id")
        if service_id is not None:
            svc = (
                ServiceAccount.objects.for_organization(request.organization)
                .filter(id=service_id, customer=customer)
                .first()
            )
            if svc is None:
                raise NotFound("Connection was not found for this customer.")
        else:
            cust_services = list(
                ServiceAccount.objects.for_organization(request.organization)
                .filter(customer=customer)
                .values_list("id", flat=True)[:2]
            )
            service_id = cust_services[0] if len(cust_services) == 1 else None

        try:
            result = create_complaint(
                organization=request.organization,
                customer_id=customer.id,
                service_account_id=service_id,
                category=data["category"],
                priority=data["priority"],
                subject=data["subject"],
                description=data["description"],
                source=Complaint.Source.DEALER,
                created_by=request.user,
            )
        except SupportDomainError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        complaint = (
            Complaint.objects.for_organization(request.organization)
            .select_related("customer", "service_account")
            .get(id=result.complaint.id)
        )
        return Response(_complaint_row(complaint), status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Company Info & About
# ---------------------------------------------------------------------------

class DealerCompanyInfoSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False)
    alternate_phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    address_line = serializers.CharField(max_length=500, required=False)
    city = serializers.CharField(max_length=150, required=False)
    area = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_phone(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Phone cannot be blank.")
        return cleaned

    def validate_address_line(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Address cannot be blank.")
        return cleaned

    def validate_city(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("City cannot be blank.")
        return cleaned


def _company_info_payload(dealer: Dealer, can_edit: bool) -> dict:
    return {
        "dealer_code": dealer.dealer_code,
        "name": dealer.name,
        "company_name": dealer.company_name,
        "phone": dealer.phone,
        "alternate_phone": dealer.alternate_phone,
        "email": dealer.email,
        "address_line": dealer.address_line,
        "city": dealer.city,
        "area": dealer.area,
        "status": dealer.status,
        "can_edit": can_edit,
    }


class DealerCompanyInfoView(DealerPortalView):
    required_rights_by_method = {
        "GET": (),
        "PATCH": ("can_edit_company_info",),
    }

    def get(self, request):
        can_edit = request.dealer_employee is None or request.dealer_employee.can_edit_company_info
        return Response(_company_info_payload(request.dealer, can_edit))

    @transaction.atomic
    def patch(self, request):
        serializer = DealerCompanyInfoSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        dealer = request.dealer
        changes = {}
        for field in ("company_name", "phone", "alternate_phone", "email", "address_line", "city", "area"):
            if field in data:
                new_val = data[field].strip() if isinstance(data[field], str) else data[field]
                old_val = getattr(dealer, field)
                if new_val != old_val:
                    changes[field] = {"from": old_val, "to": new_val}
                    setattr(dealer, field, new_val)

        if changes:
            dealer.save()
            record_audit_log(
                organization=request.organization,
                actor=request.user,
                action="DEALER_COMPANY_INFO_UPDATED",
                resource_type="Dealer",
                resource_id=str(dealer.id),
                metadata={"dealer_code": dealer.dealer_code, "changes": changes},
            )
        return Response(_company_info_payload(dealer, can_edit=True))


class DealerAboutView(DealerPortalView):
    def get(self, request):
        org = request.organization
        return Response({
            "organization": {
                "name": org.name,
                "phone": org.phone,
                "email": org.email,
                "address": org.address,
                "city": org.city,
            },
            "dealer_code": request.dealer.dealer_code,
            "powered_by": "Powered by Nexora ISP",
        })


# ---------------------------------------------------------------------------
# Jump (impersonate) into dealer or employee panel
# ---------------------------------------------------------------------------

class DealerJumpView(APIView):
    """ISP OWNER opens a dealer's portal without knowing their password."""

    permission_classes = [IsOrganizationOwner]

    def post(self, request, dealer_id):
        from accounts.api.jump import issue_jump_tokens

        auth = getattr(request, "auth", None)
        if auth and auth.get("impersonated_by"):
            raise ValidationError({"detail": "Exit your current jump session before jumping again."})

        dealer = _get_dealer(request.organization, dealer_id)
        if dealer.status != Dealer.Status.ACTIVE:
            raise ValidationError({"detail": "Only active dealers can be opened."})

        membership = dealer.portal_membership
        if membership is None or not membership.is_active or not membership.user.is_active:
            raise ValidationError({"detail": "Enable portal login for this dealer first."})

        tokens = issue_jump_tokens(
            target_user=membership.user,
            organization=request.organization,
            actor_user=request.user,
            jump_kind="DEALER",
        )
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_PORTAL_JUMP_STARTED",
            resource_type="Dealer",
            resource_id=str(dealer.id),
            metadata={
                "dealer_code": dealer.dealer_code,
                "target_user_id": str(membership.user_id),
                "impersonated_by": str(request.user.id),
            },
        )
        return Response(tokens | {"target_name": dealer.name})


class DealerEmployeeJumpView(DealerPortalView):
    """Dealer's own login opens one of their active employees' portals."""

    dealer_owner_only = True

    def post(self, request, employee_id):
        from accounts.api.jump import issue_jump_tokens

        employee = (
            DealerEmployee.objects.for_organization(request.organization)
            .filter(id=employee_id, dealer=request.dealer)
            .select_related("membership__user")
            .first()
        )
        if employee is None:
            raise NotFound("Employee was not found for this dealer.")
        if not employee.membership.is_active or not employee.membership.user.is_active:
            raise ValidationError({"detail": "This employee login is turned off."})

        tokens = issue_jump_tokens(
            target_user=employee.membership.user,
            organization=request.organization,
            actor_user=request.user,
            jump_kind="DEALER_EMPLOYEE",
        )
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_EMPLOYEE_JUMP_STARTED",
            resource_type="DealerEmployee",
            resource_id=str(employee.id),
            metadata={
                "dealer_code": request.dealer.dealer_code,
                "employee_id": str(employee.id),
                "target_user_id": str(employee.membership.user_id),
                "impersonated_by": str(request.user.id),
            },
        )
        return Response(tokens)



