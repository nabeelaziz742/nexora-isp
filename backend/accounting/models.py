import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from tenancy.base_models import TenantScopedModel


class Account(TenantScopedModel):
    class Category(models.TextChoices):
        ASSET = "ASSET", "Asset"
        LIABILITY = "LIABILITY", "Liability"
        EQUITY = "EQUITY", "Equity"
        REVENUE = "REVENUE", "Revenue"
        EXPENSE = "EXPENSE", "Expense"

    class AccountType(models.TextChoices):
        CURRENT_ASSET = "CURRENT_ASSET", "Current Asset"
        NON_CURRENT_ASSET = "NON_CURRENT_ASSET", "Non-Current Asset"
        CURRENT_LIABILITY = "CURRENT_LIABILITY", "Current Liability"
        LONG_TERM_LIABILITY = "LONG_TERM_LIABILITY", "Long-Term Liability"
        EQUITY = "EQUITY", "Equity"
        OPERATING_REVENUE = "OPERATING_REVENUE", "Operating Revenue"
        NON_OPERATING_REVENUE = "NON_OPERATING_REVENUE", "Non-Operating Revenue"
        DIRECT_EXPENSE = "DIRECT_EXPENSE", "Direct Expense"
        OPERATING_EXPENSE = "OPERATING_EXPENSE", "Operating Expense"
        ADMINISTRATIVE_EXPENSE = "ADMINISTRATIVE_EXPENSE", "Administrative Expense"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=50,
    )

    name = models.CharField(
        max_length=200,
    )

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
    )

    account_type = models.CharField(
        max_length=40,
        choices=AccountType.choices,
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )

    description = models.TextField(
        blank=True,
    )

    is_system = models.BooleanField(
        default=False,
        help_text="System accounts (e.g. Accounts Receivable, Cash) cannot be deleted or deactivated.",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "accounting_account"
        ordering = ["code"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_account_code_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "category"],
                name="acc_org_cat_idx",
            ),
            models.Index(
                fields=["organization", "account_type"],
                name="acc_org_type_idx",
            ),
            models.Index(
                fields=["organization", "is_active"],
                name="acc_org_active_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.parent and self.parent.organization_id != self.organization_id:
            raise ValidationError("Parent account must belong to the same organization.")

    def __str__(self):
        return f"{self.code} - {self.name} ({self.category})"


class FinancialPeriod(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=100,
    )

    start_date = models.DateField()

    end_date = models.DateField()

    is_closed = models.BooleanField(
        default=False,
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_financial_periods",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "accounting_financial_period"
        ordering = ["-start_date"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_period_name_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="period_end_gte_start",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "is_closed"],
                name="period_org_closed_idx",
            ),
            models.Index(
                fields=["organization", "start_date", "end_date"],
                name="period_org_dates_idx",
            ),
        ]

    def __str__(self):
        status = "CLOSED" if self.is_closed else "OPEN"
        return f"{self.name} ({self.start_date} to {self.end_date}) [{status}]"


class JournalEntry(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"
        REVERSED = "REVERSED", "Reversed"

    class ReferenceType(models.TextChoices):
        MANUAL = "MANUAL", "Manual Journal Entry"
        INVOICE = "INVOICE", "Customer Invoice"
        PAYMENT = "PAYMENT", "Customer Payment"
        PAYMENT_REVERSAL = "PAYMENT_REVERSAL", "Payment Reversal"
        INVOICE_CANCEL = "INVOICE_CANCEL", "Invoice Cancellation"
        EXPENSE = "EXPENSE", "Operational Expense"
        INCOME = "INCOME", "Direct Income"
        TRANSFER = "TRANSFER", "Cash / Bank Transfer"
        DEALER_ACCRUAL = "DEALER_ACCRUAL", "Dealer Commission Accrual"
        DEALER_SETTLEMENT = "DEALER_SETTLEMENT", "Dealer Payout Settlement"
        POS_SALE = "POS_SALE", "POS Hardware Sale"
        POS_SALE_REVERSAL = "POS_SALE_REVERSAL", "POS Sale Cancellation Reversal"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    entry_number = models.CharField(
        max_length=100,
    )

    date = models.DateField()

    narration = models.TextField()

    reference_type = models.CharField(
        max_length=40,
        choices=ReferenceType.choices,
        default=ReferenceType.MANUAL,
    )

    reference_id = models.CharField(
        max_length=255,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.POSTED,
    )

    period = models.ForeignKey(
        FinancialPeriod,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_entries",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_journal_entries",
    )

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posted_journal_entries",
    )

    posted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reversed_entry = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reversals",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "accounting_journal_entry"
        ordering = ["-date", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "entry_number"],
                name="unique_journal_entry_number_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "date"],
                name="je_org_date_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="je_org_status_idx",
            ),
            models.Index(
                fields=["organization", "reference_type", "reference_id"],
                name="je_org_ref_idx",
            ),
        ]

    @property
    def total_debit(self) -> Decimal:
        val = self.lines.aggregate(total=models.Sum("debit"))["total"]
        return val or Decimal("0.00")

    @property
    def total_credit(self) -> Decimal:
        val = self.lines.aggregate(total=models.Sum("credit"))["total"]
        return val or Decimal("0.00")

    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit

    def clean(self):
        super().clean()
        if self.period and self.period.organization_id != self.organization_id:
            raise ValidationError("Financial period must belong to the same organization.")
        if self.period and self.period.is_closed and self.status == self.Status.POSTED:
            raise ValidationError("Cannot post journal entry into a closed financial period.")

    def __str__(self):
        return f"{self.entry_number} ({self.date}) [{self.status}] - {self.narration[:40]}"


class JournalLine(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines",
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="journal_lines",
    )

    description = models.CharField(
        max_length=255,
        blank=True,
    )

    debit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    credit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    line_order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "accounting_journal_line"
        ordering = ["line_order", "created_at"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(debit__gte=0),
                name="journal_line_debit_gte_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(credit__gte=0),
                name="journal_line_credit_gte_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(debit__gt=0) | models.Q(credit__gt=0),
                name="journal_line_has_debit_or_credit",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "account"],
                name="jline_org_acc_idx",
            ),
            models.Index(
                fields=["organization", "journal_entry"],
                name="jline_org_entry_idx",
            ),
            models.Index(
                fields=["account", "created_at"],
                name="jline_acct_created_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.journal_entry and self.journal_entry.organization_id != self.organization_id:
            raise ValidationError("JournalLine organization must match JournalEntry organization.")
        if self.account and self.account.organization_id != self.organization_id:
            raise ValidationError("JournalLine account must belong to the same organization.")

    def __str__(self):
        return f"{self.journal_entry.entry_number} | {self.account.code} - Dr: {self.debit} Cr: {self.credit}"


class Expense(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    expense_number = models.CharField(
        max_length=100,
    )

    expense_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="expenses",
    )

    payment_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="expense_payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    date = models.DateField()

    payee = models.CharField(
        max_length=200,
        blank=True,
    )

    category = models.CharField(
        max_length=100,
        blank=True,
    )

    reference = models.CharField(
        max_length=150,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    receipt_file = models.FileField(
        upload_to="expenses/%Y/%m/",
        null=True,
        blank=True,
    )

    journal_entry = models.OneToOneField(
        JournalEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="expense_record",
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_expenses",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "accounting_expense"
        ordering = ["-date", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "expense_number"],
                name="unique_expense_number_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="expense_amount_gt_zero",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "date"],
                name="exp_org_date_idx",
            ),
            models.Index(
                fields=["organization", "category"],
                name="exp_org_cat_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.expense_account.category != Account.Category.EXPENSE:
            raise ValidationError("Expense account must be of category EXPENSE.")
        if self.payment_account.category != Account.Category.ASSET:
            raise ValidationError("Payment account must be of category ASSET.")
        if (
            self.expense_account.organization_id != self.organization_id
            or self.payment_account.organization_id != self.organization_id
        ):
            raise ValidationError("Expense accounts must belong to the same organization.")

    def __str__(self):
        return f"{self.expense_number} - {self.amount} ({self.payee or self.category})"


class DirectIncome(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    income_number = models.CharField(
        max_length=100,
    )

    income_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="direct_incomes",
    )

    deposit_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="income_deposits",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    date = models.DateField()

    received_from = models.CharField(
        max_length=200,
        blank=True,
    )

    reference = models.CharField(
        max_length=150,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    journal_entry = models.OneToOneField(
        JournalEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="direct_income_record",
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_incomes",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "accounting_direct_income"
        ordering = ["-date", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "income_number"],
                name="unique_income_number_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="income_amount_gt_zero",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "date"],
                name="inc_org_date_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.income_account.category != Account.Category.REVENUE:
            raise ValidationError("Income account must be of category REVENUE.")
        if self.deposit_account.category != Account.Category.ASSET:
            raise ValidationError("Deposit account must be of category ASSET.")
        if (
            self.income_account.organization_id != self.organization_id
            or self.deposit_account.organization_id != self.organization_id
        ):
            raise ValidationError("Income accounts must belong to the same organization.")

    def __str__(self):
        return f"{self.income_number} - {self.amount} ({self.received_from})"


class FundTransfer(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    transfer_number = models.CharField(
        max_length=100,
    )

    from_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="transfers_out",
    )

    to_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="transfers_in",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    date = models.DateField()

    reference = models.CharField(
        max_length=150,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    journal_entry = models.OneToOneField(
        JournalEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fund_transfer_record",
    )

    transferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transferred_funds",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "accounting_fund_transfer"
        ordering = ["-date", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "transfer_number"],
                name="unique_transfer_number_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="transfer_amount_gt_zero",
            ),
        ]

    def clean(self):
        super().clean()
        if self.from_account.category != Account.Category.ASSET:
            raise ValidationError("From account must be an ASSET account (Cash or Bank).")
        if self.to_account.category != Account.Category.ASSET:
            raise ValidationError("To account must be an ASSET account (Cash or Bank).")
        if self.from_account_id == self.to_account_id:
            raise ValidationError("Source and destination accounts cannot be the same.")
        if (
            self.from_account.organization_id != self.organization_id
            or self.to_account.organization_id != self.organization_id
        ):
            raise ValidationError("Transfer accounts must belong to the same organization.")

    def __str__(self):
        return f"{self.transfer_number}: {self.from_account.name} -> {self.to_account.name} ({self.amount})"


class DealerSettlement(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    settlement_number = models.CharField(
        max_length=100,
    )

    dealer = models.ForeignKey(
        "customers.Dealer",
        on_delete=models.PROTECT,
        related_name="settlements",
    )

    payment_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="dealer_settlements",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    period_start = models.DateField()

    period_end = models.DateField()

    settlement_date = models.DateField()

    notes = models.TextField(
        blank=True,
    )

    journal_entry = models.OneToOneField(
        JournalEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dealer_settlement_record",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_dealer_settlements",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "accounting_dealer_settlement"
        ordering = ["-settlement_date", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "settlement_number"],
                name="unique_dealer_settlement_number_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="settlement_amount_gt_zero",
            ),
        ]

    def clean(self):
        super().clean()
        if self.dealer.organization_id != self.organization_id:
            raise ValidationError("Dealer must belong to the same organization.")
        if self.payment_account.organization_id != self.organization_id:
            raise ValidationError("Payment account must belong to the same organization.")
        if self.payment_account.category != Account.Category.ASSET:
            raise ValidationError("Payment account must be an ASSET account (Cash or Bank).")

    def __str__(self):
        return f"{self.settlement_number} - {self.dealer.name} ({self.amount})"
