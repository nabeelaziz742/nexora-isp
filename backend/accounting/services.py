import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

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
from tenancy.models import Organization
from tenancy.services import record_audit_log

logger = logging.getLogger(__name__)
User = get_user_model()


class AccountingDomainError(Exception):
    pass


# Default Chart of Accounts Template for ISP Tenants
DEFAULT_COA_TEMPLATE = [
    # ASSETS
    {
        "code": "1000",
        "name": "Cash on Hand / Drawers",
        "category": Account.Category.ASSET,
        "account_type": Account.AccountType.CURRENT_ASSET,
        "description": "Physical cash collections and petty cash",
        "is_system": True,
    },
    {
        "code": "1010",
        "name": "Primary Operating Bank Account",
        "category": Account.Category.ASSET,
        "account_type": Account.AccountType.CURRENT_ASSET,
        "description": "Main bank account for billing deposits and disbursements",
        "is_system": True,
    },
    {
        "code": "1020",
        "name": "Mobile Wallets & Merchant Accounts",
        "category": Account.Category.ASSET,
        "account_type": Account.AccountType.CURRENT_ASSET,
        "description": "Easypaisa, JazzCash, and online payment gateways",
        "is_system": False,
    },
    {
        "code": "1200",
        "name": "Accounts Receivable (Subscribers)",
        "category": Account.Category.ASSET,
        "account_type": Account.AccountType.CURRENT_ASSET,
        "description": "Billed invoices pending customer settlement",
        "is_system": True,
    },
    {
        "code": "1500",
        "name": "Network Hardware & CPE Inventory",
        "category": Account.Category.ASSET,
        "account_type": Account.AccountType.NON_CURRENT_ASSET,
        "description": "Routers, ONUs, OLTs, switches, and deployment equipment",
        "is_system": False,
    },
    # LIABILITIES
    {
        "code": "2000",
        "name": "Accounts Payable (Vendors & Upstream)",
        "category": Account.Category.LIABILITY,
        "account_type": Account.AccountType.CURRENT_LIABILITY,
        "description": "Payables to transit providers, bandwidth vendors, and hardware suppliers",
        "is_system": True,
    },
    {
        "code": "2010",
        "name": "Dealer & Partner Payable",
        "category": Account.Category.LIABILITY,
        "account_type": Account.AccountType.CURRENT_LIABILITY,
        "description": "Accrued commissions owed to sub-dealers / franchisees",
        "is_system": True,
    },
    {
        "code": "2020",
        "name": "Customer Advance Payments / Deposits",
        "category": Account.Category.LIABILITY,
        "account_type": Account.AccountType.CURRENT_LIABILITY,
        "description": "Security deposits and advance collections",
        "is_system": False,
    },
    # EQUITY
    {
        "code": "3000",
        "name": "Owner Capital & Equity",
        "category": Account.Category.EQUITY,
        "account_type": Account.AccountType.EQUITY,
        "description": "Owner capital contributions and equity stake",
        "is_system": True,
    },
    {
        "code": "3900",
        "name": "Retained Earnings",
        "category": Account.Category.EQUITY,
        "account_type": Account.AccountType.EQUITY,
        "description": "Cumulative net income retained in business",
        "is_system": True,
    },
    # REVENUE
    {
        "code": "4000",
        "name": "Internet Subscription Revenue",
        "category": Account.Category.REVENUE,
        "account_type": Account.AccountType.OPERATING_REVENUE,
        "description": "Recurring monthly internet package charges",
        "is_system": True,
    },
    {
        "code": "4010",
        "name": "Installation & Setup Revenue",
        "category": Account.Category.REVENUE,
        "account_type": Account.AccountType.OPERATING_REVENUE,
        "description": "One-time subscriber fiber drop and activation fees",
        "is_system": False,
    },
    {
        "code": "4020",
        "name": "Static IP & Value-Added Services",
        "category": Account.Category.REVENUE,
        "account_type": Account.AccountType.OPERATING_REVENUE,
        "description": "Public IP allocations and premium SLAs",
        "is_system": False,
    },
    {
        "code": "4090",
        "name": "Miscellaneous & Other Direct Income",
        "category": Account.Category.REVENUE,
        "account_type": Account.AccountType.NON_OPERATING_REVENUE,
        "description": "Equipment sales, scrap, and non-operational income",
        "is_system": False,
    },
    # EXPENSES
    {
        "code": "5000",
        "name": "Upstream Bandwidth & IP Transit",
        "category": Account.Category.EXPENSE,
        "account_type": Account.AccountType.DIRECT_EXPENSE,
        "description": "Tier-1 bandwidth connectivity and IX transit cost",
        "is_system": True,
    },
    {
        "code": "5010",
        "name": "Fiber Optic & Network Maintenance",
        "category": Account.Category.EXPENSE,
        "account_type": Account.AccountType.OPERATING_EXPENSE,
        "description": "Fiber cuts, splicing, pole rent, and field repairs",
        "is_system": False,
    },
    {
        "code": "5020",
        "name": "Electricity, Generator & Fuel",
        "category": Account.Category.EXPENSE,
        "account_type": Account.AccountType.OPERATING_EXPENSE,
        "description": "PoP power, utility bills, and diesel backup",
        "is_system": False,
    },
    {
        "code": "5030",
        "name": "Staff Salaries & Field Compensation",
        "category": Account.Category.EXPENSE,
        "account_type": Account.AccountType.ADMINISTRATIVE_EXPENSE,
        "description": "Payroll for technicians, recovery staff, and support agents",
        "is_system": False,
    },
    {
        "code": "5040",
        "name": "Office & Node Rent",
        "category": Account.Category.EXPENSE,
        "account_type": Account.AccountType.ADMINISTRATIVE_EXPENSE,
        "description": "Headquarters and distributed PoP rental expenses",
        "is_system": False,
    },
    {
        "code": "5050",
        "name": "Hardware & Deployment Equipment",
        "category": Account.Category.EXPENSE,
        "account_type": Account.AccountType.DIRECT_EXPENSE,
        "description": "Patch cords, splitters, splice trays, and drop cables",
        "is_system": False,
    },
    {
        "code": "5060",
        "name": "Dealer & Franchisee Commission Expense",
        "category": Account.Category.EXPENSE,
        "account_type": Account.AccountType.OPERATING_EXPENSE,
        "description": "Commissions earned by sub-dealers on monthly customer collections",
        "is_system": True,
    },
    {
        "code": "5090",
        "name": "General & Administrative Expenses",
        "category": Account.Category.EXPENSE,
        "account_type": Account.AccountType.ADMINISTRATIVE_EXPENSE,
        "description": "Software licenses, legal, stationery, and refreshments",
        "is_system": False,
    },
]


def _normalize_decimal(amount, default="0.00") -> Decimal:
    try:
        val = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        val = Decimal(default)
    return val.quantize(Decimal("0.01"))


def _lock_organization_for_numbering(*, organization: Organization) -> Organization:
    return Organization.objects.select_for_update().get(id=organization.id)


def generate_journal_entry_number(*, organization: Organization) -> str:
    prefix = organization.code.upper()[:12]
    sequence = JournalEntry.objects.for_organization(organization).count() + 1
    return f"{prefix}-JE-{sequence:06d}"


def generate_expense_number(*, organization: Organization) -> str:
    prefix = organization.code.upper()[:12]
    sequence = Expense.objects.for_organization(organization).count() + 1
    return f"{prefix}-EXP-{sequence:06d}"


def generate_income_number(*, organization: Organization) -> str:
    prefix = organization.code.upper()[:12]
    sequence = DirectIncome.objects.for_organization(organization).count() + 1
    return f"{prefix}-INC-{sequence:06d}"


def generate_transfer_number(*, organization: Organization) -> str:
    prefix = organization.code.upper()[:12]
    sequence = FundTransfer.objects.for_organization(organization).count() + 1
    return f"{prefix}-TRF-{sequence:06d}"


def generate_settlement_number(*, organization: Organization) -> str:
    prefix = organization.code.upper()[:12]
    sequence = DealerSettlement.objects.for_organization(organization).count() + 1
    return f"{prefix}-SET-{sequence:06d}"


@transaction.atomic
def get_or_create_default_chart_of_accounts(organization: Organization) -> dict[str, Account]:
    """Ensures standard default ISP chart of accounts exists for the organization."""
    accounts = {}
    existing = {
        acc.code: acc for acc in Account.objects.for_organization(organization)
    }

    for item in DEFAULT_COA_TEMPLATE:
        code = item["code"]
        if code in existing:
            accounts[code] = existing[code]
        else:
            acc = Account.objects.create(
                organization=organization,
                code=code,
                name=item["name"],
                category=item["category"],
                account_type=item["account_type"],
                description=item["description"],
                is_system=item["is_system"],
                is_active=True,
            )
            accounts[code] = acc

    return accounts


def _normalize_date(val) -> date:
    if val is None:
        return timezone.now().date()
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        try:
            return date.fromisoformat(val.split("T")[0])
        except Exception:
            return timezone.now().date()
    return timezone.now().date()


def resolve_financial_period(
    *,
    organization: Organization,
    txn_date: date,
    auto_create: bool = True,
) -> FinancialPeriod | None:
    """Resolves financial period for transaction date and enforces period lock."""
    txn_date = _normalize_date(txn_date)
    period = (
        FinancialPeriod.objects
        .for_organization(organization)
        .filter(start_date__lte=txn_date, end_date__gte=txn_date)
        .first()
    )

    if not period and auto_create:
        import calendar
        month_name = txn_date.strftime("%Y-%m")
        last_day = calendar.monthrange(txn_date.year, txn_date.month)[1]
        start_date = date(txn_date.year, txn_date.month, 1)
        end_date = date(txn_date.year, txn_date.month, last_day)

        period = FinancialPeriod.objects.create(
            organization=organization,
            name=month_name,
            start_date=start_date,
            end_date=end_date,
            is_closed=False,
        )

    if period and period.is_closed:
        raise AccountingDomainError(
            f"Financial period {period.name} ({period.start_date} to {period.end_date}) is closed. "
            "Posting transactions into a closed period is strictly prohibited."
        )

    return period


@transaction.atomic
def create_journal_entry(
    *,
    organization: Organization,
    actor: User | None,
    txn_date: date,
    narration: str,
    lines: list[dict],
    reference_type: str = JournalEntry.ReferenceType.MANUAL,
    reference_id: str = "",
    status: str = JournalEntry.Status.POSTED,
    record_audit: bool = True,
) -> JournalEntry:
    """
    Creates and posts a balanced double-entry journal entry.
    Lines format: [{'account_id': UUID/Account, 'debit': Decimal, 'credit': Decimal, 'description': str}]
    Invariant: Sum(Debits) == Sum(Credits) and both > 0
    """
    txn_date = _normalize_date(txn_date)
    if not organization.is_active:
        raise AccountingDomainError("Organization is inactive.")

    if not narration or not narration.strip():
        raise AccountingDomainError("Narration is required for journal entry.")

    if len(lines) < 2:
        raise AccountingDomainError("A double-entry journal entry requires at least two line items.")

    # Validate period lock
    period = resolve_financial_period(organization=organization, txn_date=txn_date)

    organization = _lock_organization_for_numbering(organization=organization)
    entry_number = generate_journal_entry_number(organization=organization)

    total_debits = Decimal("0.00")
    total_credits = Decimal("0.00")
    validated_lines = []

    for idx, line in enumerate(lines):
        acc = line.get("account")
        if not acc:
            acc_id = line.get("account_id")
            try:
                acc = Account.objects.for_organization(organization).get(id=acc_id)
            except (Account.DoesNotExist, ValueError) as exc:
                raise AccountingDomainError(f"Account at line {idx+1} is invalid or not found.") from exc

        # Verify account belongs to same organization
        if acc.organization_id != organization.id:
            raise AccountingDomainError(
                f"Account {acc.code} belongs to a different organization. Cross-tenant accounting is prohibited."
            )

        if not acc.is_active:
            raise AccountingDomainError(f"Account {acc.code} ({acc.name}) is inactive.")

        dr = _normalize_decimal(line.get("debit", 0))
        cr = _normalize_decimal(line.get("credit", 0))

        if dr < Decimal("0.00") or cr < Decimal("0.00"):
            raise AccountingDomainError(f"Negative debit or credit at line {idx+1} is not allowed.")

        if dr == Decimal("0.00") and cr == Decimal("0.00"):
            raise AccountingDomainError(f"Line {idx+1} has zero debit and zero credit.")

        if dr > Decimal("0.00") and cr > Decimal("0.00"):
            raise AccountingDomainError(f"Line {idx+1} cannot have both non-zero debit and credit.")

        total_debits += dr
        total_credits += cr

        validated_lines.append({
            "account": acc,
            "debit": dr,
            "credit": cr,
            "description": str(line.get("description", "")).strip(),
            "line_order": idx,
        })

    # Strict Double-Entry Invariant: Debit == Credit
    if total_debits != total_credits:
        raise AccountingDomainError(
            f"Unbalanced journal entry: Total debits ({total_debits}) must equal total credits ({total_credits})."
        )

    if total_debits <= Decimal("0.00"):
        raise AccountingDomainError("Journal entry total amount must be greater than zero.")

    now = timezone.now()
    journal_entry = JournalEntry.objects.create(
        organization=organization,
        entry_number=entry_number,
        date=txn_date,
        narration=narration.strip(),
        reference_type=reference_type,
        reference_id=reference_id.strip(),
        status=status,
        period=period,
        created_by=actor,
        posted_by=actor if status == JournalEntry.Status.POSTED else None,
        posted_at=now if status == JournalEntry.Status.POSTED else None,
    )

    line_objs = [
        JournalLine(
            organization=organization,
            journal_entry=journal_entry,
            account=item["account"],
            description=item["description"],
            debit=item["debit"],
            credit=item["credit"],
            line_order=item["line_order"],
        )
        for item in validated_lines
    ]
    JournalLine.objects.bulk_create(line_objs)

    if record_audit:
        record_audit_log(
            organization=organization,
            actor=actor,
            action="ACCOUNTING_JOURNAL_POSTED",
            resource_type="JournalEntry",
            resource_id=str(journal_entry.id),
            metadata={
                "entry_number": journal_entry.entry_number,
                "date": txn_date.isoformat(),
                "total_amount": str(total_debits),
                "reference_type": reference_type,
                "reference_id": reference_id,
            },
        )

    return journal_entry


@transaction.atomic
def reverse_journal_entry(
    *,
    organization: Organization,
    actor: User,
    entry_id,
    reversal_reason: str,
) -> JournalEntry:
    """Creates an exact reversing journal entry for a previously posted entry."""
    if not organization.is_active:
        raise AccountingDomainError("Organization is inactive.")

    if not reversal_reason or not reversal_reason.strip():
        raise AccountingDomainError("Reversal reason is mandatory.")

    try:
        original = (
            JournalEntry.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=entry_id)
        )
    except JournalEntry.DoesNotExist as exc:
        raise AccountingDomainError("Journal entry not found.") from exc

    if original.status == JournalEntry.Status.REVERSED:
        raise AccountingDomainError("Journal entry has already been reversed.")

    if original.status != JournalEntry.Status.POSTED:
        raise AccountingDomainError("Only posted journal entries can be reversed.")

    today = timezone.now().date()
    period = resolve_financial_period(organization=organization, txn_date=today)

    organization = _lock_organization_for_numbering(organization=organization)
    reversal_number = generate_journal_entry_number(organization=organization)

    reversal_lines = []
    for line in original.lines.all().order_by("line_order"):
        reversal_lines.append({
            "account": line.account,
            "debit": line.credit,   # Swap debit and credit
            "credit": line.debit,
            "description": f"Reversal of {original.entry_number}: {line.description or original.narration}",
            "line_order": line.line_order,
        })

    reversal_entry = JournalEntry.objects.create(
        organization=organization,
        entry_number=reversal_number,
        date=today,
        narration=f"Reversal of {original.entry_number}: {reversal_reason.strip()}",
        reference_type=original.reference_type,
        reference_id=original.reference_id,
        status=JournalEntry.Status.POSTED,
        period=period,
        created_by=actor,
        posted_by=actor,
        posted_at=timezone.now(),
        reversed_entry=original,
    )

    line_objs = [
        JournalLine(
            organization=organization,
            journal_entry=reversal_entry,
            account=item["account"],
            description=item["description"],
            debit=item["debit"],
            credit=item["credit"],
            line_order=item["line_order"],
        )
        for item in reversal_lines
    ]
    JournalLine.objects.bulk_create(line_objs)

    original.status = JournalEntry.Status.REVERSED
    original.save(update_fields=["status", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="ACCOUNTING_JOURNAL_REVERSED",
        resource_type="JournalEntry",
        resource_id=str(original.id),
        metadata={
            "original_entry": original.entry_number,
            "reversal_entry": reversal_entry.entry_number,
            "reason": reversal_reason.strip(),
        },
    )

    return reversal_entry


def get_general_ledger(
    *,
    organization: Organization,
    account_id=None,
    account_code=None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Calculates authoritative General Ledger statements with running balances."""
    if account_id:
        try:
            account = Account.objects.for_organization(organization).get(id=account_id)
        except Account.DoesNotExist as exc:
            raise AccountingDomainError("Account not found.") from exc
    elif account_code:
        try:
            account = Account.objects.for_organization(organization).get(code=account_code)
        except Account.DoesNotExist as exc:
            raise AccountingDomainError(f"Account with code {account_code} not found.") from exc
    else:
        raise AccountingDomainError("Either account_id or account_code must be provided.")

    # Determine standard normal balance side (Debit for Asset/Expense, Credit for Liability/Equity/Revenue)
    is_debit_normal = account.category in [Account.Category.ASSET, Account.Category.EXPENSE]

    opening_balance = Decimal("0.00")
    if start_date:
        prior_lines = JournalLine.objects.for_organization(organization).filter(
            account=account,
            journal_entry__status=JournalEntry.Status.POSTED,
            journal_entry__date__lt=start_date,
        )
        prior_debits = prior_lines.aggregate(s=Sum("debit"))["s"] or Decimal("0.00")
        prior_credits = prior_lines.aggregate(s=Sum("credit"))["s"] or Decimal("0.00")

        if is_debit_normal:
            opening_balance = prior_debits - prior_credits
        else:
            opening_balance = prior_credits - prior_debits

    lines_qs = (
        JournalLine.objects
        .for_organization(organization)
        .filter(account=account, journal_entry__status=JournalEntry.Status.POSTED)
        .select_related("journal_entry")
        .order_by("journal_entry__date", "journal_entry__created_at", "line_order")
    )

    if start_date:
        lines_qs = lines_qs.filter(journal_entry__date__gte=start_date)
    if end_date:
        lines_qs = lines_qs.filter(journal_entry__date__lte=end_date)

    entries = []
    running_balance = opening_balance
    total_debits = Decimal("0.00")
    total_credits = Decimal("0.00")

    for line in lines_qs:
        total_debits += line.debit
        total_credits += line.credit

        if is_debit_normal:
            running_balance += (line.debit - line.credit)
        else:
            running_balance += (line.credit - line.debit)

        entries.append({
            "id": str(line.id),
            "journal_entry_id": str(line.journal_entry_id),
            "entry_number": line.journal_entry.entry_number,
            "date": line.journal_entry.date.isoformat(),
            "narration": line.journal_entry.narration,
            "description": line.description,
            "reference_type": line.journal_entry.reference_type,
            "reference_id": line.journal_entry.reference_id,
            "debit": str(line.debit),
            "credit": str(line.credit),
            "running_balance": str(running_balance),
        })

    net_change = (total_debits - total_credits) if is_debit_normal else (total_credits - total_debits)

    return {
        "account": {
            "id": str(account.id),
            "code": account.code,
            "name": account.name,
            "category": account.category,
            "account_type": account.account_type,
            "normal_side": "DEBIT" if is_debit_normal else "CREDIT",
        },
        "currency": organization.currency,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "opening_balance": str(opening_balance),
        "total_debits": str(total_debits),
        "total_credits": str(total_credits),
        "net_change": str(net_change),
        "closing_balance": str(running_balance),
        "entries": entries,
    }


def get_trial_balance(
    *,
    organization: Organization,
    as_of_date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Calculates a formal periodic Trial Balance with Total Debit == Total Credit verification."""
    accounts = (
        Account.objects
        .for_organization(organization)
        .filter(is_active=True)
        .order_by("code")
    )

    lines_qs = JournalLine.objects.for_organization(organization).filter(
        journal_entry__status=JournalEntry.Status.POSTED
    )

    if as_of_date:
        lines_qs = lines_qs.filter(journal_entry__date__lte=as_of_date)
    else:
        if start_date:
            lines_qs = lines_qs.filter(journal_entry__date__gte=start_date)
        if end_date:
            lines_qs = lines_qs.filter(journal_entry__date__lte=end_date)

    aggregated = {
        row["account_id"]: {
            "total_debit": row["total_debit"] or Decimal("0.00"),
            "total_credit": row["total_credit"] or Decimal("0.00"),
        }
        for row in lines_qs.values("account_id").annotate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        )
    }

    report_rows = []
    total_debit_all = Decimal("0.00")
    total_credit_all = Decimal("0.00")

    for acc in accounts:
        acc_data = aggregated.get(acc.id, {"total_debit": Decimal("0.00"), "total_credit": Decimal("0.00")})
        dr = acc_data["total_debit"]
        cr = acc_data["total_credit"]

        if dr == Decimal("0.00") and cr == Decimal("0.00"):
            continue

        is_debit_normal = acc.category in [Account.Category.ASSET, Account.Category.EXPENSE]
        net_balance = (dr - cr) if is_debit_normal else (cr - dr)

        # For standard trial balance presentation, we present either net debit/credit or cumulative activity
        trial_dr = dr if dr >= cr else Decimal("0.00")
        trial_cr = cr if cr > dr else Decimal("0.00")

        total_debit_all += dr
        total_credit_all += cr

        report_rows.append({
            "account_id": str(acc.id),
            "code": acc.code,
            "name": acc.name,
            "category": acc.category,
            "account_type": acc.account_type,
            "debit_total": str(dr),
            "credit_total": str(cr),
            "net_balance": str(net_balance),
            "normal_side": "DEBIT" if is_debit_normal else "CREDIT",
        })

    is_balanced = (total_debit_all == total_credit_all)

    return {
        "organization_code": organization.code,
        "currency": organization.currency,
        "as_of_date": as_of_date.isoformat() if as_of_date else None,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "total_debits": str(total_debit_all),
        "total_credits": str(total_credit_all),
        "is_balanced": is_balanced,
        "accounts": report_rows,
    }


# =========================================================================
# EXPENSE, INCOME, TRANSFER & DEALER SETTLEMENT SERVICES
# =========================================================================

@transaction.atomic
def record_expense(
    *,
    organization: Organization,
    actor: User,
    expense_account_id,
    payment_account_id,
    amount,
    date_val: date,
    payee: str = "",
    category: str = "",
    reference: str = "",
    description: str = "",
    receipt_file=None,
) -> Expense:
    """Records an operational ISP expense and creates a balancing journal entry."""
    if not organization.is_active:
        raise AccountingDomainError("Organization is inactive.")

    normalized_amount = _normalize_decimal(amount)
    if normalized_amount <= Decimal("0.00"):
        raise AccountingDomainError("Expense amount must be greater than zero.")

    try:
        exp_acc = Account.objects.for_organization(organization).get(id=expense_account_id)
    except Account.DoesNotExist as exc:
        raise AccountingDomainError("Expense account not found.") from exc

    try:
        pay_acc = Account.objects.for_organization(organization).get(id=payment_account_id)
    except Account.DoesNotExist as exc:
        raise AccountingDomainError("Payment account not found.") from exc

    if exp_acc.category != Account.Category.EXPENSE:
        raise AccountingDomainError(f"Account {exp_acc.code} ({exp_acc.name}) is not an EXPENSE account.")

    if pay_acc.category != Account.Category.ASSET:
        raise AccountingDomainError(f"Account {pay_acc.code} ({pay_acc.name}) must be an ASSET account (Cash or Bank).")

    organization = _lock_organization_for_numbering(organization=organization)
    expense_number = generate_expense_number(organization=organization)

    expense = Expense.objects.create(
        organization=organization,
        expense_number=expense_number,
        expense_account=exp_acc,
        payment_account=pay_acc,
        amount=normalized_amount,
        date=date_val,
        payee=payee.strip(),
        category=category.strip() or exp_acc.name,
        reference=reference.strip(),
        description=description.strip(),
        receipt_file=receipt_file,
        recorded_by=actor,
    )

    narration = f"Expense: {expense.category} - {expense.payee or expense.description or expense.expense_number}"
    journal_entry = create_journal_entry(
        organization=organization,
        actor=actor,
        txn_date=date_val,
        narration=narration,
        reference_type=JournalEntry.ReferenceType.EXPENSE,
        reference_id=str(expense.id),
        lines=[
            {
                "account": exp_acc,
                "debit": normalized_amount,
                "credit": Decimal("0.00"),
                "description": f"Expense: {expense.payee} (Ref: {expense.reference or expense_number})",
            },
            {
                "account": pay_acc,
                "debit": Decimal("0.00"),
                "credit": normalized_amount,
                "description": f"Paid from {pay_acc.name}",
            },
        ],
    )

    expense.journal_entry = journal_entry
    expense.save(update_fields=["journal_entry", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="ACCOUNTING_EXPENSE_RECORDED",
        resource_type="Expense",
        resource_id=str(expense.id),
        metadata={
            "expense_number": expense.expense_number,
            "amount": str(expense.amount),
            "category": expense.category,
            "payee": expense.payee,
        },
    )

    return expense


@transaction.atomic
def record_direct_income(
    *,
    organization: Organization,
    actor: User,
    income_account_id,
    deposit_account_id,
    amount,
    date_val: date,
    received_from: str = "",
    reference: str = "",
    description: str = "",
) -> DirectIncome:
    """Records direct non-subscriber income and posts a balancing journal entry."""
    if not organization.is_active:
        raise AccountingDomainError("Organization is inactive.")

    normalized_amount = _normalize_decimal(amount)
    if normalized_amount <= Decimal("0.00"):
        raise AccountingDomainError("Income amount must be greater than zero.")

    try:
        inc_acc = Account.objects.for_organization(organization).get(id=income_account_id)
    except Account.DoesNotExist as exc:
        raise AccountingDomainError("Income account not found.") from exc

    try:
        dep_acc = Account.objects.for_organization(organization).get(id=deposit_account_id)
    except Account.DoesNotExist as exc:
        raise AccountingDomainError("Deposit account not found.") from exc

    if inc_acc.category != Account.Category.REVENUE:
        raise AccountingDomainError(f"Account {inc_acc.code} ({inc_acc.name}) is not a REVENUE account.")

    if dep_acc.category != Account.Category.ASSET:
        raise AccountingDomainError(f"Account {dep_acc.code} ({dep_acc.name}) must be an ASSET account (Cash or Bank).")

    organization = _lock_organization_for_numbering(organization=organization)
    income_number = generate_income_number(organization=organization)

    income = DirectIncome.objects.create(
        organization=organization,
        income_number=income_number,
        income_account=inc_acc,
        deposit_account=dep_acc,
        amount=normalized_amount,
        date=date_val,
        received_from=received_from.strip(),
        reference=reference.strip(),
        description=description.strip(),
        recorded_by=actor,
    )

    narration = f"Direct Income: {income.received_from or inc_acc.name} - {income.description or income_number}"
    journal_entry = create_journal_entry(
        organization=organization,
        actor=actor,
        txn_date=date_val,
        narration=narration,
        reference_type=JournalEntry.ReferenceType.INCOME,
        reference_id=str(income.id),
        lines=[
            {
                "account": dep_acc,
                "debit": normalized_amount,
                "credit": Decimal("0.00"),
                "description": f"Received in {dep_acc.name}",
            },
            {
                "account": inc_acc,
                "debit": Decimal("0.00"),
                "credit": normalized_amount,
                "description": f"Direct Income: {income.received_from} (Ref: {income.reference or income_number})",
            },
        ],
    )

    income.journal_entry = journal_entry
    income.save(update_fields=["journal_entry", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="ACCOUNTING_INCOME_RECORDED",
        resource_type="DirectIncome",
        resource_id=str(income.id),
        metadata={
            "income_number": income.income_number,
            "amount": str(income.amount),
            "received_from": income.received_from,
        },
    )

    return income


@transaction.atomic
def transfer_funds(
    *,
    organization: Organization,
    actor: User,
    from_account_id,
    to_account_id,
    amount,
    date_val: date,
    reference: str = "",
    description: str = "",
) -> FundTransfer:
    """Executes a fund transfer between two cash or bank asset accounts."""
    if not organization.is_active:
        raise AccountingDomainError("Organization is inactive.")

    normalized_amount = _normalize_decimal(amount)
    if normalized_amount <= Decimal("0.00"):
        raise AccountingDomainError("Transfer amount must be greater than zero.")

    if str(from_account_id) == str(to_account_id):
        raise AccountingDomainError("Source and destination accounts cannot be the same.")

    try:
        from_acc = Account.objects.for_organization(organization).get(id=from_account_id)
        to_acc = Account.objects.for_organization(organization).get(id=to_account_id)
    except Account.DoesNotExist as exc:
        raise AccountingDomainError("One or both accounts were not found.") from exc

    if from_acc.category != Account.Category.ASSET or to_acc.category != Account.Category.ASSET:
        raise AccountingDomainError("Both source and destination accounts must be ASSET accounts (Cash/Bank).")

    organization = _lock_organization_for_numbering(organization=organization)
    transfer_number = generate_transfer_number(organization=organization)

    transfer = FundTransfer.objects.create(
        organization=organization,
        transfer_number=transfer_number,
        from_account=from_acc,
        to_account=to_acc,
        amount=normalized_amount,
        date=date_val,
        reference=reference.strip(),
        description=description.strip(),
        transferred_by=actor,
    )

    narration = f"Fund Transfer: {from_acc.name} -> {to_acc.name} ({transfer_number})"
    journal_entry = create_journal_entry(
        organization=organization,
        actor=actor,
        txn_date=date_val,
        narration=narration,
        reference_type=JournalEntry.ReferenceType.TRANSFER,
        reference_id=str(transfer.id),
        lines=[
            {
                "account": to_acc,
                "debit": normalized_amount,
                "credit": Decimal("0.00"),
                "description": f"Transfer In from {from_acc.name} (Ref: {transfer_number})",
            },
            {
                "account": from_acc,
                "debit": Decimal("0.00"),
                "credit": normalized_amount,
                "description": f"Transfer Out to {to_acc.name} (Ref: {transfer_number})",
            },
        ],
    )

    transfer.journal_entry = journal_entry
    transfer.save(update_fields=["journal_entry", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="ACCOUNTING_FUND_TRANSFERRED",
        resource_type="FundTransfer",
        resource_id=str(transfer.id),
        metadata={
            "transfer_number": transfer.transfer_number,
            "from_account": from_acc.code,
            "to_account": to_acc.code,
            "amount": str(transfer.amount),
        },
    )

    return transfer


@transaction.atomic
def accrue_dealer_commission(
    *,
    organization: Organization,
    actor: User | None,
    dealer_id,
    period_start: date,
    period_end: date,
    commission_amount: Decimal | str | float,
    notes: str = "",
) -> JournalEntry:
    """
    Accrues dealer commission expense:
    Debit: 5060 Dealer Commission Expense
    Credit: 2010 Dealer & Partner Payable
    Idempotent per dealer and period.
    """
    from customers.models import Dealer

    try:
        dealer = Dealer.objects.for_organization(organization).get(id=dealer_id)
    except Dealer.DoesNotExist as exc:
        raise AccountingDomainError("Dealer not found.") from exc

    norm_amount = _normalize_decimal(commission_amount)
    if norm_amount <= Decimal("0.00"):
        raise AccountingDomainError("Commission accrual amount must be greater than zero.")

    ref_id = f"{dealer.id}:{period_start.isoformat()}:{period_end.isoformat()}"

    # Idempotency guard
    existing_entry = (
        JournalEntry.objects
        .for_organization(organization)
        .filter(
            reference_type=JournalEntry.ReferenceType.DEALER_ACCRUAL,
            reference_id=ref_id,
            status=JournalEntry.Status.POSTED,
        )
        .first()
    )
    if existing_entry:
        return existing_entry

    coa = get_or_create_default_chart_of_accounts(organization)
    exp_acc = coa.get("5060") or Account.objects.for_organization(organization).filter(category=Account.Category.EXPENSE).first()
    payable_acc = coa.get("2010") or Account.objects.for_organization(organization).filter(category=Account.Category.LIABILITY).first()

    narration = f"Commission Accrual: {dealer.name} ({dealer.dealer_code}) for {period_start} to {period_end}"
    if notes:
        narration += f" - {notes.strip()}"

    return create_journal_entry(
        organization=organization,
        actor=actor,
        txn_date=period_end,
        narration=narration,
        reference_type=JournalEntry.ReferenceType.DEALER_ACCRUAL,
        reference_id=ref_id,
        lines=[
            {
                "account": exp_acc,
                "debit": norm_amount,
                "credit": Decimal("0.00"),
                "description": f"Commission Expense for {dealer.name} ({period_start} to {period_end})",
            },
            {
                "account": payable_acc,
                "debit": Decimal("0.00"),
                "credit": norm_amount,
                "description": f"Payable to {dealer.name} ({dealer.dealer_code})",
            },
        ],
    )


@transaction.atomic
def record_dealer_settlement(
    *,
    organization: Organization,
    actor: User,
    dealer_id,
    payment_account_id,
    amount,
    period_start: date,
    period_end: date,
    settlement_date: date,
    notes: str = "",
) -> DealerSettlement:
    """
    Records a dealer commission payout settlement:
    Debit: 2010 Dealer & Partner Payable
    Credit: Payment Account (Cash or Bank)
    """
    from customers.models import Dealer

    try:
        dealer = Dealer.objects.for_organization(organization).get(id=dealer_id)
    except Dealer.DoesNotExist as exc:
        raise AccountingDomainError("Dealer not found.") from exc

    norm_amount = _normalize_decimal(amount)
    if norm_amount <= Decimal("0.00"):
        raise AccountingDomainError("Settlement amount must be greater than zero.")

    try:
        pay_acc = Account.objects.for_organization(organization).get(id=payment_account_id)
    except Account.DoesNotExist as exc:
        raise AccountingDomainError("Payment account not found.") from exc

    if pay_acc.category != Account.Category.ASSET:
        raise AccountingDomainError("Payment account must be an ASSET account (Cash/Bank).")

    organization = _lock_organization_for_numbering(organization=organization)
    settlement_number = generate_settlement_number(organization=organization)

    settlement = DealerSettlement.objects.create(
        organization=organization,
        settlement_number=settlement_number,
        dealer=dealer,
        payment_account=pay_acc,
        amount=norm_amount,
        period_start=period_start,
        period_end=period_end,
        settlement_date=settlement_date,
        notes=notes.strip(),
        created_by=actor,
    )

    coa = get_or_create_default_chart_of_accounts(organization)
    payable_acc = coa.get("2010") or Account.objects.for_organization(organization).filter(category=Account.Category.LIABILITY).first()

    narration = f"Dealer Settlement: Payout to {dealer.name} ({settlement_number})"
    journal_entry = create_journal_entry(
        organization=organization,
        actor=actor,
        txn_date=settlement_date,
        narration=narration,
        reference_type=JournalEntry.ReferenceType.DEALER_SETTLEMENT,
        reference_id=str(settlement.id),
        lines=[
            {
                "account": payable_acc,
                "debit": norm_amount,
                "credit": Decimal("0.00"),
                "description": f"Settlement Payout to {dealer.name} ({settlement_number})",
            },
            {
                "account": pay_acc,
                "debit": Decimal("0.00"),
                "credit": norm_amount,
                "description": f"Disbursed from {pay_acc.name}",
            },
        ],
    )

    settlement.journal_entry = journal_entry
    settlement.save(update_fields=["journal_entry", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="ACCOUNTING_DEALER_SETTLEMENT_RECORDED",
        resource_type="DealerSettlement",
        resource_id=str(settlement.id),
        metadata={
            "settlement_number": settlement.settlement_number,
            "dealer_id": str(dealer.id),
            "dealer_code": dealer.dealer_code,
            "amount": str(settlement.amount),
        },
    )

    return settlement


@transaction.atomic
def close_financial_period(
    *,
    organization: Organization,
    actor: User,
    period_id,
) -> FinancialPeriod:
    """Closes a financial period to prevent further transaction postings."""
    try:
        period = FinancialPeriod.objects.for_organization(organization).select_for_update().get(id=period_id)
    except FinancialPeriod.DoesNotExist as exc:
        raise AccountingDomainError("Financial period not found.") from exc

    if period.is_closed:
        raise AccountingDomainError("Financial period is already closed.")

    period.is_closed = True
    period.closed_at = timezone.now()
    period.closed_by = actor
    period.save(update_fields=["is_closed", "closed_at", "closed_by", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="ACCOUNTING_PERIOD_CLOSED",
        resource_type="FinancialPeriod",
        resource_id=str(period.id),
        metadata={"period_name": period.name, "start_date": period.start_date.isoformat(), "end_date": period.end_date.isoformat()},
    )
    return period


@transaction.atomic
def reopen_financial_period(
    *,
    organization: Organization,
    actor: User,
    period_id,
    reopen_reason: str,
) -> FinancialPeriod:
    """Reopens a closed financial period with authorized audit logging."""
    if not reopen_reason or not reopen_reason.strip():
        raise AccountingDomainError("Reopening reason is mandatory.")

    try:
        period = FinancialPeriod.objects.for_organization(organization).select_for_update().get(id=period_id)
    except FinancialPeriod.DoesNotExist as exc:
        raise AccountingDomainError("Financial period not found.") from exc

    if not period.is_closed:
        raise AccountingDomainError("Financial period is already open.")

    period.is_closed = False
    period.closed_at = None
    period.closed_by = None
    period.save(update_fields=["is_closed", "closed_at", "closed_by", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="ACCOUNTING_PERIOD_REOPENED",
        resource_type="FinancialPeriod",
        resource_id=str(period.id),
        metadata={"period_name": period.name, "reopen_reason": reopen_reason.strip()},
    )
    return period


# =========================================================================
# IDEMPOTENT BILLING -> ACCOUNTING INTEGRATION HOOKS
# =========================================================================

def post_invoice_journal_entry(invoice, actor=None) -> JournalEntry | None:
    """
    Idempotent hook for invoice generation:
    Debit: 1200 Accounts Receivable (Subscribers)
    Credit: 4000 Internet Subscription Revenue
    """
    try:
        organization = invoice.organization
        ref_id = str(invoice.id)

        # Idempotency check
        existing = (
            JournalEntry.objects
            .for_organization(organization)
            .filter(
                reference_type=JournalEntry.ReferenceType.INVOICE,
                reference_id=ref_id,
                status=JournalEntry.Status.POSTED,
            )
            .first()
        )
        if existing:
            return existing

        coa = get_or_create_default_chart_of_accounts(organization)
        ar_acc = coa.get("1200") or Account.objects.for_organization(organization).filter(category=Account.Category.ASSET).first()
        rev_acc = coa.get("4000") or Account.objects.for_organization(organization).filter(category=Account.Category.REVENUE).first()

        amount = invoice.total_amount
        if amount <= Decimal("0.00"):
            return None

        narration = f"Invoice Issued: {invoice.invoice_number} ({invoice.service_account.service_number})"

        return create_journal_entry(
            organization=organization,
            actor=actor,
            txn_date=invoice.issue_date,
            narration=narration,
            reference_type=JournalEntry.ReferenceType.INVOICE,
            reference_id=ref_id,
            record_audit=False,
            lines=[
                {
                    "account": ar_acc,
                    "debit": amount,
                    "credit": Decimal("0.00"),
                    "description": f"Customer Receivable: {invoice.invoice_number}",
                },
                {
                    "account": rev_acc,
                    "debit": Decimal("0.00"),
                    "credit": amount,
                    "description": f"Subscription Revenue: {invoice.service_account.service_number} ({invoice.billing_period_start} to {invoice.billing_period_end})",
                },
            ],
        )
    except Exception as exc:
        logger.exception("Error creating invoice journal entry for %s: %s", getattr(invoice, "invoice_number", invoice), exc)
        return None


def post_payment_journal_entry(payment, actor=None) -> JournalEntry | None:
    """
    Idempotent hook for payment receipt:
    Debit: Cash (1000) / Bank (1010) / Mobile Wallet (1020)
    Credit: 1200 Accounts Receivable (Subscribers)
    """
    try:
        organization = payment.organization
        ref_id = str(payment.id)

        # Idempotency check
        existing = (
            JournalEntry.objects
            .for_organization(organization)
            .filter(
                reference_type=JournalEntry.ReferenceType.PAYMENT,
                reference_id=ref_id,
                status=JournalEntry.Status.POSTED,
            )
            .first()
        )
        if existing:
            return existing

        coa = get_or_create_default_chart_of_accounts(organization)
        ar_acc = coa.get("1200") or Account.objects.for_organization(organization).filter(category=Account.Category.ASSET).first()

        # Map payment method to asset account
        if payment.payment_method == "CASH":
            deposit_acc = coa.get("1000") or coa.get("1010") or ar_acc
        elif payment.payment_method in ["BANK_TRANSFER", "CARD"]:
            deposit_acc = coa.get("1010") or coa.get("1000") or ar_acc
        else:
            deposit_acc = coa.get("1020") or coa.get("1010") or coa.get("1000") or ar_acc

        amount = payment.amount
        if amount <= Decimal("0.00"):
            return None

        paid_date = _normalize_date(payment.paid_at)
        narration = f"Payment Received: {payment.payment_number} via {payment.payment_method} ({payment.service_account.service_number})"

        return create_journal_entry(
            organization=organization,
            actor=actor or payment.received_by,
            txn_date=paid_date,
            narration=narration,
            reference_type=JournalEntry.ReferenceType.PAYMENT,
            reference_id=ref_id,
            record_audit=False,
            lines=[
                {
                    "account": deposit_acc,
                    "debit": amount,
                    "credit": Decimal("0.00"),
                    "description": f"Payment Collected via {payment.payment_method} (Ref: {payment.reference or payment.payment_number})",
                },
                {
                    "account": ar_acc,
                    "debit": Decimal("0.00"),
                    "credit": amount,
                    "description": f"Customer Receivable Cleared: {payment.payment_number}",
                },
            ],
        )
    except Exception as exc:
        logger.exception("Error creating payment journal entry for %s: %s", getattr(payment, "payment_number", payment), exc)
        return None


def post_payment_reversal_journal_entry(payment, actor=None) -> JournalEntry | None:
    """
    Idempotent hook for payment reversal:
    Debit: 1200 Accounts Receivable (Subscribers)
    Credit: Cash (1000) / Bank (1010) / Mobile Wallet (1020)
    """
    try:
        organization = payment.organization
        ref_id = f"REV:{payment.id}"

        # Idempotency check
        existing = (
            JournalEntry.objects
            .for_organization(organization)
            .filter(
                reference_type=JournalEntry.ReferenceType.PAYMENT_REVERSAL,
                reference_id=ref_id,
                status=JournalEntry.Status.POSTED,
            )
            .first()
        )
        if existing:
            return existing

        coa = get_or_create_default_chart_of_accounts(organization)
        ar_acc = coa.get("1200") or Account.objects.for_organization(organization).filter(category=Account.Category.ASSET).first()

        if payment.payment_method == "CASH":
            deposit_acc = coa.get("1000") or coa.get("1010") or ar_acc
        elif payment.payment_method in ["BANK_TRANSFER", "CARD"]:
            deposit_acc = coa.get("1010") or coa.get("1000") or ar_acc
        else:
            deposit_acc = coa.get("1020") or coa.get("1010") or coa.get("1000") or ar_acc

        amount = payment.amount
        rev_date = timezone.now().date()
        narration = f"Payment Reversal: {payment.payment_number} ({payment.reversal_reason or 'Payment Reversed'})"

        return create_journal_entry(
            organization=organization,
            actor=actor,
            txn_date=rev_date,
            narration=narration,
            reference_type=JournalEntry.ReferenceType.PAYMENT_REVERSAL,
            reference_id=ref_id,
            record_audit=False,
            lines=[
                {
                    "account": ar_acc,
                    "debit": amount,
                    "credit": Decimal("0.00"),
                    "description": f"Customer Receivable Reinstated: {payment.payment_number}",
                },
                {
                    "account": deposit_acc,
                    "debit": Decimal("0.00"),
                    "credit": amount,
                    "description": f"Reversal Disbursement from {deposit_acc.name}",
                },
            ],
        )
    except Exception as exc:
        logger.exception("Error creating payment reversal journal entry for %s: %s", getattr(payment, "payment_number", payment), exc)
        return None


def post_invoice_cancellation_journal_entry(invoice, actor=None) -> JournalEntry | None:
    """
    Idempotent hook for invoice cancellation / void:
    Debit: 4000 Internet Subscription Revenue
    Credit: 1200 Accounts Receivable (Subscribers)
    """
    try:
        organization = invoice.organization
        ref_id = f"CANCEL:{invoice.id}"

        # Idempotency check
        existing = (
            JournalEntry.objects
            .for_organization(organization)
            .filter(
                reference_type=JournalEntry.ReferenceType.INVOICE_CANCEL,
                reference_id=ref_id,
                status=JournalEntry.Status.POSTED,
            )
            .first()
        )
        if existing:
            return existing

        coa = get_or_create_default_chart_of_accounts(organization)
        ar_acc = coa.get("1200") or Account.objects.for_organization(organization).filter(category=Account.Category.ASSET).first()
        rev_acc = coa.get("4000") or Account.objects.for_organization(organization).filter(category=Account.Category.REVENUE).first()

        amount = invoice.total_amount
        if amount <= Decimal("0.00"):
            return None

        cancel_date = timezone.now().date()
        narration = f"Invoice Cancelled / Voided: {invoice.invoice_number} ({invoice.cancellation_reason or 'Cancelled'})"

        return create_journal_entry(
            organization=organization,
            actor=actor,
            txn_date=cancel_date,
            narration=narration,
            reference_type=JournalEntry.ReferenceType.INVOICE_CANCEL,
            reference_id=ref_id,
            record_audit=False,
            lines=[
                {
                    "account": rev_acc,
                    "debit": amount,
                    "credit": Decimal("0.00"),
                    "description": f"Revenue Reversed: {invoice.invoice_number}",
                },
                {
                    "account": ar_acc,
                    "debit": Decimal("0.00"),
                    "credit": amount,
                    "description": f"Customer Receivable Cancelled: {invoice.invoice_number}",
                },
            ],
        )
    except Exception as exc:
        logger.exception("Error creating invoice cancellation journal entry for %s: %s", getattr(invoice, "invoice_number", invoice), exc)
        return None
