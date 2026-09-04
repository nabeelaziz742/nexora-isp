from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


from django.contrib.auth import get_user_model
from django.test import TestCase

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
    PromiseToPay,
    RecoveryAllocation,
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
        items = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(items), 1)
        self.assertEqual(
            items[0]["invoice_number"],
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
        items = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(items), 1)
        self.assertEqual(
            items[0]["service_number"],
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

        items = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(
            len(items),
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


class PromiseToPayLifecycleTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Alpha Fiber Net",
            code="ALPHA",
            is_active=True,
        )
        self.other_organization = Organization.objects.create(
            name="Beta Telecom",
            code="BETA",
            is_active=True,
        )
        self.owner = User.objects.create_user(
            username="alpha_owner@nexora.local",
            password="StrongPassword123!",
            email="alpha_owner@nexora.local",
        )
        self.other_owner = User.objects.create_user(
            username="beta_owner@nexora.local",
            password="StrongPassword123!",
            email="beta_owner@nexora.local",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Super Fiber 50",
            code="SF-50",
            download_speed_mbps=50,
            upload_speed_mbps=50,
            monthly_price=3500.00,
            is_active=True,
        )
        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="ALPHA-CUST-00001",
            first_name="Usman",
            last_name="Ghani",
            phone="03001234567",
            address_line="Flat 1, Building A",
            city="Islamabad",
            is_active=True,
        )
        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            customer=self.customer,
            service_number="ALPHA-SRV-00001",
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )
        self.billing_profile = BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service,
            billing_day=1,
            due_day=10,
            is_active=True,
        )
        self.invoice_res = generate_service_invoice(
            organization=self.organization,
            actor=self.owner,
            service_account_id=self.service.id,
            billing_period_start=date(2026, 9, 1),
            billing_period_end=date(2026, 9, 30),
            issue_date=date(2026, 9, 1),
            due_date=date(2026, 9, 10),
        )

    def auth(self, user, org):
        login_res = self.client.post(
            reverse("tenant-login"),
            {
                "organization_code": org.code,
                "email": user.email,
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_res.data['access']}"
        )

    def test_promise_to_pay_crud_and_validation(self):
        self.auth(self.owner, self.organization)

        # 1. Invalid deadline (earlier than promise date) -> Must fail
        bad_res = self.client.post(
            reverse("billing-promise-list-create"),
            {
                "customer_id": str(self.customer.id),
                "service_account_id": str(self.service.id),
                "invoice_id": str(self.invoice_res.invoice.id),
                "promised_amount": "3500.00",
                "promise_date": "2026-09-10",
                "deadline": "2026-09-05",
            },
            format="json",
        )
        self.assertEqual(bad_res.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Valid Promise creation
        create_res = self.client.post(
            reverse("billing-promise-list-create"),
            {
                "customer_id": str(self.customer.id),
                "service_account_id": str(self.service.id),
                "invoice_id": str(self.invoice_res.invoice.id),
                "promised_amount": "3500.00",
                "promise_date": "2026-09-10",
                "deadline": "2026-09-15",
                "notes": "Customer requested grace period till salary",
                "status": "ACTIVE",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        promise_id = create_res.data["id"]
        self.assertTrue(create_res.data["promise_number"].startswith("ALPHA-PTP-"))
        self.assertEqual(create_res.data["status"], "ACTIVE")

        # 3. Duplicate active/pending promise -> Must fail
        dup_res = self.client.post(
            reverse("billing-promise-list-create"),
            {
                "customer_id": str(self.customer.id),
                "service_account_id": str(self.service.id),
                "promised_amount": "2000.00",
                "promise_date": "2026-09-10",
                "deadline": "2026-09-20",
            },
            format="json",
        )
        self.assertEqual(dup_res.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Attempt fulfillment without payment -> Must fail
        premature_fulfill = self.client.post(
            reverse("billing-promise-status-transition", kwargs={"promise_id": promise_id}),
            {"status": "FULFILLED"},
            format="json",
        )
        self.assertEqual(premature_fulfill.status_code, status.HTTP_400_BAD_REQUEST)

        # 5. Record genuine payment
        record_invoice_payment(
            organization=self.organization,
            actor=self.owner,
            invoice_id=self.invoice_res.invoice.id,
            amount=Decimal("3500.00"),
            payment_method=Payment.Method.CASH,
            paid_at=None,
        )

        # 6. Now fulfillment succeeds
        fulfill_res = self.client.post(
            reverse("billing-promise-status-transition", kwargs={"promise_id": promise_id}),
            {"status": "FULFILLED", "notes": "Paid in full via cash"},
            format="json",
        )
        self.assertEqual(fulfill_res.status_code, status.HTTP_200_OK)
        self.assertEqual(fulfill_res.data["status"], "FULFILLED")

        # 7. Completed promise is protected from modification
        patch_res = self.client.patch(
            reverse("billing-promise-detail", kwargs={"promise_id": promise_id}),
            {"notes": "Changed notes after completion"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_tenant_promise_isolation(self):
        beta_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Beta Package",
            code="BP-1",
            download_speed_mbps=20,
            upload_speed_mbps=20,
            monthly_price=2000.00,
            is_active=True,
        )
        beta_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="BETA-CUST-00001",
            first_name="Beta",
            last_name="User",
            phone="03007776655",
            address_line="Sector Y",
            city="Karachi",
        )
        beta_service = ServiceAccount.objects.create(
            organization=self.other_organization,
            customer=beta_customer,
            service_number="BETA-SRV-00001",
            internet_package=beta_package,
            status=ServiceAccount.Status.ACTIVE,
        )
        beta_promise = PromiseToPay.objects.create(
            organization=self.other_organization,
            promise_number="BETA-PTP-00001",
            customer=beta_customer,
            service_account=beta_service,
            outstanding_amount=Decimal("5000.00"),
            promised_amount=Decimal("5000.00"),
            promise_date=date(2026, 9, 1),
            deadline=date(2026, 9, 10),
            status=PromiseToPay.Status.ACTIVE,
        )

        self.auth(self.owner, self.organization)
        res = self.client.get(reverse("billing-promise-detail", kwargs={"promise_id": beta_promise.id}))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class DefaulterAndRecoveryAllocationTests(APITestCase):
    def setUp(self):
        self.org1 = Organization.objects.create(
            name="Apex Fiber",
            code="APEX",
            currency="PKR",
        )
        self.org2 = Organization.objects.create(
            name="Zenith Net",
            code="ZENITH",
            currency="PKR",
        )
        self.owner1 = User.objects.create_user(
            username="owner@apex.local",
            email="owner@apex.local",
            password="StrongPassword123!",
            first_name="Apex",
            last_name="Admin",
        )
        self.membership1 = OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.owner1,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        self.operator1 = User.objects.create_user(
            username="operator1@apex.local",
            email="operator1@apex.local",
            password="StrongPassword123!",
            first_name="Ali",
            last_name="Recovery",
        )
        self.membership_op1 = OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.operator1,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.operator2 = User.objects.create_user(
            username="operator2@apex.local",
            email="operator2@apex.local",
            password="StrongPassword123!",
            first_name="Bilal",
            last_name="Collector",
        )
        self.membership_op2 = OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.operator2,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )

        self.owner2 = User.objects.create_user(
            username="owner@zenith.local",
            email="owner@zenith.local",
            password="StrongPassword123!",
            first_name="Zenith",
            last_name="Owner",
        )
        self.membership2 = OrganizationMembership.objects.create(
            organization=self.org2,
            user=self.owner2,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

        self.package = InternetPackage.objects.create(
            organization=self.org1,
            name="Apex Turbo 50M",
            code="AT-50M",
            download_speed_mbps=50,
            upload_speed_mbps=50,
            monthly_price=3500.00,
            is_active=True,
        )
        self.customer = Customer.objects.create(
            organization=self.org1,
            customer_number="APEX-CUST-0001",
            first_name="Haris",
            last_name="Rauf",
            phone="03001234567",
            address_line="Street 4, Sector G",
            city="Lahore",
            area="Gulberg",
        )
        self.service = ServiceAccount.objects.create(
            organization=self.org1,
            customer=self.customer,
            service_number="APEX-SRV-0001",
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )
        self.billing_profile = BillingProfile.objects.create(
            organization=self.org1,
            service_account=self.service,
            billing_day=1,
            due_day=10,
        )
        self.overdue_invoice = Invoice.objects.create(
            organization=self.org1,
            service_account=self.service,
            billing_profile=self.billing_profile,
            invoice_number="APEX-INV-0001",
            issue_date=date(2026, 7, 1),
            billing_period_start=date(2026, 7, 1),
            billing_period_end=date(2026, 7, 31),
            due_date=date(2026, 8, 10),
            status=Invoice.Status.UNPAID,
        )
        InvoiceLine.objects.create(
            organization=self.org1,
            invoice=self.overdue_invoice,
            description="Monthly Subscription",
            amount=Decimal("3500.00"),
        )

    def auth(self, org, user):
        login_res = self.client.post(
            reverse("tenant-login"),
            {
                "organization_code": org.code,
                "email": user.email,
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_defaulter_list_from_real_overdue_invoices(self):
        self.auth(self.org1, self.owner1)
        res = self.client.get(reverse("billing-defaulter-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        item = res.data[0]
        self.assertEqual(item["customer_id"], str(self.customer.id))
        self.assertEqual(item["customer_number"], "APEX-CUST-0001")
        self.assertEqual(Decimal(item["total_overdue"]), Decimal("3500.00"))
        self.assertEqual(item["overdue_invoices_count"], 1)
        self.assertIsNone(item["active_allocation"])

    def test_allocate_defaulter_and_duplicate_prevention(self):
        self.auth(self.org1, self.owner1)
        res = self.client.post(
            reverse("billing-allocation-list-create"),
            {
                "customer_id": str(self.customer.id),
                "service_account_id": str(self.service.id),
                "assigned_staff_id": str(self.operator1.id),
                "priority": "HIGH",
                "notes": "Follow up for July invoice",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["allocation_number"].startswith("APEX-REC-"))
        self.assertEqual(res.data["status"], "ALLOCATED")
        self.assertEqual(Decimal(res.data["outstanding_amount"]), Decimal("3500.00"))

        # Duplicate allocation attempt on same customer
        dup_res = self.client.post(
            reverse("billing-allocation-list-create"),
            {
                "customer_id": str(self.customer.id),
                "assigned_staff_id": str(self.operator2.id),
            },
            format="json",
        )
        self.assertEqual(dup_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reassign_recovery_allocation_preserves_history(self):
        self.auth(self.org1, self.owner1)
        create_res = self.client.post(
            reverse("billing-allocation-list-create"),
            {
                "customer_id": str(self.customer.id),
                "assigned_staff_id": str(self.operator1.id),
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        allocation_id = create_res.data["id"]
        first_alloc_num = create_res.data["allocation_number"]

        reassign_res = self.client.post(
            reverse("billing-allocation-reassign", kwargs={"allocation_id": allocation_id}),
            {
                "new_assigned_staff_id": str(self.operator2.id),
                "reassignment_reason": "Operator on leave, transferring territory",
                "priority": "CRITICAL",
            },
            format="json",
        )
        self.assertEqual(reassign_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(reassign_res.data["assigned_staff"]), str(self.operator2.id))
        self.assertEqual(str(reassign_res.data["reassigned_from"]), str(allocation_id))
        self.assertEqual(reassign_res.data["reassigned_from_number"], first_alloc_num)
        self.assertEqual(reassign_res.data["priority"], "CRITICAL")

        # Verify old allocation is cancelled with reason
        old_alloc = RecoveryAllocation.objects.get(id=allocation_id)
        self.assertEqual(old_alloc.status, RecoveryAllocation.Status.CANCELLED)
        self.assertEqual(old_alloc.reassignment_reason, "Operator on leave, transferring territory")

    def test_recovery_status_transition_with_payment_verification(self):
        self.auth(self.org1, self.owner1)
        create_res = self.client.post(
            reverse("billing-allocation-list-create"),
            {
                "customer_id": str(self.customer.id),
                "assigned_staff_id": str(self.operator1.id),
            },
            format="json",
        )
        allocation_id = create_res.data["id"]

        # 1. Contacted
        contact_res = self.client.post(
            reverse("billing-allocation-status-transition", kwargs={"allocation_id": allocation_id}),
            {"new_status": "CONTACTED", "notes": "Spoke with subscriber over phone"},
            format="json",
        )
        self.assertEqual(contact_res.status_code, status.HTTP_200_OK)
        self.assertEqual(contact_res.data["status"], "CONTACTED")

        # 2. Attempt complete without payment -> Fails
        fail_res = self.client.post(
            reverse("billing-allocation-status-transition", kwargs={"allocation_id": allocation_id}),
            {"new_status": "COMPLETED"},
            format="json",
        )
        self.assertEqual(fail_res.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Record real payment
        pay_res = self.client.post(
            reverse("billing-invoice-payment-record", kwargs={"invoice_id": self.overdue_invoice.id}),
            {
                "amount": "3500.00",
                "payment_method": "CASH",
                "reference": "REC-CASH-1",
            },
            format="json",
        )
        self.assertEqual(pay_res.status_code, status.HTTP_201_CREATED)

        # 4. Now transition to COMPLETED -> Succeeds
        comp_res = self.client.post(
            reverse("billing-allocation-status-transition", kwargs={"allocation_id": allocation_id}),
            {"new_status": "COMPLETED", "notes": "Recovered in full"},
            format="json",
        )
        self.assertEqual(comp_res.status_code, status.HTTP_200_OK)
        self.assertEqual(comp_res.data["status"], "COMPLETED")
        self.assertIsNotNone(comp_res.data["completed_date"])

        # 5. Terminal allocation cannot be modified
        term_res = self.client.post(
            reverse("billing-allocation-status-transition", kwargs={"allocation_id": allocation_id}),
            {"new_status": "IN_PROGRESS"},
            format="json",
        )
        self.assertEqual(term_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_tenant_recovery_isolation(self):
        self.auth(self.org1, self.owner1)
        create_res = self.client.post(
            reverse("billing-allocation-list-create"),
            {
                "customer_id": str(self.customer.id),
                "assigned_staff_id": str(self.operator1.id),
            },
            format="json",
        )
        allocation_id = create_res.data["id"]

        # Org 2 attempts to view Org 1 allocation
        self.auth(self.org2, self.owner2)
        get_res = self.client.get(reverse("billing-allocation-detail", kwargs={"allocation_id": allocation_id}))
        self.assertEqual(get_res.status_code, status.HTTP_404_NOT_FOUND)

    def test_recovery_dashboard_metrics(self):
        self.auth(self.org1, self.owner1)
        self.client.post(
            reverse("billing-allocation-list-create"),
            {
                "customer_id": str(self.customer.id),
                "assigned_staff_id": str(self.operator1.id),
            },
            format="json",
        )

        dash_res = self.client.get(reverse("billing-recovery-dashboard"))
        self.assertEqual(dash_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dash_res.data["total_assigned"], 1)
        self.assertEqual(dash_res.data["active_count"], 1)
        self.assertEqual(Decimal(dash_res.data["total_outstanding_assigned"]), Decimal("3500.00"))


class BillingFinancialIntegrityTests(APITestCase):
    def setUp(self):
        self.org1 = Organization.objects.create(
            name="Alpha Fiber",
            code="ALPHA-FIBER",
            currency="PKR",
            timezone="Asia/Karachi",
        )
        self.org2 = Organization.objects.create(
            name="Beta Telecom",
            code="BETA-TEL",
            currency="PKR",
            timezone="Asia/Karachi",
        )

        self.owner1 = User.objects.create_user(
            username="alpha_owner",
            email="owner@alpha.local",
            password="StrongPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.owner1,
            role=OrganizationMembership.Role.OWNER,
        )

        self.owner2 = User.objects.create_user(
            username="beta_owner",
            email="owner@beta.local",
            password="StrongPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.org2,
            user=self.owner2,
            role=OrganizationMembership.Role.OWNER,
        )

        self.pkg1 = InternetPackage.objects.create(
            organization=self.org1,
            name="Alpha 25M",
            code="ALP-25M",
            download_speed_mbps=25,
            upload_speed_mbps=10,
            monthly_price=Decimal("2500.00"),
        )
        self.customer1 = Customer.objects.create(
            organization=self.org1,
            customer_number="ALP-CUST-100",
            first_name="Zubair",
            last_name="Khan",
            phone="03009998877",
            address_line="Flat 401, Al-Noor Heights",
            city="Karachi",
            area="Gulshan",
        )
        self.service1 = ServiceAccount.objects.create(
            organization=self.org1,
            service_number="ALP-SVC-100",
            customer=self.customer1,
            internet_package=self.pkg1,
            status=ServiceAccount.Status.ACTIVE,
        )
        self.profile1 = BillingProfile.objects.create(
            organization=self.org1,
            service_account=self.service1,
            billing_cycle="MONTHLY",
            billing_day=1,
            due_day=10,
            is_active=True,
        )

    def auth(self, org, user, password="StrongPassword123!"):
        login_res = self.client.post(
            reverse("tenant-login"),
            {
                "email": user.email,
                "password": password,
                "organization_code": org.code,
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['access']}")

    def test_01_full_payment_clears_invoice(self):
        self.auth(self.org1, self.owner1)
        # 1. Generate invoice
        inv_res = self.client.post(
            reverse("billing-generate-invoice"),
            {
                "service_account_id": str(self.service1.id),
                "billing_year": 2026,
                "billing_month": 4,
            },
            format="json",
        )
        self.assertEqual(inv_res.status_code, status.HTTP_201_CREATED)
        inv_id = inv_res.data["id"]
        self.assertEqual(inv_res.data["status"], "UNPAID")
        self.assertEqual(Decimal(inv_res.data["total_amount"]), Decimal("2500.00"))
        self.assertEqual(Decimal(inv_res.data["outstanding_amount"]), Decimal("2500.00"))

        # 2. Record full payment
        pay_res = self.client.post(
            reverse("billing-invoice-payment-record", kwargs={"invoice_id": inv_id}),
            {
                "amount": "2500.00",
                "payment_method": "CASH",
                "reference": "RCPT-001",
            },
            format="json",
        )
        self.assertEqual(pay_res.status_code, status.HTTP_201_CREATED)

        # 3. Verify invoice is PAID
        detail_res = self.client.get(reverse("billing-invoice-detail", kwargs={"invoice_id": inv_id}))
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.data["status"], "PAID")
        self.assertEqual(Decimal(detail_res.data["paid_amount"]), Decimal("2500.00"))
        self.assertEqual(Decimal(detail_res.data["outstanding_amount"]), Decimal("0.00"))

    def test_02_partial_payment_maintains_partially_paid_status(self):
        self.auth(self.org1, self.owner1)
        inv_res = self.client.post(
            reverse("billing-generate-invoice"),
            {
                "service_account_id": str(self.service1.id),
                "billing_year": 2026,
                "billing_month": 5,
            },
            format="json",
        )
        inv_id = inv_res.data["id"]

        # Pay partial 1000 out of 2500
        pay_res = self.client.post(
            reverse("billing-invoice-payment-record", kwargs={"invoice_id": inv_id}),
            {"amount": "1000.00", "payment_method": "BANK_TRANSFER"},
            format="json",
        )
        self.assertEqual(pay_res.status_code, status.HTTP_201_CREATED)

        detail_res = self.client.get(reverse("billing-invoice-detail", kwargs={"invoice_id": inv_id}))
        self.assertEqual(detail_res.data["status"], "PARTIALLY_PAID")
        self.assertEqual(Decimal(detail_res.data["paid_amount"]), Decimal("1000.00"))
        self.assertEqual(Decimal(detail_res.data["outstanding_amount"]), Decimal("1500.00"))

    def test_03_subsequent_payment_completes_invoice(self):
        self.auth(self.org1, self.owner1)
        inv_res = self.client.post(
            reverse("billing-generate-invoice"),
            {
                "service_account_id": str(self.service1.id),
                "billing_year": 2026,
                "billing_month": 6,
            },
            format="json",
        )
        inv_id = inv_res.data["id"]

        # Payment 1
        self.client.post(
            reverse("billing-invoice-payment-record", kwargs={"invoice_id": inv_id}),
            {"amount": "1500.00", "payment_method": "CARD"},
            format="json",
        )
        # Payment 2 (Remainder 1000)
        self.client.post(
            reverse("billing-invoice-payment-record", kwargs={"invoice_id": inv_id}),
            {"amount": "1000.00", "payment_method": "CASH"},
            format="json",
        )

        detail_res = self.client.get(reverse("billing-invoice-detail", kwargs={"invoice_id": inv_id}))
        self.assertEqual(detail_res.data["status"], "PAID")
        self.assertEqual(Decimal(detail_res.data["paid_amount"]), Decimal("2500.00"))
        self.assertEqual(Decimal(detail_res.data["outstanding_amount"]), Decimal("0.00"))
        self.assertEqual(len(detail_res.data["allocations"]), 2)

    def test_04_monthly_billing_run_idempotency(self):
        self.auth(self.org1, self.owner1)
        # Run 1
        run1 = self.client.post(
            reverse("billing-monthly-run"),
            {"billing_year": 2026, "billing_month": 7},
            format="json",
        )
        self.assertEqual(run1.status_code, status.HTTP_200_OK)
        self.assertEqual(run1.data["generated_invoices"], 1)
        self.assertEqual(run1.data["skipped_existing_invoices"], 0)

        # Run 2 for same period -> Must be idempotent (0 generated, 1 skipped)
        run2 = self.client.post(
            reverse("billing-monthly-run"),
            {"billing_year": 2026, "billing_month": 7},
            format="json",
        )
        self.assertEqual(run2.status_code, status.HTTP_200_OK)
        self.assertEqual(run2.data["generated_invoices"], 0)
        self.assertEqual(run2.data["skipped_existing_invoices"], 1)

    def test_05_package_price_change_historical_immutability(self):
        self.auth(self.org1, self.owner1)
        # 1. Generate invoice with original price 2500
        inv_res = self.client.post(
            reverse("billing-generate-invoice"),
            {
                "service_account_id": str(self.service1.id),
                "billing_year": 2026,
                "billing_month": 8,
            },
            format="json",
        )
        inv_id = inv_res.data["id"]
        self.assertEqual(Decimal(inv_res.data["total_amount"]), Decimal("2500.00"))

        # 2. Package price changes to 4000
        self.pkg1.monthly_price = Decimal("4000.00")
        self.pkg1.save()

        # 3. Existing historical invoice remains exactly 2500.00
        detail_res = self.client.get(reverse("billing-invoice-detail", kwargs={"invoice_id": inv_id}))
        self.assertEqual(Decimal(detail_res.data["total_amount"]), Decimal("2500.00"))

    def test_06_overdue_status_filtering(self):
        self.auth(self.org1, self.owner1)
        # Generate custom invoice with past due date
        self.client.post(
            reverse("billing-custom-invoice-create"),
            {
                "service_account_id": str(self.service1.id),
                "billing_period_start": "2026-01-01",
                "billing_period_end": "2026-01-31",
                "issue_date": "2026-01-01",
                "due_date": "2026-01-10",
                "line_items": [{"description": "Old Fee", "amount": "1200.00"}],
            },
            format="json",
        )

        overdue_res = self.client.get(reverse("billing-invoice-list") + "?due_state=OVERDUE")
        self.assertEqual(overdue_res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(overdue_res.data) >= 1)

    def test_07_overpayment_prevention(self):
        self.auth(self.org1, self.owner1)
        inv_res = self.client.post(
            reverse("billing-generate-invoice"),
            {
                "service_account_id": str(self.service1.id),
                "billing_year": 2026,
                "billing_month": 9,
            },
            format="json",
        )
        inv_id = inv_res.data["id"]

        # Attempt to pay 3000 on a 2500 invoice -> Must be rejected
        overpay_res = self.client.post(
            reverse("billing-invoice-payment-record", kwargs={"invoice_id": inv_id}),
            {"amount": "3000.00", "payment_method": "CASH"},
            format="json",
        )
        self.assertEqual(overpay_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_08_cross_tenant_payment_isolation(self):
        self.auth(self.org1, self.owner1)
        inv_res = self.client.post(
            reverse("billing-generate-invoice"),
            {
                "service_account_id": str(self.service1.id),
                "billing_year": 2026,
                "billing_month": 10,
            },
            format="json",
        )
        inv_id = inv_res.data["id"]

        # Org 2 attempts to view and pay Org 1 invoice -> Must return 400/404
        self.auth(self.org2, self.owner2)
        get_res = self.client.get(reverse("billing-invoice-detail", kwargs={"invoice_id": inv_id}))
        self.assertEqual(get_res.status_code, status.HTTP_404_NOT_FOUND)

        pay_res = self.client.post(
            reverse("billing-invoice-payment-record", kwargs={"invoice_id": inv_id}),
            {"amount": "2500.00", "payment_method": "CASH"},
            format="json",
        )
        self.assertEqual(pay_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_09_rbac_permission_enforcement(self):
        # Unauthenticated request
        self.client.credentials()
        res = self.client.get(reverse("billing-invoice-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_10_payment_receipt_generation(self):
        self.auth(self.org1, self.owner1)
        inv_res = self.client.post(
            reverse("billing-generate-invoice"),
            {
                "service_account_id": str(self.service1.id),
                "billing_year": 2026,
                "billing_month": 11,
            },
            format="json",
        )
        inv_id = inv_res.data["id"]

        pay_res = self.client.post(
            reverse("billing-invoice-payment-record", kwargs={"invoice_id": inv_id}),
            {"amount": "2500.00", "payment_method": "MOBILE_WALLET", "reference": "JAZZCASH-9911"},
            format="json",
        )
        pay_id = pay_res.data["id"]

        rcpt_res = self.client.get(reverse("billing-payment-receipt", kwargs={"payment_id": pay_id}))
        self.assertEqual(rcpt_res.status_code, status.HTTP_200_OK)
        self.assertEqual(rcpt_res.data["payment_number"], pay_res.data["payment_number"])
        self.assertEqual(rcpt_res.data["customer"]["full_name"], "Zubair Khan")
        self.assertEqual(rcpt_res.data["payment_method"], "MOBILE_WALLET")
        self.assertEqual(Decimal(rcpt_res.data["amount"]), Decimal("2500.00"))
        self.assertEqual(len(rcpt_res.data["allocations"]), 1)

    def test_11_customer_financial_ledger_calculation(self):
        self.auth(self.org1, self.owner1)
        # Create custom invoice 5000
        self.client.post(
            reverse("billing-custom-invoice-create"),
            {
                "service_account_id": str(self.service1.id),
                "billing_period_start": "2026-02-01",
                "billing_period_end": "2026-02-28",
                "issue_date": "2026-02-01",
                "due_date": "2026-02-10",
                "line_items": [{"description": "Installation & Plan", "amount": "5000.00"}],
            },
            format="json",
        )
        # Payment of 3000
        self.client.post(
            reverse("billing-payment-record-with-allocations"),
            {
                "service_account_id": str(self.service1.id),
                "amount": "3000.00",
                "payment_method": "CASH",
            },
            format="json",
        )

        ledger_res = self.client.get(reverse("billing-financial-ledger") + f"?customer_id={self.customer1.id}")
        self.assertEqual(ledger_res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(ledger_res.data["total_debit"]), Decimal("5000.00"))
        self.assertEqual(Decimal(ledger_res.data["total_credit"]), Decimal("3000.00"))
        self.assertEqual(Decimal(ledger_res.data["closing_balance"]), Decimal("2000.00"))

    def test_12_multi_invoice_payment_allocation(self):
        self.auth(self.org1, self.owner1)
        inv1 = self.client.post(
            reverse("billing-custom-invoice-create"),
            {
                "service_account_id": str(self.service1.id),
                "billing_period_start": "2026-03-01",
                "billing_period_end": "2026-03-31",
                "issue_date": "2026-03-01",
                "due_date": "2026-03-10",
                "line_items": [{"description": "Plan Fee", "amount": "1000.00"}],
            },
            format="json",
        ).data["id"]

        inv2 = self.client.post(
            reverse("billing-custom-invoice-create"),
            {
                "service_account_id": str(self.service1.id),
                "billing_period_start": "2026-04-01",
                "billing_period_end": "2026-04-30",
                "issue_date": "2026-04-01",
                "due_date": "2026-04-10",
                "line_items": [{"description": "Plan Fee", "amount": "2000.00"}],
            },
            format="json",
        ).data["id"]

        # Pay 2500 across both (1000 to inv1, 1500 to inv2)
        pay_res = self.client.post(
            reverse("billing-payment-record-with-allocations"),
            {
                "service_account_id": str(self.service1.id),
                "amount": "2500.00",
                "payment_method": "BANK_TRANSFER",
                "allocations": [
                    {"invoice_id": inv1, "amount": "1000.00"},
                    {"invoice_id": inv2, "amount": "1500.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(pay_res.status_code, status.HTTP_201_CREATED)

        # inv1 is PAID, inv2 is PARTIALLY_PAID (500 remaining)
        d1 = self.client.get(reverse("billing-invoice-detail", kwargs={"invoice_id": inv1})).data
        d2 = self.client.get(reverse("billing-invoice-detail", kwargs={"invoice_id": inv2})).data
        self.assertEqual(d1["status"], "PAID")
        self.assertEqual(d2["status"], "PARTIALLY_PAID")
        self.assertEqual(Decimal(d2["outstanding_amount"]), Decimal("500.00"))

    def test_13_payment_reversal_lifecycle(self):
        self.auth(self.org1, self.owner1)
        inv_id = self.client.post(
            reverse("billing-custom-invoice-create"),
            {
                "service_account_id": str(self.service1.id),
                "billing_period_start": "2026-05-01",
                "billing_period_end": "2026-05-31",
                "issue_date": "2026-05-01",
                "due_date": "2026-05-10",
                "line_items": [{"description": "Service Fee", "amount": "1500.00"}],
            },
            format="json",
        ).data["id"]

        # Pay full
        pay_id = self.client.post(
            reverse("billing-invoice-payment-record", kwargs={"invoice_id": inv_id}),
            {"amount": "1500.00", "payment_method": "CASH"},
            format="json",
        ).data["id"]

        inv_before = self.client.get(reverse("billing-invoice-detail", kwargs={"invoice_id": inv_id})).data
        self.assertEqual(inv_before["status"], "PAID")

        # Reverse payment
        rev_res = self.client.post(
            reverse("billing-payment-reverse", kwargs={"payment_id": pay_id}),
            {"reversal_reason": "Bounced cheque / cashier entry mistake"},
            format="json",
        )
        self.assertEqual(rev_res.status_code, status.HTTP_200_OK)
        self.assertTrue(rev_res.data["is_reversed"])

        # Invoice balance is restored back to UNPAID
        inv_after = self.client.get(reverse("billing-invoice-detail", kwargs={"invoice_id": inv_id})).data
        self.assertEqual(inv_after["status"], "UNPAID")
        self.assertEqual(Decimal(inv_after["outstanding_amount"]), Decimal("1500.00"))

    def test_14_invoice_cancellation_lifecycle(self):
        self.auth(self.org1, self.owner1)
        inv_id = self.client.post(
            reverse("billing-custom-invoice-create"),
            {
                "service_account_id": str(self.service1.id),
                "billing_period_start": "2026-06-01",
                "billing_period_end": "2026-06-30",
                "issue_date": "2026-06-01",
                "due_date": "2026-06-10",
                "line_items": [{"description": "Wrong charge", "amount": "800.00"}],
            },
            format="json",
        ).data["id"]

        # Cancel invoice
        cancel_res = self.client.post(
            reverse("billing-invoice-cancel", kwargs={"invoice_id": inv_id}),
            {"cancellation_reason": "Billed in error by dispatcher"},
            format="json",
        )
        self.assertEqual(cancel_res.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_res.data["status"], "CANCELLED")
        self.assertEqual(cancel_res.data["cancellation_reason"], "Billed in error by dispatcher")

    def test_15_custom_invoice_with_line_items(self):
        self.auth(self.org1, self.owner1)
        res = self.client.post(
            reverse("billing-custom-invoice-create"),
            {
                "service_account_id": str(self.service1.id),
                "billing_period_start": "2026-07-01",
                "billing_period_end": "2026-07-31",
                "issue_date": "2026-07-01",
                "due_date": "2026-07-10",
                "line_items": [
                    {"description": "Internet Plan", "amount": "2500.00", "quantity": 1, "unit_price": "2500.00"},
                    {"description": "Dual-Band ONU Device", "amount": "4500.00", "quantity": 1, "unit_price": "4500.00"},
                    {"description": "Installation Service", "amount": "1500.00", "quantity": 1, "unit_price": "1500.00"},
                ],
                "notes": "New fiber setup",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(res.data["total_amount"]), Decimal("8500.00"))
        self.assertEqual(len(res.data["lines"]), 3)

