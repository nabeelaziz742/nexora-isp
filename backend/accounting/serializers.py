from rest_framework import serializers

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


class AccountSerializer(serializers.ModelSerializer):
    parent_code = serializers.CharField(source="parent.code", read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "code",
            "name",
            "category",
            "account_type",
            "parent",
            "parent_code",
            "parent_name",
            "description",
            "is_system",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]


class FinancialPeriodSerializer(serializers.ModelSerializer):
    closed_by_name = serializers.CharField(
        source="closed_by.get_full_name",
        read_only=True,
    )

    class Meta:
        model = FinancialPeriod
        fields = [
            "id",
            "name",
            "start_date",
            "end_date",
            "is_closed",
            "closed_at",
            "closed_by",
            "closed_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_closed", "closed_at", "closed_by", "created_at", "updated_at"]


class JournalLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    account_category = serializers.CharField(source="account.category", read_only=True)

    class Meta:
        model = JournalLine
        fields = [
            "id",
            "account",
            "account_code",
            "account_name",
            "account_category",
            "description",
            "debit",
            "credit",
            "line_order",
        ]
        read_only_fields = ["id"]


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True, read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)
    posted_by_name = serializers.CharField(source="posted_by.get_full_name", read_only=True)
    reversed_entry_number = serializers.CharField(source="reversed_entry.entry_number", read_only=True)
    total_debit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_credit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    is_balanced = serializers.BooleanField(read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "entry_number",
            "date",
            "narration",
            "reference_type",
            "reference_id",
            "status",
            "period",
            "period_name",
            "created_by",
            "created_by_name",
            "posted_by",
            "posted_by_name",
            "posted_at",
            "reversed_entry",
            "reversed_entry_number",
            "total_debit",
            "total_credit",
            "is_balanced",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "entry_number",
            "status",
            "period",
            "created_by",
            "posted_by",
            "posted_at",
            "reversed_entry",
            "total_debit",
            "total_credit",
            "is_balanced",
            "created_at",
            "updated_at",
        ]


class ExpenseSerializer(serializers.ModelSerializer):
    expense_account_code = serializers.CharField(source="expense_account.code", read_only=True)
    expense_account_name = serializers.CharField(source="expense_account.name", read_only=True)
    payment_account_code = serializers.CharField(source="payment_account.code", read_only=True)
    payment_account_name = serializers.CharField(source="payment_account.name", read_only=True)
    journal_entry_number = serializers.CharField(source="journal_entry.entry_number", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "expense_number",
            "expense_account",
            "expense_account_code",
            "expense_account_name",
            "payment_account",
            "payment_account_code",
            "payment_account_name",
            "amount",
            "date",
            "payee",
            "category",
            "reference",
            "description",
            "receipt_file",
            "journal_entry",
            "journal_entry_number",
            "recorded_by",
            "recorded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "expense_number",
            "journal_entry",
            "recorded_by",
            "created_at",
            "updated_at",
        ]


class DirectIncomeSerializer(serializers.ModelSerializer):
    income_account_code = serializers.CharField(source="income_account.code", read_only=True)
    income_account_name = serializers.CharField(source="income_account.name", read_only=True)
    deposit_account_code = serializers.CharField(source="deposit_account.code", read_only=True)
    deposit_account_name = serializers.CharField(source="deposit_account.name", read_only=True)
    journal_entry_number = serializers.CharField(source="journal_entry.entry_number", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)

    class Meta:
        model = DirectIncome
        fields = [
            "id",
            "income_number",
            "income_account",
            "income_account_code",
            "income_account_name",
            "deposit_account",
            "deposit_account_code",
            "deposit_account_name",
            "amount",
            "date",
            "received_from",
            "reference",
            "description",
            "journal_entry",
            "journal_entry_number",
            "recorded_by",
            "recorded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "income_number",
            "journal_entry",
            "recorded_by",
            "created_at",
            "updated_at",
        ]


class FundTransferSerializer(serializers.ModelSerializer):
    from_account_code = serializers.CharField(source="from_account.code", read_only=True)
    from_account_name = serializers.CharField(source="from_account.name", read_only=True)
    to_account_code = serializers.CharField(source="to_account.code", read_only=True)
    to_account_name = serializers.CharField(source="to_account.name", read_only=True)
    journal_entry_number = serializers.CharField(source="journal_entry.entry_number", read_only=True)
    transferred_by_name = serializers.CharField(source="transferred_by.get_full_name", read_only=True)

    class Meta:
        model = FundTransfer
        fields = [
            "id",
            "transfer_number",
            "from_account",
            "from_account_code",
            "from_account_name",
            "to_account",
            "to_account_code",
            "to_account_name",
            "amount",
            "date",
            "reference",
            "description",
            "journal_entry",
            "journal_entry_number",
            "transferred_by",
            "transferred_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "transfer_number",
            "journal_entry",
            "transferred_by",
            "created_at",
            "updated_at",
        ]


class DealerSettlementSerializer(serializers.ModelSerializer):
    dealer_code = serializers.CharField(source="dealer.dealer_code", read_only=True)
    dealer_name = serializers.CharField(source="dealer.name", read_only=True)
    payment_account_code = serializers.CharField(source="payment_account.code", read_only=True)
    payment_account_name = serializers.CharField(source="payment_account.name", read_only=True)
    journal_entry_number = serializers.CharField(source="journal_entry.entry_number", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = DealerSettlement
        fields = [
            "id",
            "settlement_number",
            "dealer",
            "dealer_code",
            "dealer_name",
            "payment_account",
            "payment_account_code",
            "payment_account_name",
            "amount",
            "period_start",
            "period_end",
            "settlement_date",
            "notes",
            "journal_entry",
            "journal_entry_number",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "settlement_number",
            "journal_entry",
            "created_by",
            "created_at",
            "updated_at",
        ]
