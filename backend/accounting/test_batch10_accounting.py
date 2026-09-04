import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

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
from accounting.services import (
    AccountingDomainError,
    accrue_dealer_commission,
    close_financial_period,
    create_journal_entry,
    get_general_ledger,
    get_or_create_default_chart_of_accounts,
    get_trial_balance,
    post_invoice_cancellation_journal_entry,
    post_invoice_journal_entry,
    post_payment_journal_entry,
    post_payment_reversal_journal_entry,
    record_dealer_settlement,
    record_direct_income,
    record_expense,
    reopen_financial_period,
    resolve_financial_period,
    reverse_journal_entry,
    transfer_funds,
)
from billing.models import Invoice, InvoiceLine, Payment, PaymentAllocation
from customers.models import BillingProfile, Customer, Dealer, InternetPackage, ServiceAccount
from tenancy.models import AuditLog, Organization, OrganizationMembership

User = get_user_model()


class Batch10AccountingTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Organization 1 (Main Tenant)
        self.org = Organization.objects.create(
            name="Nexora Fiber Alpha",
            code="NX-ALPHA",
            currency="PKR",
            is_active=True,
        )

        # Organization 2 (Tenant Isolation Check)
        self.other_org = Organization.objects.create(
            name="Beta Telecom",
            code="NX-BETA",
            currency="PKR",
            is_active=True,
        )

        # Users
        self.owner_user = User.objects.create_user(
            username="owner_alpha",
            email="owner@alpha.com",
            password="Password123!",
            first_name="Alpha",
            last_name="Owner",
        )
        self.owner_membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.owner_user,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

        self.accountant_user = User.objects.create_user(
            username="accountant_alpha",
            email="accountant@alpha.com",
            password="Password123!",
            first_name="Alpha",
            last_name="Accountant",
        )
        self.accountant_membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.accountant_user,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        from tenancy.models import StaffProfile
        StaffProfile.objects.create(
            organization=self.org,
            user=self.accountant_user,
            membership=self.accountant_membership,
            staff_code="NX-ACC-01",
            role=StaffProfile.Role.ACCOUNTANT,
        )

        self.other_user = User.objects.create_user(
            username="user_beta",
            email="user@beta.com",
            password="Password123!",
            first_name="Beta",
            last_name="Staff",
        )
        self.other_membership = OrganizationMembership.objects.create(
            organization=self.other_org,
            user=self.other_user,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

        # JWT Tokens
        token_acc = RefreshToken.for_user(self.accountant_user)
        token_acc["organization_id"] = str(self.org.id)
        self.auth_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {str(token_acc.access_token)}",
        }

        token_other = RefreshToken.for_user(self.other_user)
        token_other["organization_id"] = str(self.other_org.id)
        self.other_auth_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {str(token_other.access_token)}",
        }

    # -------------------------------------------------------------------------
    # 1. CHART OF ACCOUNTS TESTS
    # -------------------------------------------------------------------------
    def test_default_chart_of_accounts_provisioning(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        self.assertGreaterEqual(len(coa), 18)

        # Check key system accounts
        self.assertIn("1000", coa)
        self.assertIn("1010", coa)
        self.assertIn("1200", coa)
        self.assertIn("2000", coa)
        self.assertIn("2010", coa)
        self.assertIn("4000", coa)
        self.assertIn("5000", coa)
        self.assertIn("5060", coa)

        self.assertTrue(coa["1200"].is_system)
        self.assertEqual(coa["1200"].category, Account.Category.ASSET)
        self.assertEqual(coa["4000"].category, Account.Category.REVENUE)

    def test_account_creation_and_uniqueness(self):
        acc = Account.objects.create(
            organization=self.org,
            code="1050",
            name="Petty Cash Drawer 2",
            category=Account.Category.ASSET,
            account_type=Account.AccountType.CURRENT_ASSET,
            is_active=True,
        )
        self.assertEqual(acc.code, "1050")

        # Duplicate code in same org should fail
        with transaction.atomic():
            with self.assertRaises(Exception):
                Account.objects.create(
                    organization=self.org,
                    code="1050",
                    name="Duplicate Code",
                    category=Account.Category.ASSET,
                    account_type=Account.AccountType.CURRENT_ASSET,
                )

        # Same code in different org should succeed (Tenant Scoped)
        acc_beta = Account.objects.create(
            organization=self.other_org,
            code="1050",
            name="Beta Petty Cash",
            category=Account.Category.ASSET,
            account_type=Account.AccountType.CURRENT_ASSET,
        )
        self.assertEqual(acc_beta.organization, self.other_org)

    # -------------------------------------------------------------------------
    # 2. DOUBLE-ENTRY JOURNAL ENTRY TESTS
    # -------------------------------------------------------------------------
    def test_balanced_journal_entry_creation(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        today = timezone.now().date()

        lines = [
            {"account": coa["1000"], "debit": Decimal("5000.00"), "credit": Decimal("0.00")},
            {"account": coa["4090"], "debit": Decimal("0.00"), "credit": Decimal("5000.00")},
        ]

        entry = create_journal_entry(
            organization=self.org,
            actor=self.accountant_user,
            txn_date=today,
            narration="Scrap equipment sale",
            lines=lines,
        )

        self.assertIsNotNone(entry.id)
        self.assertTrue(entry.entry_number.startswith("NX-ALPHA-JE-"))
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(entry.total_debit, Decimal("5000.00"))
        self.assertEqual(entry.total_credit, Decimal("5000.00"))
        self.assertTrue(entry.is_balanced)
        self.assertEqual(entry.lines.count(), 2)

    def test_unbalanced_journal_entry_rejected(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        today = timezone.now().date()

        lines = [
            {"account": coa["1000"], "debit": Decimal("5000.00"), "credit": Decimal("0.00")},
            {"account": coa["4090"], "debit": Decimal("0.00"), "credit": Decimal("4000.00")},
        ]

        with self.assertRaises(AccountingDomainError) as ctx:
            create_journal_entry(
                organization=self.org,
                actor=self.accountant_user,
                txn_date=today,
                narration="Unbalanced Test",
                lines=lines,
            )
        self.assertIn("Unbalanced journal entry", str(ctx.exception))

    def test_journal_entry_reversal(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        today = timezone.now().date()

        entry = create_journal_entry(
            organization=self.org,
            actor=self.accountant_user,
            txn_date=today,
            narration="Original entry to reverse",
            lines=[
                {"account": coa["1010"], "debit": Decimal("15000.00"), "credit": Decimal("0.00")},
                {"account": coa["4000"], "debit": Decimal("0.00"), "credit": Decimal("15000.00")},
            ],
        )

        reversal = reverse_journal_entry(
            organization=self.org,
            actor=self.accountant_user,
            entry_id=entry.id,
            reversal_reason="Mistaken manual entry",
        )

        entry.refresh_from_db()
        self.assertEqual(entry.status, JournalEntry.Status.REVERSED)
        self.assertEqual(reversal.status, JournalEntry.Status.POSTED)
        self.assertEqual(reversal.reversed_entry, entry)

        # Check that debit and credit are swapped
        rev_lines = reversal.lines.all().order_by("line_order")
        self.assertEqual(rev_lines[0].account, coa["1010"])
        self.assertEqual(rev_lines[0].credit, Decimal("15000.00"))
        self.assertEqual(rev_lines[1].account, coa["4000"])
        self.assertEqual(rev_lines[1].debit, Decimal("15000.00"))

    # -------------------------------------------------------------------------
    # 3. GENERAL LEDGER & TRIAL BALANCE TESTS
    # -------------------------------------------------------------------------
    def test_general_ledger_and_running_balance(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        t1 = date(2026, 9, 1)
        t2 = date(2026, 9, 2)
        t3 = date(2026, 9, 3)

        # Txn 1: +10,000 to Bank
        create_journal_entry(
            organization=self.org,
            actor=self.accountant_user,
            txn_date=t1,
            narration="Capital deposit",
            lines=[
                {"account": coa["1010"], "debit": Decimal("10000.00"), "credit": Decimal("0.00")},
                {"account": coa["3000"], "debit": Decimal("0.00"), "credit": Decimal("10000.00")},
            ],
        )

        # Txn 2: -3,000 from Bank for Rent
        create_journal_entry(
            organization=self.org,
            actor=self.accountant_user,
            txn_date=t2,
            narration="Rent payment",
            lines=[
                {"account": coa["5040"], "debit": Decimal("3000.00"), "credit": Decimal("0.00")},
                {"account": coa["1010"], "debit": Decimal("0.00"), "credit": Decimal("3000.00")},
            ],
        )

        # Txn 3: +5,000 to Bank from Service
        create_journal_entry(
            organization=self.org,
            actor=self.accountant_user,
            txn_date=t3,
            narration="Service collection",
            lines=[
                {"account": coa["1010"], "debit": Decimal("5000.00"), "credit": Decimal("0.00")},
                {"account": coa["4000"], "debit": Decimal("0.00"), "credit": Decimal("5000.00")},
            ],
        )

        ledger = get_general_ledger(
            organization=self.org,
            account_id=coa["1010"].id,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
        )

        self.assertEqual(ledger["opening_balance"], "0.00")
        self.assertEqual(ledger["total_debits"], "15000.00")
        self.assertEqual(ledger["total_credits"], "3000.00")
        self.assertEqual(ledger["closing_balance"], "12000.00")
        self.assertEqual(len(ledger["entries"]), 3)

    def test_trial_balance_equality(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        today = date(2026, 9, 15)

        create_journal_entry(
            organization=self.org,
            actor=self.accountant_user,
            txn_date=today,
            narration="Trial Balance Seed Txn",
            lines=[
                {"account": coa["1010"], "debit": Decimal("50000.00"), "credit": Decimal("0.00")},
                {"account": coa["1200"], "debit": Decimal("20000.00"), "credit": Decimal("0.00")},
                {"account": coa["3000"], "debit": Decimal("0.00"), "credit": Decimal("50000.00")},
                {"account": coa["4000"], "debit": Decimal("0.00"), "credit": Decimal("20000.00")},
            ],
        )

        tb = get_trial_balance(organization=self.org, as_of_date=today)
        self.assertTrue(tb["is_balanced"])
        self.assertEqual(tb["total_debits"], "70000.00")
        self.assertEqual(tb["total_credits"], "70000.00")

    # -------------------------------------------------------------------------
    # 4. CASH, BANK & FUND TRANSFER TESTS
    # -------------------------------------------------------------------------
    def test_fund_transfer_between_accounts(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        today = timezone.now().date()

        transfer = transfer_funds(
            organization=self.org,
            actor=self.accountant_user,
            from_account_id=coa["1010"].id,
            to_account_id=coa["1000"].id,
            amount=Decimal("10000.00"),
            date_val=today,
            reference="CHQ-8899",
            description="Withdraw cash for office drawer",
        )

        self.assertIsNotNone(transfer.journal_entry)
        self.assertEqual(transfer.journal_entry.status, JournalEntry.Status.POSTED)
        self.assertTrue(transfer.journal_entry.is_balanced)
        self.assertEqual(transfer.journal_entry.total_debit, Decimal("10000.00"))

    # -------------------------------------------------------------------------
    # 5. EXPENSE & DIRECT INCOME TESTS
    # -------------------------------------------------------------------------
    def test_expense_recording(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        today = timezone.now().date()

        exp = record_expense(
            organization=self.org,
            actor=self.accountant_user,
            expense_account_id=coa["5020"].id,  # Electricity
            payment_account_id=coa["1010"].id,  # Bank
            amount=Decimal("12500.00"),
            date_val=today,
            payee="LESCO Power Distribution",
            category="Utilities",
            reference="BILL-998822",
            description="PoP 1 August Electricity",
        )

        self.assertIsNotNone(exp.journal_entry)
        self.assertEqual(exp.amount, Decimal("12500.00"))
        self.assertEqual(exp.journal_entry.total_debit, Decimal("12500.00"))
        self.assertEqual(exp.journal_entry.total_credit, Decimal("12500.00"))

    def test_direct_income_recording(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        today = timezone.now().date()

        inc = record_direct_income(
            organization=self.org,
            actor=self.accountant_user,
            income_account_id=coa["4090"].id,
            deposit_account_id=coa["1000"].id,
            amount=Decimal("4500.00"),
            date_val=today,
            received_from="Ahmed Electronics",
            reference="REC-4433",
            description="Used router sale",
        )

        self.assertIsNotNone(inc.journal_entry)
        self.assertEqual(inc.amount, Decimal("4500.00"))
        self.assertEqual(inc.journal_entry.total_debit, Decimal("4500.00"))

    # -------------------------------------------------------------------------
    # 6. IDEMPOTENT BILLING INTEGRATION HOOKS TESTS
    # -------------------------------------------------------------------------
    def test_invoice_creation_journal_hook_and_idempotency(self):
        coa = get_or_create_default_chart_of_accounts(self.org)

        # Create Customer, Service, and BillingProfile
        pkg = InternetPackage.objects.create(
            organization=self.org,
            name="Fast Fiber 50",
            code="FF-50",
            monthly_price=Decimal("3500.00"),
            download_speed_mbps=50,
            upload_speed_mbps=50,
        )
        cust = Customer.objects.create(
            organization=self.org,
            customer_number="NX-CUST-100",
            first_name="Zubair",
            last_name="Khan",
            phone="03001234567",
        )
        srv = ServiceAccount.objects.create(
            organization=self.org,
            customer=cust,
            service_number="NX-SRV-100",
            internet_package=pkg,
            status=ServiceAccount.Status.ACTIVE,
        )
        bp = BillingProfile.objects.create(
            organization=self.org,
            service_account=srv,
            billing_day=1,
            due_day=10,
        )
        inv = Invoice.objects.create(
            organization=self.org,
            invoice_number="NX-ALPHA-INV-000100",
            service_account=srv,
            billing_profile=bp,
            billing_period_start=date(2026, 9, 1),
            billing_period_end=date(2026, 9, 30),
            issue_date=date(2026, 9, 1),
            due_date=date(2026, 9, 10),
            status=Invoice.Status.UNPAID,
        )
        InvoiceLine.objects.create(
            organization=self.org,
            invoice=inv,
            description="Monthly Internet",
            amount=Decimal("3500.00"),
        )

        je1 = post_invoice_journal_entry(invoice=inv, actor=self.accountant_user)
        self.assertIsNotNone(je1)
        self.assertEqual(je1.total_debit, Decimal("3500.00"))
        self.assertEqual(je1.total_credit, Decimal("3500.00"))

        # Idempotency: Repeating hook must return exact same entry without creating duplicate records
        je2 = post_invoice_journal_entry(invoice=inv, actor=self.accountant_user)
        self.assertEqual(je1.id, je2.id)
        self.assertEqual(JournalEntry.objects.filter(reference_type="INVOICE", reference_id=str(inv.id)).count(), 1)

    def test_payment_and_reversal_journal_hook(self):
        coa = get_or_create_default_chart_of_accounts(self.org)

        pkg = InternetPackage.objects.create(
            organization=self.org,
            name="Fast Fiber 25",
            code="FF-25",
            monthly_price=Decimal("2500.00"),
            download_speed_mbps=25,
            upload_speed_mbps=25,
        )
        cust = Customer.objects.create(
            organization=self.org,
            customer_number="NX-CUST-101",
            first_name="Tariq",
            last_name="Ali",
            phone="03007654321",
        )
        srv = ServiceAccount.objects.create(
            organization=self.org,
            customer=cust,
            service_number="NX-SRV-101",
            internet_package=pkg,
            status=ServiceAccount.Status.ACTIVE,
        )

        payment = Payment.objects.create(
            organization=self.org,
            payment_number="NX-ALPHA-PAY-000101",
            service_account=srv,
            amount=Decimal("2500.00"),
            payment_method=Payment.Method.CASH,
            paid_at=timezone.now(),
        )

        je_pay = post_payment_journal_entry(payment=payment, actor=self.accountant_user)
        self.assertIsNotNone(je_pay)
        self.assertEqual(je_pay.total_debit, Decimal("2500.00"))
        self.assertEqual(je_pay.total_credit, Decimal("2500.00"))

        # Payment Reversal Hook
        payment.is_reversed = True
        payment.reversal_reason = "Bounce / Fraud"
        payment.save()

        je_rev = post_payment_reversal_journal_entry(payment=payment, actor=self.accountant_user)
        self.assertIsNotNone(je_rev)
        self.assertEqual(je_rev.total_debit, Decimal("2500.00"))
        self.assertEqual(je_rev.total_credit, Decimal("2500.00"))

    # -------------------------------------------------------------------------
    # 7. DEALER COMMISSION ACCRUAL & SETTLEMENT TESTS
    # -------------------------------------------------------------------------
    def test_dealer_commission_accrual_and_settlement(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        dealer = Dealer.objects.create(
            organization=self.org,
            dealer_code="DLR-001",
            name="Johar Town Broadband",
            commission_rate_percentage=Decimal("15.00"),
            commission_type=Dealer.CommissionType.PERCENTAGE,
            joining_date=date(2026, 1, 1),
            status=Dealer.Status.ACTIVE,
            phone="03009998877",
        )

        # Accrue Commission: 15% of 100,000 = 15,000
        p_start = date(2026, 9, 1)
        p_end = date(2026, 9, 30)
        je_accrual = accrue_dealer_commission(
            organization=self.org,
            actor=self.accountant_user,
            dealer_id=dealer.id,
            period_start=p_start,
            period_end=p_end,
            commission_amount=Decimal("15000.00"),
        )
        self.assertIsNotNone(je_accrual)
        self.assertEqual(je_accrual.total_debit, Decimal("15000.00"))

        # Idempotency check
        je_accrual_2 = accrue_dealer_commission(
            organization=self.org,
            actor=self.accountant_user,
            dealer_id=dealer.id,
            period_start=p_start,
            period_end=p_end,
            commission_amount=Decimal("15000.00"),
        )
        self.assertEqual(je_accrual.id, je_accrual_2.id)

        # Settle Commission via Bank
        settlement = record_dealer_settlement(
            organization=self.org,
            actor=self.accountant_user,
            dealer_id=dealer.id,
            payment_account_id=coa["1010"].id,
            amount=Decimal("15000.00"),
            period_start=p_start,
            period_end=p_end,
            settlement_date=date(2026, 10, 5),
            notes="Full payout via bank transfer",
        )
        self.assertIsNotNone(settlement.journal_entry)
        self.assertEqual(settlement.amount, Decimal("15000.00"))
        self.assertEqual(settlement.journal_entry.total_debit, Decimal("15000.00"))

    # -------------------------------------------------------------------------
    # 8. FINANCIAL PERIOD LOCK & REOPEN TESTS
    # -------------------------------------------------------------------------
    def test_financial_period_locking(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        period = FinancialPeriod.objects.create(
            organization=self.org,
            name="2026-08",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            is_closed=False,
        )

        # Close period
        close_financial_period(
            organization=self.org,
            actor=self.owner_user,
            period_id=period.id,
        )
        period.refresh_from_db()
        self.assertTrue(period.is_closed)

        # Attempting to post transaction in closed period must raise domain error
        with self.assertRaises(AccountingDomainError) as ctx:
            create_journal_entry(
                organization=self.org,
                actor=self.accountant_user,
                txn_date=date(2026, 8, 15),
                narration="Backdated posting attempt",
                lines=[
                    {"account": coa["1000"], "debit": Decimal("1000.00"), "credit": Decimal("0.00")},
                    {"account": coa["4090"], "debit": Decimal("0.00"), "credit": Decimal("1000.00")},
                ],
            )
        self.assertIn("closed", str(ctx.exception).lower())

        # Reopen period
        reopen_financial_period(
            organization=self.org,
            actor=self.owner_user,
            period_id=period.id,
            reopen_reason="Auditor authorized adjustment",
        )
        period.refresh_from_db()
        self.assertFalse(period.is_closed)

        # Posting now succeeds
        entry = create_journal_entry(
            organization=self.org,
            actor=self.accountant_user,
            txn_date=date(2026, 8, 15),
            narration="Authorized adjustment after reopen",
            lines=[
                {"account": coa["1000"], "debit": Decimal("1000.00"), "credit": Decimal("0.00")},
                {"account": coa["4090"], "debit": Decimal("0.00"), "credit": Decimal("1000.00")},
            ],
        )
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)

    # -------------------------------------------------------------------------
    # 9. REST API & RBAC PERMISSIONS TESTS
    # -------------------------------------------------------------------------
    def test_api_overview_endpoint(self):
        url = "/api/v1/accounting/overview/"
        resp = self.client.get(url, **self.auth_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("metrics", resp.data)
        self.assertIn("cash_bank_balance", resp.data["metrics"])
        self.assertIn("receivables_balance", resp.data["metrics"])

    def test_api_create_account_and_tenant_isolation(self):
        url = "/api/v1/accounting/accounts/"
        payload = {
            "code": "1099",
            "name": "Special Reserve Cash",
            "category": "ASSET",
            "account_type": "CURRENT_ASSET",
            "description": "Emergency cash buffer",
        }
        resp = self.client.post(url, payload, format="json", **self.auth_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["code"], "1099")

        # Verify other tenant cannot see this account
        resp_other = self.client.get(url, **self.other_auth_headers)
        self.assertEqual(resp_other.status_code, status.HTTP_200_OK)
        codes = [acc["code"] for acc in resp_other.data]
        self.assertNotIn("1099", codes)

    def test_api_trial_balance_endpoint(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        url = "/api/v1/accounting/trial-balance/"
        resp = self.client.get(url, **self.auth_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("total_debits", resp.data)
        self.assertIn("total_credits", resp.data)
        self.assertTrue(resp.data["is_balanced"])
