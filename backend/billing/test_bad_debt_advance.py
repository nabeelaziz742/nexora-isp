from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounting.models import JournalEntry, JournalLine
from billing.models import Invoice, Payment
from billing.services import (
    BillingDomainError,
    cancel_invoice,
    generate_custom_invoice,
    generate_service_invoice,
    get_financial_ledger,
    get_service_advance_balance,
    record_payment_with_allocations,
    recover_bad_debt,
    reverse_payment,
    write_off_invoice,
)
from customers.models import BillingProfile, Customer, InternetPackage, ServiceAccount
from customers.suspension_services import calculate_service_outstanding
from tenancy.models import Organization, OrganizationMembership, StaffProfile


User = get_user_model()


class BillingFixtureMixin:
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name="Bad Debt ISP",
            code="BADDEBT-ISP",
            city="Lahore",
            currency="PKR",
        )
        self.owner = User.objects.create_user(
            username="baddebt-owner",
            email="baddebt-owner@nexora.local",
            password="StrongTestPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )
        customer = Customer.objects.create(
            organization=self.organization,
            customer_number="BD-CUST-001",
            first_name="Ali",
            last_name="Khan",
            phone="03004444441",
            address_line="Street 1",
            city="Lahore",
        )
        package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 20",
            code="BD-20",
            download_speed_mbps=20,
            upload_speed_mbps=10,
            monthly_price="2500.00",
        )
        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="BD-SRV-001",
            customer=customer,
            internet_package=package,
            status=ServiceAccount.Status.ACTIVE,
        )
        BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service,
            billing_day=1,
            due_day=10,
        )

    def make_invoice(self, month=9):
        return generate_service_invoice(
            organization=self.organization,
            actor=self.owner,
            service_account_id=self.service.id,
            billing_period_start=date(2026, month, 1),
            billing_period_end=date(2026, month, 28),
            issue_date=date(2026, month, 1),
            due_date=date(2026, month, 10),
        ).invoice

    def pay(self, amount, allocations=None):
        return record_payment_with_allocations(
            organization=self.organization,
            actor=self.owner,
            service_account_id=self.service.id,
            amount=amount,
            payment_method=Payment.Method.CASH,
            allocations=allocations,
        )

    def journal_total(self, reference_type, account_code, side):
        lines = JournalLine.objects.filter(
            journal_entry__organization=self.organization,
            journal_entry__reference_type=reference_type,
            account__code=account_code,
        )
        return sum((getattr(line, side) for line in lines), Decimal("0.00"))


class BadDebtWriteOffTests(BillingFixtureMixin, TestCase):
    def test_write_off_settles_outstanding_and_posts_expense(self):
        invoice = self.make_invoice()
        self.pay("1000.00")

        invoice = write_off_invoice(
            organization=self.organization,
            actor=self.owner,
            invoice_id=invoice.id,
            write_off_reason="Customer relocated abroad",
        )

        self.assertEqual(invoice.status, Invoice.Status.WRITTEN_OFF)
        self.assertEqual(invoice.written_off_amount, Decimal("1500.00"))
        self.assertEqual(invoice.outstanding_amount, Decimal("0.00"))
        self.assertEqual(invoice.written_off_by, self.owner)
        self.assertEqual(
            self.journal_total(JournalEntry.ReferenceType.BAD_DEBT_WRITE_OFF, "5070", "debit"),
            Decimal("1500.00"),
        )
        self.assertEqual(
            self.journal_total(JournalEntry.ReferenceType.BAD_DEBT_WRITE_OFF, "1200", "credit"),
            Decimal("1500.00"),
        )

    def test_written_off_invoice_leaves_collections_and_auto_allocation(self):
        invoice = self.make_invoice()
        write_off_invoice(
            organization=self.organization,
            actor=self.owner,
            invoice_id=invoice.id,
            write_off_reason="Uncollectible",
        )

        outstanding, unpaid, _ = calculate_service_outstanding(self.service)
        self.assertEqual(outstanding, Decimal("0.00"))
        self.assertEqual(unpaid, [])

        # A later ordinary payment must not silently land on the bad debt.
        payment = self.pay("500.00")
        self.assertEqual(payment.allocated_amount, Decimal("0.00"))

    def test_only_open_invoices_can_be_written_off(self):
        invoice = self.make_invoice()
        self.pay("2500.00")

        with self.assertRaisesMessage(BillingDomainError, "Only unpaid or partially paid"):
            write_off_invoice(
                organization=self.organization,
                actor=self.owner,
                invoice_id=invoice.id,
                write_off_reason="Paid already",
            )

    def test_write_off_requires_reason(self):
        invoice = self.make_invoice()
        with self.assertRaisesMessage(BillingDomainError, "reason is mandatory"):
            write_off_invoice(
                organization=self.organization,
                actor=self.owner,
                invoice_id=invoice.id,
                write_off_reason="  ",
            )

    def test_written_off_invoice_cannot_be_cancelled(self):
        invoice = self.make_invoice()
        write_off_invoice(
            organization=self.organization,
            actor=self.owner,
            invoice_id=invoice.id,
            write_off_reason="Uncollectible",
        )

        with self.assertRaisesMessage(BillingDomainError, "written off"):
            cancel_invoice(
                organization=self.organization,
                actor=self.owner,
                invoice_id=invoice.id,
                cancellation_reason="Trying to void",
            )


class BadDebtRecoveryTests(BillingFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.invoice = self.make_invoice()
        write_off_invoice(
            organization=self.organization,
            actor=self.owner,
            invoice_id=self.invoice.id,
            write_off_reason="Uncollectible",
        )

    def recover(self, amount):
        return recover_bad_debt(
            organization=self.organization,
            actor=self.owner,
            invoice_id=self.invoice.id,
            amount=amount,
            payment_method=Payment.Method.CASH,
            reference="RCV-1",
        )

    def test_partial_recovery_reinstates_and_collects(self):
        payment = self.recover("1000.00")

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.WRITTEN_OFF)
        self.assertEqual(self.invoice.written_off_amount, Decimal("1500.00"))
        self.assertEqual(self.invoice.bad_debt_recovered_amount, Decimal("1000.00"))
        self.assertEqual(self.invoice.paid_amount, Decimal("1000.00"))
        self.assertEqual(self.invoice.outstanding_amount, Decimal("0.00"))
        self.assertEqual(payment.allocated_amount, Decimal("1000.00"))
        # Net bad debt expense = written off minus recovered.
        self.assertEqual(
            self.journal_total(JournalEntry.ReferenceType.BAD_DEBT_RECOVERY, "5070", "credit"),
            Decimal("1000.00"),
        )

    def test_full_recovery_marks_invoice_paid(self):
        self.recover("2500.00")

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertEqual(self.invoice.written_off_amount, Decimal("0.00"))
        self.assertEqual(self.invoice.bad_debt_recovered_amount, Decimal("2500.00"))

    def test_recovery_cannot_exceed_written_off_balance(self):
        with self.assertRaisesMessage(BillingDomainError, "exceeds the written-off balance"):
            self.recover("2600.00")

    def test_reversing_recovery_writes_balance_off_again(self):
        payment = self.recover("1000.00")

        reverse_payment(
            organization=self.organization,
            actor=self.owner,
            payment_id=payment.id,
            reversal_reason="Cheque bounced",
        )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.WRITTEN_OFF)
        self.assertEqual(self.invoice.written_off_amount, Decimal("2500.00"))
        self.assertEqual(self.invoice.bad_debt_recovered_amount, Decimal("0.00"))
        self.assertEqual(self.invoice.outstanding_amount, Decimal("0.00"))
        self.assertEqual(
            self.journal_total(JournalEntry.ReferenceType.BAD_DEBT_WRITE_OFF, "5070", "debit"),
            Decimal("3500.00"),
        )

    def test_ledger_nets_write_off_and_recovery(self):
        self.recover("1000.00")

        ledger = get_financial_ledger(organization=self.organization, service_account_id=self.service.id)

        self.assertEqual(ledger["closing_balance"], Decimal("0.00"))
        self.assertEqual(ledger["advance_balance"], Decimal("0.00"))
        self.assertIn("WRITE_OFF", [entry["type"] for entry in ledger["entries"]])


class AdvanceBalanceTests(BillingFixtureMixin, TestCase):
    def test_overpayment_becomes_advance(self):
        self.make_invoice()
        self.pay("4000.00")

        self.assertEqual(get_service_advance_balance(service_account=self.service), Decimal("1500.00"))
        ledger = get_financial_ledger(organization=self.organization, service_account_id=self.service.id)
        self.assertEqual(ledger["advance_balance"], Decimal("1500.00"))

    def test_next_invoice_consumes_advance_automatically(self):
        self.pay("4000.00")

        invoice = self.make_invoice(month=10)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(invoice.paid_amount, Decimal("2500.00"))
        self.assertEqual(get_service_advance_balance(service_account=self.service), Decimal("1500.00"))

    def test_partial_advance_leaves_remaining_due(self):
        self.pay("1000.00")

        invoice = self.make_invoice(month=10)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PARTIALLY_PAID)
        self.assertEqual(invoice.outstanding_amount, Decimal("1500.00"))
        self.assertEqual(get_service_advance_balance(service_account=self.service), Decimal("0.00"))

    def test_advance_is_used_oldest_payment_first(self):
        first = self.pay("1000.00")
        second = self.pay("2000.00")

        self.make_invoice(month=10)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.unallocated_amount, Decimal("0.00"))
        self.assertEqual(second.unallocated_amount, Decimal("500.00"))

    def test_reversed_payment_is_not_advance(self):
        payment = self.pay("3000.00")
        reverse_payment(
            organization=self.organization,
            actor=self.owner,
            payment_id=payment.id,
            reversal_reason="Entered twice",
        )

        invoice = self.make_invoice(month=10)

        self.assertEqual(invoice.paid_amount, Decimal("0.00"))
        self.assertEqual(get_service_advance_balance(service_account=self.service), Decimal("0.00"))

    def test_custom_invoice_also_consumes_advance(self):
        self.pay("800.00")

        invoice = generate_custom_invoice(
            organization=self.organization,
            actor=self.owner,
            service_account_id=self.service.id,
            billing_period_start=date(2026, 10, 5),
            billing_period_end=date(2026, 10, 5),
            issue_date=date(2026, 10, 5),
            due_date=date(2026, 10, 15),
            line_items=[{"description": "Router replacement", "amount": "800.00"}],
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)


class BadDebtAPITests(BillingFixtureMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.invoice = self.make_invoice()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.login(self.owner)}")

    def login(self, user):
        response = self.client.post(
            reverse("tenant-login"),
            {
                "email": user.email,
                "password": "StrongTestPassword123!",
                "organization_code": self.organization.code,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["access"]

    def test_write_off_and_recovery_through_api(self):
        response = self.client.post(
            reverse("billing-invoice-write-off", kwargs={"invoice_id": self.invoice.id}),
            {"write_off_reason": "Customer unreachable for 6 months"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], Invoice.Status.WRITTEN_OFF)
        self.assertEqual(Decimal(response.data["written_off_amount"]), Decimal("2500.00"))

        response = self.client.post(
            reverse("billing-bad-debt-recovery", kwargs={"invoice_id": self.invoice.id}),
            {"amount": "700.00", "payment_method": Payment.Method.MOBILE_WALLET, "reference": "JC-123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Decimal(response.data["amount"]), Decimal("700.00"))

        summary = self.client.get(reverse("billing-summary")).data
        self.assertEqual(summary["written_off_count"], 1)
        self.assertEqual(Decimal(str(summary["total_written_off"])), Decimal("1800.00"))
        self.assertEqual(Decimal(str(summary["total_bad_debt_recovered"])), Decimal("700.00"))
        self.assertEqual(summary["overdue_count"], 0)

        listed = self.client.get(reverse("billing-invoice-list"), {"status": Invoice.Status.WRITTEN_OFF}).data
        rows = listed["results"] if isinstance(listed, dict) else listed
        self.assertEqual([row["invoice_number"] for row in rows], [self.invoice.invoice_number])

    def test_summary_reports_customer_advance(self):
        self.pay("4000.00")

        summary = self.client.get(reverse("billing-summary")).data

        self.assertEqual(Decimal(str(summary["total_advance"])), Decimal("1500.00"))

    def test_staff_without_finance_role_cannot_write_off(self):
        staff = User.objects.create_user(
            username="baddebt-staff",
            email="baddebt-staff@nexora.local",
            password="StrongTestPassword123!",
        )
        membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=staff,
            role=OrganizationMembership.Role.STAFF,
        )
        StaffProfile.objects.create(
            organization=self.organization,
            membership=membership,
            user=staff,
            staff_code="BADDEBT-ISP-STF-0001",
            role=StaffProfile.Role.OPERATOR,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.login(staff)}")

        response = self.client.post(
            reverse("billing-invoice-write-off", kwargs={"invoice_id": self.invoice.id}),
            {"write_off_reason": "Not allowed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.UNPAID)
