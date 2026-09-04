from datetime import date, datetime
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
from accounting.serializers import (
    AccountSerializer,
    DealerSettlementSerializer,
    DirectIncomeSerializer,
    ExpenseSerializer,
    FinancialPeriodSerializer,
    FundTransferSerializer,
    JournalEntrySerializer,
)
from accounting.services import (
    AccountingDomainError,
    accrue_dealer_commission,
    close_financial_period,
    create_journal_entry,
    get_general_ledger,
    get_or_create_default_chart_of_accounts,
    get_trial_balance,
    record_dealer_settlement,
    record_direct_income,
    record_expense,
    reopen_financial_period,
    reverse_journal_entry,
    transfer_funds,
)
from tenancy.permissions import (
    CanCloseFinancialPeriod,
    CanManageAccounting,
    HasActiveTenantContext,
    IsOrganizationStaffOrOwner,
)


class AccountingOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request):
        organization = request.organization
        today = timezone.now().date()
        month_start = date(today.year, today.month, 1)

        # Auto-provision COA if none exists
        if not Account.objects.for_organization(organization).exists():
            get_or_create_default_chart_of_accounts(organization)

        # Cash & Bank Assets
        cash_bank_lines = (
            JournalLine.objects
            .for_organization(organization)
            .filter(
                account__category=Account.Category.ASSET,
                account__code__in=["1000", "1010", "1020"],
                journal_entry__status=JournalEntry.Status.POSTED,
            )
        )
        total_cash_dr = cash_bank_lines.aggregate(s=Sum("debit"))["s"] or Decimal("0.00")
        total_cash_cr = cash_bank_lines.aggregate(s=Sum("credit"))["s"] or Decimal("0.00")
        cash_bank_balance = total_cash_dr - total_cash_cr

        # Accounts Receivable
        ar_lines = (
            JournalLine.objects
            .for_organization(organization)
            .filter(
                account__code="1200",
                journal_entry__status=JournalEntry.Status.POSTED,
            )
        )
        ar_dr = ar_lines.aggregate(s=Sum("debit"))["s"] or Decimal("0.00")
        ar_cr = ar_lines.aggregate(s=Sum("credit"))["s"] or Decimal("0.00")
        receivables_balance = ar_dr - ar_cr

        # MTD Revenue
        rev_lines = (
            JournalLine.objects
            .for_organization(organization)
            .filter(
                account__category=Account.Category.REVENUE,
                journal_entry__status=JournalEntry.Status.POSTED,
                journal_entry__date__gte=month_start,
                journal_entry__date__lte=today,
            )
        )
        rev_cr = rev_lines.aggregate(s=Sum("credit"))["s"] or Decimal("0.00")
        rev_dr = rev_lines.aggregate(s=Sum("debit"))["s"] or Decimal("0.00")
        mtd_revenue = rev_cr - rev_dr

        # MTD Expenses
        exp_lines = (
            JournalLine.objects
            .for_organization(organization)
            .filter(
                account__category=Account.Category.EXPENSE,
                journal_entry__status=JournalEntry.Status.POSTED,
                journal_entry__date__gte=month_start,
                journal_entry__date__lte=today,
            )
        )
        exp_dr = exp_lines.aggregate(s=Sum("debit"))["s"] or Decimal("0.00")
        exp_cr = exp_lines.aggregate(s=Sum("credit"))["s"] or Decimal("0.00")
        mtd_expenses = exp_dr - exp_cr

        net_margin = mtd_revenue - mtd_expenses

        # Recent Journals
        recent_journals = (
            JournalEntry.objects
            .for_organization(organization)
            .select_related("period", "created_by", "posted_by", "reversed_entry")
            .prefetch_related("lines__account")[:10]
        )

        # Cash & Bank Accounts breakdown
        cash_bank_accounts = []
        for acc in Account.objects.for_organization(organization).filter(category=Account.Category.ASSET, code__in=["1000", "1010", "1020", "1500"]):
            lines = JournalLine.objects.for_organization(organization).filter(account=acc, journal_entry__status=JournalEntry.Status.POSTED)
            dr = lines.aggregate(s=Sum("debit"))["s"] or Decimal("0.00")
            cr = lines.aggregate(s=Sum("credit"))["s"] or Decimal("0.00")
            cash_bank_accounts.append({
                "id": str(acc.id),
                "code": acc.code,
                "name": acc.name,
                "account_type": acc.account_type,
                "balance": str(dr - cr),
            })

        return Response({
            "currency": organization.currency,
            "metrics": {
                "cash_bank_balance": str(cash_bank_balance),
                "receivables_balance": str(receivables_balance),
                "mtd_revenue": str(mtd_revenue),
                "mtd_expenses": str(mtd_expenses),
                "net_margin": str(net_margin),
                "total_accounts_count": Account.objects.for_organization(organization).count(),
                "total_journal_entries_count": JournalEntry.objects.for_organization(organization).count(),
            },
            "cash_bank_accounts": cash_bank_accounts,
            "recent_journals": JournalEntrySerializer(recent_journals, many=True).data,
        })


class AccountListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request):
        organization = request.organization
        category = request.query_params.get("category", "").strip()
        search = request.query_params.get("search", "").strip()
        is_active = request.query_params.get("is_active")

        # Auto-provision if empty
        if not Account.objects.for_organization(organization).exists():
            get_or_create_default_chart_of_accounts(organization)

        qs = Account.objects.for_organization(organization).select_related("parent").order_by("code")

        if category:
            qs = qs.filter(category=category.upper())
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search) | Q(description__icontains=search))
        if is_active is not None and is_active != "":
            active_bool = is_active.lower() in ["true", "1", "yes"]
            qs = qs.filter(is_active=active_bool)

        serializer = AccountSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        organization = request.organization
        serializer = AccountSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data.get("code")
        if Account.objects.for_organization(organization).filter(code=code).exists():
            return Response({"error": f"Account with code {code} already exists for this organization."}, status=status.HTTP_400_BAD_REQUEST)

        parent = serializer.validated_data.get("parent")
        if parent and parent.organization_id != organization.id:
            return Response({"error": "Parent account must belong to the same organization."}, status=status.HTTP_400_BAD_REQUEST)

        account = serializer.save(organization=organization, is_system=False)
        return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


class AccountDetailView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def _get_account(self, request, account_id):
        try:
            return Account.objects.for_organization(request.organization).get(id=account_id)
        except Account.DoesNotExist:
            return None

    def get(self, request, account_id):
        account = self._get_account(request, account_id)
        if not account:
            return Response({"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AccountSerializer(account).data)

    def put(self, request, account_id):
        account = self._get_account(request, account_id)
        if not account:
            return Response({"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AccountSerializer(account, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data)

    def patch(self, request, account_id):
        return self.put(request, account_id)

    def delete(self, request, account_id):
        account = self._get_account(request, account_id)
        if not account:
            return Response({"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

        if account.is_system:
            return Response({"error": "System accounts cannot be deleted."}, status=status.HTTP_400_BAD_REQUEST)

        if account.journal_lines.exists():
            return Response({"error": "Cannot delete account with financial journal transactions. Deactivate it instead."}, status=status.HTTP_400_BAD_REQUEST)

        account.delete()
        return Response({"message": "Account deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class AccountInitDefaultView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def post(self, request):
        accounts = get_or_create_default_chart_of_accounts(request.organization)
        return Response({
            "message": "Default chart of accounts initialized successfully.",
            "accounts_count": len(accounts),
        }, status=status.HTTP_200_OK)


class JournalEntryListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request):
        organization = request.organization
        ref_type = request.query_params.get("reference_type", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        search = request.query_params.get("search", "").strip()

        qs = (
            JournalEntry.objects
            .for_organization(organization)
            .select_related("period", "created_by", "posted_by", "reversed_entry")
            .prefetch_related("lines__account")
            .order_by("-date", "-created_at")
        )

        if ref_type:
            qs = qs.filter(reference_type=ref_type)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        if search:
            qs = qs.filter(
                Q(entry_number__icontains=search)
                | Q(narration__icontains=search)
                | Q(reference_id__icontains=search)
            )

        serializer = JournalEntrySerializer(qs[:100], many=True)
        return Response(serializer.data)

    def post(self, request):
        organization = request.organization
        data = request.data

        txn_date = data.get("date")
        if isinstance(txn_date, str):
            try:
                txn_date = date.fromisoformat(txn_date)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        elif not txn_date:
            txn_date = timezone.now().date()

        narration = data.get("narration", "")
        lines = data.get("lines", [])

        try:
            journal_entry = create_journal_entry(
                organization=organization,
                actor=request.user,
                txn_date=txn_date,
                narration=narration,
                lines=lines,
                reference_type=data.get("reference_type", JournalEntry.ReferenceType.MANUAL),
                reference_id=data.get("reference_id", ""),
            )
            return Response(JournalEntrySerializer(journal_entry).data, status=status.HTTP_201_CREATED)
        except AccountingDomainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class JournalEntryDetailView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request, entry_id):
        try:
            entry = (
                JournalEntry.objects
                .for_organization(request.organization)
                .select_related("period", "created_by", "posted_by", "reversed_entry")
                .prefetch_related("lines__account")
                .get(id=entry_id)
            )
            return Response(JournalEntrySerializer(entry).data)
        except JournalEntry.DoesNotExist:
            return Response({"error": "Journal entry not found."}, status=status.HTTP_404_NOT_FOUND)


class JournalEntryReverseView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def post(self, request, entry_id):
        reason = request.data.get("reason", "Manual reversal by staff")
        try:
            reversal = reverse_journal_entry(
                organization=request.organization,
                actor=request.user,
                entry_id=entry_id,
                reversal_reason=reason,
            )
            return Response(JournalEntrySerializer(reversal).data, status=status.HTTP_201_CREATED)
        except AccountingDomainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class GeneralLedgerView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request):
        organization = request.organization
        account_id = request.query_params.get("account_id")
        account_code = request.query_params.get("account_code")
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        start_date = date.fromisoformat(start_date_str) if start_date_str else None
        end_date = date.fromisoformat(end_date_str) if end_date_str else None

        if not account_id and not account_code:
            # Return list of accounts with current balance summaries for quick navigation
            accounts = Account.objects.for_organization(organization).filter(is_active=True).order_by("code")
            summaries = []
            for acc in accounts:
                lines = JournalLine.objects.for_organization(organization).filter(account=acc, journal_entry__status=JournalEntry.Status.POSTED)
                dr = lines.aggregate(s=Sum("debit"))["s"] or Decimal("0.00")
                cr = lines.aggregate(s=Sum("credit"))["s"] or Decimal("0.00")
                is_debit = acc.category in [Account.Category.ASSET, Account.Category.EXPENSE]
                bal = (dr - cr) if is_debit else (cr - dr)
                summaries.append({
                    "id": str(acc.id),
                    "code": acc.code,
                    "name": acc.name,
                    "category": acc.category,
                    "account_type": acc.account_type,
                    "total_debits": str(dr),
                    "total_credits": str(cr),
                    "balance": str(bal),
                })
            return Response({"accounts": summaries})

        try:
            ledger = get_general_ledger(
                organization=organization,
                account_id=account_id,
                account_code=account_code,
                start_date=start_date,
                end_date=end_date,
            )
            return Response(ledger)
        except AccountingDomainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class TrialBalanceView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request):
        organization = request.organization
        as_of_str = request.query_params.get("as_of_date")
        start_str = request.query_params.get("start_date")
        end_str = request.query_params.get("end_date")

        as_of_date = date.fromisoformat(as_of_str) if as_of_str else None
        start_date = date.fromisoformat(start_str) if start_str else None
        end_date = date.fromisoformat(end_str) if end_str else None

        tb = get_trial_balance(
            organization=organization,
            as_of_date=as_of_date,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(tb)


class ExpenseListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request):
        organization = request.organization
        category = request.query_params.get("category", "").strip()
        search = request.query_params.get("search", "").strip()

        qs = (
            Expense.objects
            .for_organization(organization)
            .select_related("expense_account", "payment_account", "journal_entry", "recorded_by")
            .order_by("-date", "-created_at")
        )
        if category:
            qs = qs.filter(category__icontains=category)
        if search:
            qs = qs.filter(
                Q(expense_number__icontains=search)
                | Q(payee__icontains=search)
                | Q(description__icontains=search)
                | Q(reference__icontains=search)
            )

        serializer = ExpenseSerializer(qs[:100], many=True)
        return Response(serializer.data)

    def post(self, request):
        organization = request.organization
        data = request.data

        date_val = data.get("date")
        if isinstance(date_val, str):
            try:
                date_val = date.fromisoformat(date_val)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        elif not date_val:
            date_val = timezone.now().date()

        try:
            expense = record_expense(
                organization=organization,
                actor=request.user,
                expense_account_id=data.get("expense_account_id") or data.get("expense_account"),
                payment_account_id=data.get("payment_account_id") or data.get("payment_account"),
                amount=data.get("amount"),
                date_val=date_val,
                payee=data.get("payee", ""),
                category=data.get("category", ""),
                reference=data.get("reference", ""),
                description=data.get("description", ""),
                receipt_file=request.FILES.get("receipt_file"),
            )
            return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)
        except AccountingDomainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class DirectIncomeListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request):
        organization = request.organization
        search = request.query_params.get("search", "").strip()

        qs = (
            DirectIncome.objects
            .for_organization(organization)
            .select_related("income_account", "deposit_account", "journal_entry", "recorded_by")
            .order_by("-date", "-created_at")
        )
        if search:
            qs = qs.filter(
                Q(income_number__icontains=search)
                | Q(received_from__icontains=search)
                | Q(description__icontains=search)
                | Q(reference__icontains=search)
            )

        serializer = DirectIncomeSerializer(qs[:100], many=True)
        return Response(serializer.data)

    def post(self, request):
        organization = request.organization
        data = request.data

        date_val = data.get("date")
        if isinstance(date_val, str):
            try:
                date_val = date.fromisoformat(date_val)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        elif not date_val:
            date_val = timezone.now().date()

        try:
            income = record_direct_income(
                organization=organization,
                actor=request.user,
                income_account_id=data.get("income_account_id") or data.get("income_account"),
                deposit_account_id=data.get("deposit_account_id") or data.get("deposit_account"),
                amount=data.get("amount"),
                date_val=date_val,
                received_from=data.get("received_from", ""),
                reference=data.get("reference", ""),
                description=data.get("description", ""),
            )
            return Response(DirectIncomeSerializer(income).data, status=status.HTTP_201_CREATED)
        except AccountingDomainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class FundTransferListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request):
        organization = request.organization
        qs = (
            FundTransfer.objects
            .for_organization(organization)
            .select_related("from_account", "to_account", "journal_entry", "transferred_by")
            .order_by("-date", "-created_at")
        )
        serializer = FundTransferSerializer(qs[:100], many=True)
        return Response(serializer.data)

    def post(self, request):
        organization = request.organization
        data = request.data

        date_val = data.get("date")
        if isinstance(date_val, str):
            try:
                date_val = date.fromisoformat(date_val)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        elif not date_val:
            date_val = timezone.now().date()

        try:
            transfer = transfer_funds(
                organization=organization,
                actor=request.user,
                from_account_id=data.get("from_account_id") or data.get("from_account"),
                to_account_id=data.get("to_account_id") or data.get("to_account"),
                amount=data.get("amount"),
                date_val=date_val,
                reference=data.get("reference", ""),
                description=data.get("description", ""),
            )
            return Response(FundTransferSerializer(transfer).data, status=status.HTTP_201_CREATED)
        except AccountingDomainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class DealerSettlementListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request):
        organization = request.organization
        dealer_id = request.query_params.get("dealer_id")
        qs = (
            DealerSettlement.objects
            .for_organization(organization)
            .select_related("dealer", "payment_account", "journal_entry", "created_by")
            .order_by("-settlement_date", "-created_at")
        )
        if dealer_id:
            qs = qs.filter(dealer_id=dealer_id)

        serializer = DealerSettlementSerializer(qs[:100], many=True)
        return Response(serializer.data)

    def post(self, request):
        organization = request.organization
        data = request.data

        try:
            settlement = record_dealer_settlement(
                organization=organization,
                actor=request.user,
                dealer_id=data.get("dealer_id") or data.get("dealer"),
                payment_account_id=data.get("payment_account_id") or data.get("payment_account"),
                amount=data.get("amount"),
                period_start=date.fromisoformat(str(data.get("period_start"))),
                period_end=date.fromisoformat(str(data.get("period_end"))),
                settlement_date=date.fromisoformat(str(data.get("settlement_date", timezone.now().date()))),
                notes=data.get("notes", ""),
            )
            return Response(DealerSettlementSerializer(settlement).data, status=status.HTTP_201_CREATED)
        except (AccountingDomainError, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class DealerAccrualCreateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def post(self, request):
        organization = request.organization
        data = request.data
        dealer_id = data.get("dealer_id")
        start_str = data.get("period_start")
        end_str = data.get("period_end")
        amount = data.get("commission_amount")

        if not dealer_id or not start_str or not end_str or not amount:
            return Response({"error": "dealer_id, period_start, period_end, and commission_amount are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            entry = accrue_dealer_commission(
                organization=organization,
                actor=request.user,
                dealer_id=dealer_id,
                period_start=date.fromisoformat(str(start_str)),
                period_end=date.fromisoformat(str(end_str)),
                commission_amount=amount,
                notes=data.get("notes", ""),
            )
            return Response(JournalEntrySerializer(entry).data, status=status.HTTP_201_CREATED)
        except (AccountingDomainError, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class FinancialPeriodListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanManageAccounting]

    def get(self, request):
        qs = FinancialPeriod.objects.for_organization(request.organization).order_by("-start_date")
        return Response(FinancialPeriodSerializer(qs, many=True).data)

    def post(self, request):
        serializer = FinancialPeriodSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        period = serializer.save(organization=request.organization, is_closed=False)
        return Response(FinancialPeriodSerializer(period).data, status=status.HTTP_201_CREATED)


class FinancialPeriodCloseView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanCloseFinancialPeriod]

    def post(self, request, period_id):
        try:
            period = close_financial_period(
                organization=request.organization,
                actor=request.user,
                period_id=period_id,
            )
            return Response(FinancialPeriodSerializer(period).data)
        except AccountingDomainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class FinancialPeriodReopenView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenantContext, CanCloseFinancialPeriod]

    def post(self, request, period_id):
        reason = request.data.get("reason", "Period reopened by authorized admin")
        try:
            period = reopen_financial_period(
                organization=request.organization,
                actor=request.user,
                period_id=period_id,
                reopen_reason=reason,
            )
            return Response(FinancialPeriodSerializer(period).data)
        except AccountingDomainError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
