"""Dealer portal Accounts overview and Cash Journal (manual entries + derived ledger)."""
import io
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from accounting.models import DealerSettlement
from billing.models import Payment
from customers.dealer_cash import employee_cash_in_hand
from customers.dealer_payout import dealer_payout, payout_json
from customers.dealer_portal import DealerPortalView, _month_bounds
from customers.import_views import XLSX_CONTENT_TYPE
from customers.models import (
    DealerEmployee,
    DealerEmployeeExpense,
    DealerJournalEntry,
    ServiceAccount,
)
from tenancy.services import record_audit_log


def _parse_date_range(request) -> tuple[date, date, str]:
    """Return inclusive start_date, exclusive end_date, and label."""
    from_raw = request.query_params.get("from", "").strip()
    to_raw = request.query_params.get("to", "").strip()
    if from_raw or to_raw:
        try:
            start = date.fromisoformat(from_raw) if from_raw else _month_bounds(None)[0]
            end_inclusive = date.fromisoformat(to_raw) if to_raw else timezone.localdate()
        except ValueError as exc:
            raise ValidationError({"detail": "Use YYYY-MM-DD for dates."}) from exc
        if end_inclusive < start:
            raise ValidationError({"detail": "End date cannot be before start date."})
        from datetime import timedelta

        return start, end_inclusive + timedelta(days=1), f"{start.isoformat()}..{end_inclusive.isoformat()}"

    month_param = request.query_params.get("month", "").strip() or None
    start, end = _month_bounds(month_param)
    return start, end, start.strftime("%Y-%m")


def _build_journal_rows(request, start: date, end: date, kind_filter: str = "") -> list[dict]:
    dealer = request.dealer
    org = request.organization
    employee = getattr(request, "dealer_employee", None)
    can_void_right = employee is None or employee.can_void_journal_entries
    rows: list[dict] = []

    manual_qs = (
        DealerJournalEntry.objects.for_organization(org)
        .filter(dealer=dealer, date__gte=start, date__lt=end)
        .select_related("created_by", "voided_by")
    )
    if kind_filter:
        manual_qs = manual_qs.filter(kind=kind_filter)
    for entry in manual_qs:
        rows.append({
            "id": str(entry.id),
            "date": entry.date.isoformat(),
            "sort_ts": entry.created_at.isoformat(),
            "source": "MANUAL",
            "source_label": "Manual Entry",
            "kind": entry.kind,
            "amount": str(entry.amount),
            "description": entry.description,
            "recorded_by": (entry.created_by.get_full_name() or entry.created_by.email) if entry.created_by else "Dealer",
            "is_manual": True,
            "is_void": entry.is_void,
            "void_reason": entry.void_reason,
            "voided_at": entry.voided_at.isoformat() if entry.voided_at else None,
            "can_void": bool(can_void_right and not entry.is_void),
        })

    if not kind_filter or kind_filter == DealerJournalEntry.Kind.INCOME:
        payments_qs = (
            Payment.objects.for_organization(org)
            .filter(
                service_account__customer__dealer=dealer,
                is_reversed=False,
                paid_at__date__gte=start,
                paid_at__date__lt=end,
            )
            .select_related("service_account__customer", "received_by")
        )
        for p in payments_qs[:1000]:
            p_date = timezone.localtime(p.paid_at).date() if p.paid_at else p.created_at.date()
            rows.append({
                "id": f"payment:{p.id}",
                "date": p_date.isoformat(),
                "sort_ts": p.paid_at.isoformat() if p.paid_at else p.created_at.isoformat(),
                "source": "CUSTOMER_PAYMENT",
                "source_label": "Customer Payment",
                "kind": DealerJournalEntry.Kind.INCOME,
                "amount": str(p.amount),
                "description": f"{p.payment_number} — {p.service_account.customer.full_name}",
                "recorded_by": (p.received_by.get_full_name() or p.received_by.email) if p.received_by else "Office",
                "is_manual": False,
                "is_void": False,
                "void_reason": "",
                "voided_at": None,
                "can_void": False,
            })

        settlements_qs = DealerSettlement.objects.for_organization(org).filter(
            dealer=dealer,
            settlement_date__gte=start,
            settlement_date__lt=end,
        ).select_related("created_by")
        for s in settlements_qs[:500]:
            rows.append({
                "id": f"settlement:{s.id}",
                "date": s.settlement_date.isoformat(),
                "sort_ts": s.created_at.isoformat(),
                "source": "ISP_PAYOUT",
                "source_label": "ISP Payout",
                "kind": DealerJournalEntry.Kind.INCOME,
                "amount": str(s.amount),
                "description": f"Settlement {s.settlement_number}" + (f" ({s.notes})" if s.notes else ""),
                "recorded_by": (s.created_by.get_full_name() or s.created_by.email) if s.created_by else "ISP",
                "is_manual": False,
                "is_void": False,
                "void_reason": "",
                "voided_at": None,
                "can_void": False,
            })

    if not kind_filter or kind_filter == DealerJournalEntry.Kind.EXPENSE:
        expenses_qs = (
            DealerEmployeeExpense.objects.for_organization(org)
            .filter(
                dealer=dealer,
                status=DealerEmployeeExpense.Status.APPROVED,
                spent_on__gte=start,
                spent_on__lt=end,
            )
            .select_related("employee__membership__user")
        )
        for exp in expenses_qs[:500]:
            emp_user = exp.employee.membership.user
            rows.append({
                "id": f"expense:{exp.id}",
                "date": exp.spent_on.isoformat(),
                "sort_ts": exp.created_at.isoformat(),
                "source": "EMPLOYEE_EXPENSE",
                "source_label": "Approved Expense",
                "kind": DealerJournalEntry.Kind.EXPENSE,
                "amount": str(exp.amount),
                "description": f"{exp.get_category_display()}: {exp.description}",
                "recorded_by": emp_user.get_full_name() or emp_user.email,
                "is_manual": False,
                "is_void": False,
                "void_reason": "",
                "voided_at": None,
                "can_void": False,
            })

    rows.sort(key=lambda r: (r["date"], r["sort_ts"]), reverse=True)
    for r in rows:
        r.pop("sort_ts", None)
    return rows


class DealerAccountsView(DealerPortalView):
    required_rights = ("can_view_accounts",)

    def get(self, request):
        dealer = request.dealer
        org = request.organization
        start, end = _month_bounds(request.query_params.get("month"))

        collected_month = (
            Payment.objects.for_organization(org)
            .filter(
                service_account__customer__dealer=dealer,
                is_reversed=False,
                paid_at__date__gte=start,
                paid_at__date__lt=end,
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        active_connections = (
            ServiceAccount.objects.for_organization(org)
            .filter(customer__dealer=dealer, status=ServiceAccount.Status.ACTIVE)
            .count()
        )

        is_sub_dealer = dealer.parent_dealer_id is not None
        parent_name = dealer.parent_dealer.name if is_sub_dealer else None
        if is_sub_dealer:
            commission_earned = Decimal("0.00")
            payout_info = None
            commission_note = f"Paid by {parent_name}"
        else:
            payout = dealer_payout(dealer, collected=collected_month, own_active=active_connections)
            commission_earned = payout["amount"]
            payout_info = payout_json(payout)
            commission_note = ""

        settlements_all = DealerSettlement.objects.for_organization(org).filter(dealer=dealer).order_by("-settlement_date", "-created_at")
        payouts_received_month = (
            settlements_all.filter(settlement_date__gte=start, settlement_date__lt=end)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        payouts_received_total = settlements_all.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        employees = (
            DealerEmployee.objects.for_organization(org)
            .filter(dealer=dealer, membership__is_active=True, membership__user__is_active=True)
            .select_related("membership__user")
            .order_by("membership__user__first_name")
        )
        cash_breakdown = []
        cash_in_hand_total = Decimal("0.00")
        for emp in employees:
            held = employee_cash_in_hand(emp)
            cash_in_hand_total += held
            cash_breakdown.append({
                "employee_id": str(emp.id),
                "name": emp.membership.user.get_full_name() or emp.membership.user.email,
                "cash_in_hand": str(held),
            })

        approved_expenses_month = (
            DealerEmployeeExpense.objects.for_organization(org)
            .filter(
                dealer=dealer,
                status=DealerEmployeeExpense.Status.APPROVED,
                spent_on__gte=start,
                spent_on__lt=end,
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        pending_expenses_count = (
            DealerEmployeeExpense.objects.for_organization(org)
            .filter(dealer=dealer, status=DealerEmployeeExpense.Status.PENDING)
            .count()
        )

        manual_entries = DealerJournalEntry.objects.for_organization(org).filter(
            dealer=dealer,
            is_void=False,
            date__gte=start,
            date__lt=end,
        )
        manual_income = (
            manual_entries.filter(kind=DealerJournalEntry.Kind.INCOME).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        manual_expense = (
            manual_entries.filter(kind=DealerJournalEntry.Kind.EXPENSE).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        net_cash_flow = (
            collected_month + payouts_received_month + manual_income - approved_expenses_month - manual_expense
        ).quantize(Decimal("0.01"))

        return Response({
            "month": start.strftime("%Y-%m"),
            "is_sub_dealer": is_sub_dealer,
            "parent_dealer_name": parent_name,
            "commission_note": commission_note,
            "collected_this_month": str(collected_month),
            "commission_earned": str(commission_earned),
            "payout": payout_info,
            "payouts_received_this_month": str(payouts_received_month),
            "payouts_received_total": str(payouts_received_total),
            "employee_cash_in_hand_total": str(cash_in_hand_total),
            "employee_cash_breakdown": cash_breakdown,
            "approved_expenses_this_month": str(approved_expenses_month),
            "pending_expenses_count": pending_expenses_count,
            "manual_income_this_month": str(manual_income),
            "manual_expense_this_month": str(manual_expense),
            "net_cash_flow_this_month": str(net_cash_flow),
            "recent_settlements": [
                {
                    "id": str(s.id),
                    "settlement_number": s.settlement_number,
                    "settlement_date": s.settlement_date.isoformat(),
                    "period_start": s.period_start.isoformat(),
                    "period_end": s.period_end.isoformat(),
                    "amount": str(s.amount),
                    "notes": s.notes,
                }
                for s in settlements_all[:20]
            ],
        })


class DealerJournalCreateSerializer(serializers.Serializer):
    date = serializers.DateField()
    kind = serializers.ChoiceField(choices=DealerJournalEntry.Kind.choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1.00"))
    description = serializers.CharField(max_length=500)

    def validate_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Date cannot be in the future.")
        return value

    def validate_description(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Description is required.")
        return cleaned


class DealerJournalView(DealerPortalView):
    required_rights_by_method = {
        "GET": ("can_view_journal", "can_add_journal_entries"),
        "POST": ("can_add_journal_entries",),
    }

    def get(self, request):
        start, end, period_label = _parse_date_range(request)
        kind_filter = request.query_params.get("kind", "").strip().upper()
        if kind_filter and kind_filter not in {DealerJournalEntry.Kind.INCOME, DealerJournalEntry.Kind.EXPENSE}:
            raise ValidationError({"kind": "Use INCOME or EXPENSE."})

        rows = _build_journal_rows(request, start, end, kind_filter=kind_filter)
        active_rows = [r for r in rows if not r["is_void"]]
        total_income = sum(
            (Decimal(r["amount"]) for r in active_rows if r["kind"] == DealerJournalEntry.Kind.INCOME),
            Decimal("0.00"),
        )
        total_expense = sum(
            (Decimal(r["amount"]) for r in active_rows if r["kind"] == DealerJournalEntry.Kind.EXPENSE),
            Decimal("0.00"),
        )
        return Response({
            "period": period_label,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "total_income": str(total_income),
            "total_expense": str(total_expense),
            "net": str(total_income - total_expense),
            "results": rows,
        })

    @transaction.atomic
    def post(self, request):
        serializer = DealerJournalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        entry = DealerJournalEntry.objects.create(
            organization=request.organization,
            dealer=request.dealer,
            date=data["date"],
            kind=data["kind"],
            amount=data["amount"],
            description=data["description"],
            created_by=request.user,
        )
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_JOURNAL_ENTRY_ADDED",
            resource_type="DealerJournalEntry",
            resource_id=str(entry.id),
            metadata={
                "dealer_code": request.dealer.dealer_code,
                "date": entry.date.isoformat(),
                "kind": entry.kind,
                "amount": str(entry.amount),
                "description": entry.description,
            },
        )
        return Response(
            {
                "id": str(entry.id),
                "date": entry.date.isoformat(),
                "source": "MANUAL",
                "source_label": "Manual Entry",
                "kind": entry.kind,
                "amount": str(entry.amount),
                "description": entry.description,
                "recorded_by": request.user.get_full_name() or request.user.email,
                "is_manual": True,
                "is_void": False,
                "void_reason": "",
                "voided_at": None,
                "can_void": request.dealer_employee is None or request.dealer_employee.can_void_journal_entries,
            },
            status=status.HTTP_201_CREATED,
        )


class DealerJournalVoidSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)

    def validate_reason(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Reason is required.")
        return cleaned


class DealerJournalVoidView(DealerPortalView):
    required_rights = ("can_void_journal_entries",)

    @transaction.atomic
    def post(self, request, entry_id):
        entry = (
            DealerJournalEntry.objects.for_organization(request.organization)
            .filter(id=entry_id, dealer=request.dealer)
            .first()
        )
        if entry is None:
            raise NotFound("Manual journal entry was not found.")
        if entry.is_void:
            raise ValidationError({"detail": "This journal entry is already voided."})

        serializer = DealerJournalVoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        entry.is_void = True
        entry.void_reason = reason
        entry.voided_by = request.user
        entry.voided_at = timezone.now()
        entry.save(update_fields=["is_void", "void_reason", "voided_by", "voided_at", "updated_at"])

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_JOURNAL_ENTRY_VOIDED",
            resource_type="DealerJournalEntry",
            resource_id=str(entry.id),
            metadata={
                "dealer_code": request.dealer.dealer_code,
                "kind": entry.kind,
                "amount": str(entry.amount),
                "reason": reason,
            },
        )
        return Response({
            "id": str(entry.id),
            "is_void": True,
            "void_reason": entry.void_reason,
            "voided_at": entry.voided_at.isoformat(),
        })


class DealerJournalExportView(DealerPortalView):
    required_rights = ("can_view_journal", "can_add_journal_entries")

    def perform_content_negotiation(self, request, force=False):
        renderer = self.get_renderers()[0]
        return (renderer, renderer.media_type)

    def get(self, request):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill

        start, end, period_label = _parse_date_range(request)
        kind_filter = request.query_params.get("kind", "").strip().upper()
        rows = _build_journal_rows(request, start, end, kind_filter=kind_filter)

        wb = Workbook()
        ws = wb.active
        ws.title = "Journal"
        headers = ["Date", "Source", "Type", "Description", "Income (PKR)", "Expense (PKR)", "Status", "Recorded By"]
        ws.append(headers)
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1F4E79")
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

        for r in rows:
            ws.append([
                r["date"],
                r["source_label"],
                r["kind"],
                r["description"],
                r["amount"] if r["kind"] == "INCOME" and not r["is_void"] else "",
                r["amount"] if r["kind"] == "EXPENSE" and not r["is_void"] else "",
                f"Void ({r['void_reason']})" if r["is_void"] else "Active",
                r["recorded_by"],
            ])

        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 20

        buf = io.BytesIO()
        wb.save(buf)
        response = HttpResponse(buf.getvalue(), content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="dealer_journal_{period_label}.xlsx"'
        return response
