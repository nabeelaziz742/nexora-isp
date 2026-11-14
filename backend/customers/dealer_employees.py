"""A dealer's own employees: the dealer creates their logins and decides what each may do.

Employees sign in like the dealer (DEALER membership role, same portal) and are
always limited to that dealer's customers. Only the dealer's own login manages
them; an employee can never create or change another employee.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from customers.dealer_portal import DealerPortalView
from customers.models import DealerEmployee
from tenancy.models import OrganizationMembership
from tenancy.services import record_audit_log

User = get_user_model()

MAX_EMPLOYEES_PER_DEALER = 25


def employee_row(employee: DealerEmployee) -> dict:
    user = employee.membership.user
    return {
        "id": str(employee.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name() or user.email,
        "email": user.email,
        "phone": employee.phone,
        "is_active": employee.membership.is_active and user.is_active,
        "rights": {right: getattr(employee, right) for right in DealerEmployee.RIGHTS},
        "created_at": employee.created_at.isoformat(),
    }


def _check_password(password: str, user=None) -> None:
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)}) from exc


def _apply_rights(employee: DealerEmployee, rights: dict) -> None:
    for right in DealerEmployee.RIGHTS:
        if right in rights:
            setattr(employee, right, bool(rights[right]))


def _get_employee(request, employee_id) -> DealerEmployee:
    employee = (
        DealerEmployee.objects.for_organization(request.organization)
        .select_related("membership__user")
        .filter(id=employee_id, dealer=request.dealer)
        .first()
    )
    if employee is None:
        raise NotFound("Employee was not found.")
    return employee


@transaction.atomic
def create_dealer_employee(*, organization, dealer, actor, data: dict) -> DealerEmployee:
    if DealerEmployee.objects.for_organization(organization).filter(dealer=dealer).count() >= MAX_EMPLOYEES_PER_DEALER:
        raise ValidationError({"detail": f"A dealer can have at most {MAX_EMPLOYEES_PER_DEALER} employees."})
    email = data["email"].strip().lower()
    # Always a fresh account: never attach the dealer portal to an existing user.
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError({"email": "This email is already used by another account."})
    _check_password(data["password"])

    user = User.objects.create_user(
        username=email,
        email=email,
        password=data["password"],
        first_name=data["first_name"].strip()[:150],
        last_name=data.get("last_name", "").strip()[:150],
        is_active=True,
    )
    membership = OrganizationMembership.objects.create(
        organization=organization,
        user=user,
        role=OrganizationMembership.Role.DEALER,
        is_active=True,
    )
    employee = DealerEmployee(
        organization=organization,
        dealer=dealer,
        membership=membership,
        phone=data.get("phone", "").strip(),
    )
    _apply_rights(employee, data.get("rights", {}))
    employee.save()
    record_audit_log(
        organization=organization,
        actor=actor,
        action="DEALER_EMPLOYEE_CREATED",
        resource_type="DealerEmployee",
        resource_id=str(employee.id),
        metadata={"dealer_code": dealer.dealer_code, "email": email},
    )
    return employee


@transaction.atomic
def update_dealer_employee(*, organization, employee: DealerEmployee, actor, data: dict) -> DealerEmployee:
    user = employee.membership.user
    user_fields = []
    for field in ("first_name", "last_name"):
        if field in data:
            setattr(user, field, data[field].strip()[:150])
            user_fields.append(field)
    if user_fields:
        user.save(update_fields=user_fields)
    if "phone" in data:
        employee.phone = data["phone"].strip()
    _apply_rights(employee, data.get("rights", {}))
    employee.save()
    if "is_active" in data and employee.membership.is_active != data["is_active"]:
        employee.membership.is_active = data["is_active"]
        employee.membership.save(update_fields=["is_active", "updated_at"])
    record_audit_log(
        organization=organization,
        actor=actor,
        action="DEALER_EMPLOYEE_UPDATED",
        resource_type="DealerEmployee",
        resource_id=str(employee.id),
        metadata={
            "dealer_code": employee.dealer.dealer_code,
            "is_active": employee.membership.is_active,
            "rights": {right: getattr(employee, right) for right in DealerEmployee.RIGHTS},
        },
    )
    return employee


class RightsSerializer(serializers.Serializer):
    can_view_customers = serializers.BooleanField(required=False)
    can_collect_payments = serializers.BooleanField(required=False)
    can_recharge = serializers.BooleanField(required=False)
    can_request_customers = serializers.BooleanField(required=False)
    can_view_collections = serializers.BooleanField(required=False)


class EmployeeCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=8, max_length=128)
    rights = RightsSerializer(required=False, default=dict)


class EmployeeUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    rights = RightsSerializer(required=False, default=dict)


class EmployeePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=8, max_length=128)


class DealerOwnerView(DealerPortalView):
    dealer_owner_only = True


class DealerEmployeeListView(DealerOwnerView):
    def get(self, request):
        employees = (
            DealerEmployee.objects.for_organization(request.organization)
            .filter(dealer=request.dealer)
            .select_related("membership__user")
        )
        return Response({
            "results": [employee_row(employee) for employee in employees],
            "max_employees": MAX_EMPLOYEES_PER_DEALER,
        })

    def post(self, request):
        serializer = EmployeeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = create_dealer_employee(
            organization=request.organization,
            dealer=request.dealer,
            actor=request.user,
            data=serializer.validated_data,
        )
        return Response(employee_row(employee), status=status.HTTP_201_CREATED)


class DealerEmployeeDetailView(DealerOwnerView):
    def patch(self, request, employee_id):
        employee = _get_employee(request, employee_id)
        serializer = EmployeeUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        employee = update_dealer_employee(
            organization=request.organization,
            employee=employee,
            actor=request.user,
            data=serializer.validated_data,
        )
        return Response(employee_row(employee))


class DealerEmployeePasswordView(DealerOwnerView):
    def post(self, request, employee_id):
        employee = _get_employee(request, employee_id)
        serializer = EmployeePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = employee.membership.user
        _check_password(serializer.validated_data["password"], user)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_EMPLOYEE_PASSWORD_RESET",
            resource_type="DealerEmployee",
            resource_id=str(employee.id),
            metadata={"dealer_code": request.dealer.dealer_code},
        )
        return Response({"detail": "Password changed."})
