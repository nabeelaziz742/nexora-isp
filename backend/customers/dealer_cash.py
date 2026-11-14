"""Cash in hand: what a dealer's employee collected and has not handed over yet.

Every payment an employee records adds to their cash in hand; reversing it
takes it back off, and so does an expense the ISP approved (it was paid
from that cash). When the employee hands the money over, to their dealer or
to the ISP office, a DealerCashHandover is recorded for the full balance and
the employee is back at zero. Nothing is ever edited or deleted, so the
history shows who received how much and when.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import Payment
from customers.dealer_employees import DealerOwnerView
from customers.dealer_portal import DealerPortalView, _get_dealer
from customers.models import DealerCashHandover, DealerEmployee, DealerEmployeeExpense
from tenancy.permissions import IsOrganizationAdminOrOwner
from tenancy.services import record_audit_log

HISTORY_LIMIT = 20


def employee_cash_in_hand(employee: DealerEmployee) -> Decimal:
    collected = (
        Payment.objects.for_organization(employee.organization_id)
        .filter(
            received_by_id=employee.membership.user_id,
            service_account__customer__dealer_id=employee.dealer_id,
            is_reversed=False,
        )
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    handed_over = (
        DealerCashHandover.objects.for_organization(employee.organization_id)
        .filter(employee=employee)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    approved_expenses = (
        DealerEmployeeExpense.objects.for_organization(employee.organization_id)
        .filter(employee=employee, status=DealerEmployeeExpense.Status.APPROVED)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    return collected - handed_over - approved_expenses


def handover_row(handover: DealerCashHandover) -> dict:
    receiver = handover.received_by
    return {
        "id": str(handover.id),
        "amount": str(handover.amount),
        "received_by_type": handover.received_by_type,
        "received_by": (receiver.get_full_name() or receiver.email) if receiver else "",
        "notes": handover.notes,
        "created_at": handover.created_at.isoformat(),
    }


def handover_history(employee: DealerEmployee) -> list[dict]:
    handovers = (
        DealerCashHandover.objects.for_organization(employee.organization_id)
        .filter(employee=employee)
        .select_related("received_by")[:HISTORY_LIMIT]
    )
    return [handover_row(handover) for handover in handovers]


def employee_cash_row(employee: DealerEmployee) -> dict:
    user = employee.membership.user
    history = handover_history(employee)
    return {
        "employee_id": str(employee.id),
        "name": user.get_full_name() or user.email,
        "phone": employee.phone,
        "is_active": employee.membership.is_active and user.is_active,
        "cash_in_hand": str(employee_cash_in_hand(employee)),
        "last_handover": history[0] if history else None,
    }


@transaction.atomic
def receive_employee_cash(*, organization, employee: DealerEmployee, actor, received_by_type: str, notes: str = "") -> DealerCashHandover:
    # Lock the employee so a double click cannot record the same cash twice.
    employee = DealerEmployee.objects.select_for_update().select_related("dealer").get(pk=employee.pk)
    amount = employee_cash_in_hand(employee)
    if amount <= 0:
        raise ValidationError({"detail": "This employee has no cash to hand over."})
    handover = DealerCashHandover.objects.create(
        organization=organization,
        dealer=employee.dealer,
        employee=employee,
        amount=amount,
        received_by=actor,
        received_by_type=received_by_type,
        notes=notes.strip(),
    )
    record_audit_log(
        organization=organization,
        actor=actor,
        action="DEALER_EMPLOYEE_CASH_RECEIVED",
        resource_type="DealerEmployee",
        resource_id=str(employee.id),
        metadata={
            "dealer_code": employee.dealer.dealer_code,
            "amount": str(amount),
            "received_by_type": received_by_type,
        },
    )
    return handover


def _employees(organization, dealer):
    return (
        DealerEmployee.objects.for_organization(organization)
        .filter(dealer=dealer)
        .select_related("membership__user")
    )


def _dealer_employee(organization, dealer, employee_id) -> DealerEmployee:
    employee = _employees(organization, dealer).filter(id=employee_id).first()
    if employee is None:
        raise NotFound("Employee was not found.")
    return employee


def _team_response(organization, dealer) -> dict:
    rows = [employee_cash_row(employee) for employee in _employees(organization, dealer)]
    total = sum((Decimal(row["cash_in_hand"]) for row in rows), Decimal("0.00"))
    return {"total_cash_in_hand": str(total), "results": rows}


class CashReceivedSerializer(serializers.Serializer):
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Dealer portal
# ---------------------------------------------------------------------------

class DealerCashView(DealerPortalView):
    """An employee sees their own cash in hand; the dealer sees every employee's."""

    def get(self, request):
        employee = request.dealer_employee
        if employee is None:
            return Response(_team_response(request.organization, request.dealer))
        return Response({
            "cash_in_hand": str(employee_cash_in_hand(employee)),
            "history": handover_history(employee),
        })


class DealerEmployeeCashReceivedView(DealerOwnerView):
    def post(self, request, employee_id):
        employee = _dealer_employee(request.organization, request.dealer, employee_id)
        serializer = CashReceivedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        handover = receive_employee_cash(
            organization=request.organization,
            employee=employee,
            actor=request.user,
            received_by_type=DealerCashHandover.ReceivedBy.DEALER,
            notes=serializer.validated_data["notes"],
        )
        return Response(
            {"handover": handover_row(handover), "employee": employee_cash_row(employee)},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# ISP office (dashboard)
# ---------------------------------------------------------------------------

class OfficeDealerCashView(APIView):
    permission_classes = [IsOrganizationAdminOrOwner]

    def get(self, request, dealer_id):
        dealer = _get_dealer(request.organization, dealer_id)
        return Response(_team_response(request.organization, dealer))


class OfficeEmployeeCashReceivedView(APIView):
    permission_classes = [IsOrganizationAdminOrOwner]

    def post(self, request, dealer_id, employee_id):
        dealer = _get_dealer(request.organization, dealer_id)
        employee = _dealer_employee(request.organization, dealer, employee_id)
        serializer = CashReceivedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        handover = receive_employee_cash(
            organization=request.organization,
            employee=employee,
            actor=request.user,
            received_by_type=DealerCashHandover.ReceivedBy.ISP,
            notes=serializer.validated_data["notes"],
        )
        return Response(
            {"handover": handover_row(handover), "employee": employee_cash_row(employee)},
            status=status.HTTP_201_CREATED,
        )
