from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


from django.contrib.auth import get_user_model
from django.test import TestCase

from billing.models import (
    Invoice,
    Payment,
    PaymentAllocation,
)
from billing.services import (
    BillingDomainError,
    generate_service_invoice,
    record_invoice_payment,
)
from customers.models import (
    BillingProfile,
    Customer,
    InternetPackage,
    ServiceAccount,
)
from tenancy.models import (
    AuditLog,
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class BillingDomainTests(TestCase):
    def setUp(self):
        self.organization_a = Organization.objects.create(
            name="Billing ISP A",
            code="BILL-A",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.organization_b = Organization.objects.create(
            name="Billing ISP B",
            code="BILL-B",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.actor = User.objects.create_user(
            username="billing-owner",
            email="billing-owner@nexora.local",
            password="StrongTestPassword123!",
        )

        self.customer_a = Customer.objects.create(
            organization=self.organization_a,
            customer_number="BILL-CUST-A-001",
            first_name="Ali",
            phone="03001111111",
            address_line="Billing Address A",
            city="Lahore",
        )

        self.customer_b = Customer.objects.create(
            organization=self.organization_b,
            customer_number="BILL-CUST-B-001",
            first_name="Ahmed",
            phone="03002222222",
            address_line="Billing Address B",
            city="Karachi",
        )

        self.package_a = InternetPackage.objects.create(
            organization=self.organization_a,
            name="Fiber 50",
            code="BILL-A-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.package_b = InternetPackage.objects.create(
            organization=self.organization_b,
            name="Fiber 100",
            code="BILL-B-100",
            download_speed_mbps=100,
            upload_speed_mbps=50,
            monthly_price="8000.00",
        )

        self.service_a = ServiceAccount.objects.create(
            organization=self.organization_a,
            service_number="BILL-SRV-A-001",
            customer=self.customer_a,
            internet_package=self.package_a,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.service_b = ServiceAccount.objects.create(
            organization=self.organization_b,
            service_number="BILL-SRV-B-001",
            customer=self.customer_b,
            internet_package=self.package_b,
            status=ServiceAccount.Status.ACTIVE,
        )

        BillingProfile.objects.create(
            organization=self.organization_a,
            service_account=self.service_a,
            billing_day=1,
            due_day=10,
        )

        BillingProfile.objects.create(
            organization=self.organization_b,
            service_account=self.service_b,
            billing_day=1,
            due_day=10,
        )

    

    def generate_invoice_a(self):
        return generate_service_invoice(
            organization=self.organization_a,
            actor=self.actor,
            service_account_id=self.service_a.id,
            billing_period_start=date(2026, 7, 1),
            billing_period_end=date(2026, 7, 31),
            issue_date=date(2026, 7, 1),
            due_date=date(2026, 7, 10),
        )

    def test_invoice_generation_creates_package_charge(self):
        result = self.generate_invoice_a()

        self.assertEqual(
            result.invoice.total_amount,
            Decimal("5000.00"),
        )
        self.assertEqual(
            result.invoice.outstanding_amount,
            Decimal("5000.00"),
        )
        self.assertEqual(
            result.invoice.status,
            Invoice.Status.UNPAID,
        )

        self.assertEqual(
            result.invoice.lines.count(),
            1,
        )

    def test_duplicate_service_billing_period_is_blocked(self):
        self.generate_invoice_a()

        with self.assertRaises(BillingDomainError):
            self.generate_invoice_a()

        self.assertEqual(
            Invoice.objects
            .for_organization(self.organization_a)
            .count(),
            1,
        )

    def test_cross_tenant_service_invoice_is_blocked(self):
        with self.assertRaises(BillingDomainError):
            generate_service_invoice(
                organization=self.organization_a,
                actor=self.actor,
                service_account_id=self.service_b.id,
                billing_period_start=date(2026, 7, 1),
                billing_period_end=date(2026, 7, 31),
                issue_date=date(2026, 7, 1),
                due_date=date(2026, 7, 10),
            )

        self.assertEqual(
            Invoice.objects.count(),
            0,
        )

    def test_partial_payment_updates_invoice_status(self):
        invoice = self.generate_invoice_a().invoice

        result = record_invoice_payment(
            organization=self.organization_a,
            actor=self.actor,
            invoice_id=invoice.id,
            amount="2000.00",
            payment_method=Payment.Method.CASH,
        )

        result.invoice.refresh_from_db()

        self.assertEqual(
            result.invoice.status,
            Invoice.Status.PARTIALLY_PAID,
        )
        self.assertEqual(
            result.invoice.paid_amount,
            Decimal("2000.00"),
        )
        self.assertEqual(
            result.invoice.outstanding_amount,
            Decimal("3000.00"),
        )

    def test_full_payment_marks_invoice_paid(self):
        invoice = self.generate_invoice_a().invoice

        result = record_invoice_payment(
            organization=self.organization_a,
            actor=self.actor,
            invoice_id=invoice.id,
            amount="5000.00",
            payment_method=Payment.Method.BANK_TRANSFER,
            reference="BANK-REF-001",
        )

        result.invoice.refresh_from_db()

        self.assertEqual(
            result.invoice.status,
            Invoice.Status.PAID,
        )
        self.assertEqual(
            result.invoice.outstanding_amount,
            Decimal("0.00"),
        )

    def test_multiple_payments_can_complete_invoice(self):
        invoice = self.generate_invoice_a().invoice

        record_invoice_payment(
            organization=self.organization_a,
            actor=self.actor,
            invoice_id=invoice.id,
            amount="2000.00",
            payment_method=Payment.Method.CASH,
        )

        result = record_invoice_payment(
            organization=self.organization_a,
            actor=self.actor,
            invoice_id=invoice.id,
            amount="3000.00",
            payment_method=Payment.Method.CASH,
        )

        result.invoice.refresh_from_db()

        self.assertEqual(
            result.invoice.status,
            Invoice.Status.PAID,
        )
        self.assertEqual(
            Payment.objects
            .for_organization(self.organization_a)
            .count(),
            2,
        )
        self.assertEqual(
            PaymentAllocation.objects
            .for_organization(self.organization_a)
            .count(),
            2,
        )

    def test_payment_cannot_exceed_outstanding_amount(self):
        invoice = self.generate_invoice_a().invoice

        with self.assertRaises(BillingDomainError):
            record_invoice_payment(
                organization=self.organization_a,
                actor=self.actor,
                invoice_id=invoice.id,
                amount="5000.01",
                payment_method=Payment.Method.CASH,
            )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

        self.assertEqual(
            PaymentAllocation.objects.count(),
            0,
        )

    def test_cross_tenant_invoice_payment_is_blocked(self):
        invoice = self.generate_invoice_a().invoice

        with self.assertRaises(BillingDomainError):
            record_invoice_payment(
                organization=self.organization_b,
                actor=self.actor,
                invoice_id=invoice.id,
                amount="1000.00",
                payment_method=Payment.Method.CASH,
            )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_invoice_generation_records_audit_event(self):
        self.generate_invoice_a()

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization_a,
                action="BILLING_INVOICE_GENERATED",
            ).exists()
        )

    def test_payment_records_audit_event(self):
        invoice = self.generate_invoice_a().invoice

        record_invoice_payment(
            organization=self.organization_a,
            actor=self.actor,
            invoice_id=invoice.id,
            amount="1000.00",
            payment_method=Payment.Method.CASH,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization_a,
                action="BILLING_PAYMENT_RECORDED",
            ).exists()
        )


class BillingOperationalAPITests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Billing ISP",
            code="BILLING-API",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Billing ISP",
            code="OTHER-BILLING",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.owner = User.objects.create_user(
            username="billing-api-owner",
            email="billing-api-owner@nexora.local",
            password="StrongTestPassword123!",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="API-BILL-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03003333331",
            address_line="Billing API Street",
            city="Lahore",
        )

        self.other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-BILL-CUST-001",
            first_name="Other",
            last_name="Customer",
            phone="03003333332",
            address_line="Other Billing Street",
            city="Karachi",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 50",
            code="API-BILL-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Fiber 100",
            code="OTHER-BILL-100",
            download_speed_mbps=100,
            upload_speed_mbps=50,
            monthly_price="8000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="API-BILL-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.other_service = ServiceAccount.objects.create(
            organization=self.other_organization,
            service_number="OTHER-BILL-SRV-001",
            customer=self.other_customer,
            internet_package=self.other_package,
            status=ServiceAccount.Status.ACTIVE,
        )

        BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service,
            billing_day=1,
            due_day=10,
        )

        BillingProfile.objects.create(
            organization=self.other_organization,
            service_account=self.other_service,
            billing_day=1,
            due_day=10,
        )

        self.invoice = generate_service_invoice(
            organization=self.organization,
            actor=self.owner,
            service_account_id=self.service.id,
            billing_period_start=date(2026, 7, 1),
            billing_period_end=date(2026, 7, 31),
            issue_date=date(2026, 7, 1),
            due_date=date(2026, 7, 10),
        ).invoice

        self.other_invoice = generate_service_invoice(
            organization=self.other_organization,
            actor=self.owner,
            service_account_id=self.other_service.id,
            billing_period_start=date(2026, 7, 1),
            billing_period_end=date(2026, 7, 31),
            issue_date=date(2026, 7, 1),
            due_date=date(2026, 7, 10),
        ).invoice

        self.authenticate_owner()

    def authenticate_owner(self):
        response = self.client.post(
            reverse("tenant-login"),
            {
                "email": self.owner.email,
                "password": "StrongTestPassword123!",
                "organization_code": self.organization.code,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {response.data['access']}"
            )
        )

    def test_invoice_list_returns_only_current_tenant_invoices(self):
        response = self.client.get(
            reverse("billing-invoice-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["invoice_number"],
            self.invoice.invoice_number,
        )

    def test_invoice_detail_returns_financial_context(self):
        response = self.client.get(
            reverse(
                "billing-invoice-detail",
                kwargs={
                    "invoice_id": self.invoice.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["total_amount"],
            "5000.00",
        )
        self.assertEqual(
            response.data["outstanding_amount"],
            "5000.00",
        )
        self.assertEqual(
            len(response.data["lines"]),
            1,
        )

    def test_invoice_detail_blocks_cross_tenant_invoice(self):
        response = self.client.get(
            reverse(
                "billing-invoice-detail",
                kwargs={
                    "invoice_id": self.other_invoice.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_record_payment_action_records_partial_payment(self):
        response = self.client.post(
            reverse(
                "billing-invoice-payment-record",
                kwargs={
                    "invoice_id": self.invoice.id,
                },
            ),
            {
                "amount": "2000.00",
                "payment_method": Payment.Method.CASH,
                "reference": "CASH-001",
                "notes": "Counter payment",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.invoice.refresh_from_db()

        self.assertEqual(
            self.invoice.status,
            Invoice.Status.PARTIALLY_PAID,
        )
        self.assertEqual(
            response.data["amount"],
            "2000.00",
        )

    def test_record_payment_action_blocks_cross_tenant_invoice(self):
        response = self.client.post(
            reverse(
                "billing-invoice-payment-record",
                kwargs={
                    "invoice_id": self.other_invoice.id,
                },
            ),
            {
                "amount": "1000.00",
                "payment_method": Payment.Method.CASH,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertFalse(
            Payment.objects
            .for_organization(self.organization)
            .exists()
        )

    def test_payment_list_returns_current_tenant_payments(self):
        record_invoice_payment(
            organization=self.organization,
            actor=self.owner,
            invoice_id=self.invoice.id,
            amount="1000.00",
            payment_method=Payment.Method.CASH,
        )

        response = self.client.get(
            reverse("billing-payment-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["service_number"],
            self.service.service_number,
        )

    def test_billing_summary_returns_real_ledger_totals(self):
        record_invoice_payment(
            organization=self.organization,
            actor=self.owner,
            invoice_id=self.invoice.id,
            amount="2000.00",
            payment_method=Payment.Method.CASH,
        )

        response = self.client.get(
            reverse("billing-summary")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["currency"],
            "PKR",
        )
        self.assertEqual(
            response.data["total_invoiced"],
            Decimal("5000.00"),
        )
        self.assertEqual(
            response.data["total_paid"],
            Decimal("2000.00"),
        )
        self.assertEqual(
            response.data["total_outstanding"],
            Decimal("3000.00"),
        )
        self.assertEqual(
            response.data["partially_paid_count"],
            1,
        )

class MonthlyBillingGenerationTests(
    BillingDomainTests
):
    def test_monthly_generation_creates_invoice(self):
        from billing.services import (
            generate_monthly_invoices,
        )

        result = generate_monthly_invoices(
            organization=self.organization_a,
            actor=self.actor,
            billing_year=2026,
            billing_month=8,
        )

        self.assertEqual(
            result.eligible_services,
            1,
        )
        self.assertEqual(
            result.generated_invoices,
            1,
        )
        self.assertEqual(
            result.skipped_existing_invoices,
            0,
        )

        invoice = (
            Invoice.objects
            .for_organization(self.organization_a)
            .get()
        )

        self.assertEqual(
            invoice.billing_period_start,
            date(2026, 8, 1),
        )
        self.assertEqual(
            invoice.billing_period_end,
            date(2026, 8, 31),
        )
        self.assertEqual(
            invoice.issue_date,
            date(2026, 8, 1),
        )
        self.assertEqual(
            invoice.due_date,
            date(2026, 8, 10),
        )
        self.assertEqual(
            invoice.total_amount,
            Decimal("5000.00"),
        )

    def test_monthly_generation_skips_duplicate_period(
        self,
    ):
        from billing.services import (
            generate_monthly_invoices,
        )

        generate_monthly_invoices(
            organization=self.organization_a,
            actor=self.actor,
            billing_year=2026,
            billing_month=8,
        )

        result = generate_monthly_invoices(
            organization=self.organization_a,
            actor=self.actor,
            billing_year=2026,
            billing_month=8,
        )

        self.assertEqual(
            result.generated_invoices,
            0,
        )
        self.assertEqual(
            result.skipped_existing_invoices,
            1,
        )

        self.assertEqual(
            Invoice.objects
            .for_organization(self.organization_a)
            .count(),
            1,
        )

    def test_monthly_generation_is_tenant_scoped(self):
        from billing.services import (
            generate_monthly_invoices,
        )

        generate_monthly_invoices(
            organization=self.organization_a,
            actor=self.actor,
            billing_year=2026,
            billing_month=8,
        )

        self.assertEqual(
            Invoice.objects
            .for_organization(self.organization_a)
            .count(),
            1,
        )

        self.assertEqual(
            Invoice.objects
            .for_organization(self.organization_b)
            .count(),
            0,
        )

    def test_full_payment_records_fully_paid_audit(
        self,
    ):
        invoice = self.generate_invoice_a().invoice

        record_invoice_payment(
            organization=self.organization_a,
            actor=self.actor,
            invoice_id=invoice.id,
            amount="5000.00",
            payment_method=Payment.Method.CASH,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization_a,
                action="BILLING_INVOICE_FULLY_PAID",
                resource_id=invoice.id,
            ).exists()
        )

    def test_partial_payment_does_not_record_fully_paid_audit(
        self,
    ):
        invoice = self.generate_invoice_a().invoice

        record_invoice_payment(
            organization=self.organization_a,
            actor=self.actor,
            invoice_id=invoice.id,
            amount="2000.00",
            payment_method=Payment.Method.CASH,
        )

        self.assertFalse(
            AuditLog.objects.filter(
                organization=self.organization_a,
                action="BILLING_INVOICE_FULLY_PAID",
                resource_id=invoice.id,
            ).exists()
        )


class BillingFilterAPITests(
    BillingOperationalAPITests
):
    def test_invoice_filter_by_billing_period(self):
        response = self.client.get(
            reverse("billing-invoice-list"),
            {
                "billing_period": "2026-07",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_invalid_billing_period_is_rejected(self):
        response = self.client.get(
            reverse("billing-invoice-list"),
            {
                "billing_period": "invalid",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_billing_summary_contains_overdue_metrics(
        self,
    ):
        response = self.client.get(
            reverse("billing-summary")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "overdue_count",
            response.data,
        )

        self.assertIn(
            "overdue_outstanding",
            response.data,
        )