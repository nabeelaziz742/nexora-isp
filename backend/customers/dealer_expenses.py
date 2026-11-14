"""Expenses a dealer's employee paid on the job, and the ISP's decision on them.

The employee sends a request from the dealer portal (bike repair, food, ...).
The ISP office approves or rejects it. Approved expenses come off the
employee's cash in hand (see customers.dealer_cash). A decision is final: an
approved or rejected request cannot be reviewed again.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.dealer_portal import DealerPortalView
from customers.models import DealerEmployeeExpense
from tenancy.permissions import IsOrganizationAdminOrOwner
from tenancy.services import record_audit_log

MAX_EXPENSE_AMOUNT = Decimal("100000.00")
LIST_LIMIT = 200


def expense_row(expense: DealerEmployeeExpense) -> dict:
    employee_user = expense.employee.membership.user
    reviewer = expense.reviewed_by
    return {
        "id": str(expense.id),
        "dealer_name": expense.dealer.name,
        "dealer_code": expense.dealer.dealer_code,
        "employee_id": str(expense.employee_id),
        "employee_name": employee_user.get_full_name() or employee_user.email,
        "category": expense.category,
        "category_label": expense.get_category_display(),
        "amount": str(expense.amount),
        "spent_on": expense.spent_on.isoformat(),
        "description": expense.description,
        "status": expense.status,
        "reviewed_by": (reviewer.get_full_name() or reviewer.email) if reviewer else "",
        "reviewed_at": expense.reviewed_at.isoformat() if expense.reviewed_at else None,
        "review_note": expense.review_note,
        "created_at": expense.created_at.isoformat(),
    }


def _expenses(organization):
    return (
        DealerEmployeeExpense.objects.for_organization(organization)
        .select_related("dealer", "employee__membership__user", "reviewed_by")
    )


@transaction.atomic
def review_expense(*, organization, expense_id, actor, approve: bool, note: str = "") -> DealerEmployeeExpense:
    expense = (
        DealerEmployeeExpense.objects.for_organization(organization)
        .select_for_update()
        .filter(id=expense_id)
        .first()
    )
    if expense is None:
        raise NotFound("Expense request was not found.")
    if expense.status != DealerEmployeeExpense.Status.PENDING:
        raise ValidationError({"detail": f"This request was already {expense.get_status_display().lower()}."})
    expense.status = DealerEmployeeExpense.Status.APPROVED if approve else DealerEmployeeExpense.Status.REJECTED
    expense.reviewed_by = actor
    expense.reviewed_at = timezone.now()
    expense.review_note = note.strip()
    expense.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note"])
    record_audit_log(
        organization=organization,
        actor=actor,
        action="DEALER_EXPENSE_APPROVED" if approve else "DEALER_EXPENSE_REJECTED",
        resource_type="DealerEmployeeExpense",
        resource_id=str(expense.id),
        metadata={"amount": str(expense.amount), "category": expense.category},
    )
    return _expenses(organization).get(pk=expense.pk)


class ExpenseRequestSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=DealerEmployeeExpense.Category.choices)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("1.00"), max_value=MAX_EXPENSE_AMOUNT,
    )
    spent_on = serializers.DateField()
    description = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

    def validate_spent_on(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("The date cannot be in the future.")
        return value

    def validate(self, attrs):
        if attrs["category"] == DealerEmployeeExpense.Category.OTHER and not attrs["description"].strip():
            raise serializers.ValidationError({"description": "Write what the money was spent on."})
        return attrs


class ExpenseReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[("APPROVE", "Approve"), ("REJECT", "Reject")])
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Dealer portal: the employee asks, the dealer can see their employees' requests
# ---------------------------------------------------------------------------

class DealerExpenseView(DealerPortalView):
    def get(self, request):
        expenses = _expenses(request.organization).filter(dealer=request.dealer)
        if request.dealer_employee is not None:
            expenses = expenses.filter(employee=request.dealer_employee)
        return Response({"results": [expense_row(expense) for expense in expenses[:LIST_LIMIT]]})

    def post(self, request):
        employee = request.dealer_employee
        if employee is None:
            raise PermissionDenied("Only employees send expense requests.")
        serializer = ExpenseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        expense = DealerEmployeeExpense.objects.create(
            organization=request.organization,
            dealer=request.dealer,
            employee=employee,
            category=data["category"],
            amount=data["amount"],
            spent_on=data["spent_on"],
            description=data["description"].strip(),
        )
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_EXPENSE_REQUESTED",
            resource_type="DealerEmployeeExpense",
            resource_id=str(expense.id),
            metadata={"dealer_code": request.dealer.dealer_code, "amount": str(expense.amount)},
        )
        return Response(expense_row(_expenses(request.organization).get(pk=expense.pk)), status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# ISP office: every dealer's requests in one place
# ---------------------------------------------------------------------------

class OfficeExpenseListView(APIView):
    permission_classes = [IsOrganizationAdminOrOwner]

    def get(self, request):
        expenses = _expenses(request.organization)
        counts = {choice: 0 for choice in DealerEmployeeExpense.Status.values}
        for row in expenses.values_list("status", flat=True):
            counts[row] += 1
        wanted = request.query_params.get("status", "").strip().upper()
        if wanted in DealerEmployeeExpense.Status.values:
            expenses = expenses.filter(status=wanted)
        return Response({
            "counts": counts,
            "results": [expense_row(expense) for expense in expenses[:LIST_LIMIT]],
        })


class OfficeExpenseReviewView(APIView):
    permission_classes = [IsOrganizationAdminOrOwner]

    def post(self, request, expense_id):
        serializer = ExpenseReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense = review_expense(
            organization=request.organization,
            expense_id=expense_id,
            actor=request.user,
            approve=serializer.validated_data["decision"] == "APPROVE",
            note=serializer.validated_data["note"],
        )
        return Response(expense_row(expense))
