from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
)
from customers.models import (
    BillingProfile,
    Customer,
    InternetPackage,
    ServiceAccount,
)
from tenancy.models import (
    Organization,
    OrganizationMembership,
)


class RevenueIntelligenceOperationalAPITests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Revenue ISP",
            code="REVENUE-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Revenue ISP",
            code="OTHER-REVENUE",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        User = get_user_model()

        self.owner = User.objects.create_user(
            username="revenue-owner",
            email="revenue-owner@nexora.test",
            password="StrongPass123!",
            first_name="Revenue",
            last_name="Owner",
        )

        self.other_owner = User.objects.create_user(
            username="other-revenue-owner",
            email="other-revenue-owner@nexora.test",
            password="StrongPass123!",
            first_name="Other",
            last_name="Owner",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )

        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_owner,
            role=OrganizationMembership.Role.OWNER,
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="REV-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03008880001",
            address_line="Revenue Street",
            city="Lahore",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Revenue Fiber 50",
            code="REV-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price=Decimal("5000.00"),
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="REV-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.billing_profile = BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service,
            billing_day=1,
            due_day=10,
        )

        self.invoice = Invoice.objects.create(
            organization=self.organization,
            invoice_number="REV-INV-001",
            service_account=self.service,
            billing_profile=self.billing_profile,
            billing_period_start=date(2026, 7, 1),
            billing_period_end=date(2026, 7, 31),
            issue_date=date(2026, 7, 1),
            due_date=date(2026, 7, 10),
            status=Invoice.Status.PARTIALLY_PAID,
        )

        InvoiceLine.objects.create(
            organization=self.organization,
            invoice=self.invoice,
            description="Monthly Internet Service",
            amount=Decimal("5000.00"),
        )

        self.cash_payment = Payment.objects.create(
            organization=self.organization,
            payment_number="REV-PAY-001",
            service_account=self.service,
            amount=Decimal("3000.00"),
            payment_method=Payment.Method.CASH,
            received_by=self.owner,
            paid_at=timezone.make_aware(
                datetime(2026, 7, 5, 10, 0, 0)
            ),
        )

        PaymentAllocation.objects.create(
            organization=self.organization,
            payment=self.cash_payment,
            invoice=self.invoice,
            amount=Decimal("2000.00"),
        )

        self.wallet_payment = Payment.objects.create(
            organization=self.organization,
            payment_number="REV-PAY-002",
            service_account=self.service,
            amount=Decimal("1000.00"),
            payment_method=Payment.Method.MOBILE_WALLET,
            received_by=self.owner,
            paid_at=timezone.make_aware(
                datetime(2026, 7, 6, 11, 0, 0)
            ),
        )

        other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-REV-CUST",
            first_name="Other",
            last_name="Customer",
            phone="03008880002",
            address_line="Other Revenue Street",
            city="Karachi",
        )

        other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Other Revenue Fiber",
            code="OTHER-REV-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price=Decimal("9000.00"),
        )

        other_service = ServiceAccount.objects.create(
            organization=self.other_organization,
            service_number="OTHER-REV-SRV",
            customer=other_customer,
            internet_package=other_package,
            status=ServiceAccount.Status.ACTIVE,
        )

        other_billing_profile = BillingProfile.objects.create(
            organization=self.other_organization,
            service_account=other_service,
            billing_day=1,
            due_day=10,
        )

        other_invoice = Invoice.objects.create(
            organization=self.other_organization,
            invoice_number="OTHER-REV-INV",
            service_account=other_service,
            billing_profile=other_billing_profile,
            billing_period_start=date(2026, 7, 1),
            billing_period_end=date(2026, 7, 31),
            issue_date=date(2026, 7, 1),
            due_date=date(2026, 7, 10),
            status=Invoice.Status.UNPAID,
        )

        InvoiceLine.objects.create(
            organization=self.other_organization,
            invoice=other_invoice,
            description="Other Tenant Internet Service",
            amount=Decimal("9000.00"),
        )

        self.client = APIClient()

    def authenticate(
        self,
        *,
        user=None,
        organization=None,
    ):
        user = user or self.owner
        organization = organization or self.organization

        access_token = AccessToken.for_user(user)
        access_token["organization_id"] = str(
            organization.id
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {str(access_token)}"
            )
        )

    def test_revenue_overview_api_uses_real_ledger_totals(self):
        self.authenticate()

        response = self.client.get(
            "/api/v1/revenue-intelligence/overview/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["invoiced_amount"],
            "5000.00",
        )
        self.assertEqual(
            response.data["collected_amount"],
            "2000.00",
        )
        self.assertEqual(
            response.data["outstanding_receivables"],
            "3000.00",
        )
        self.assertEqual(
            response.data["recorded_payments"],
            "4000.00",
        )
        self.assertEqual(
            response.data["allocated_payments"],
            "2000.00",
        )
        self.assertEqual(
            response.data["unallocated_payments"],
            "2000.00",
        )

    def test_revenue_overview_is_tenant_scoped(self):
        self.authenticate(
            user=self.other_owner,
            organization=self.other_organization,
        )

        response = self.client.get(
            "/api/v1/revenue-intelligence/overview/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["invoiced_amount"],
            "9000.00",
        )
        self.assertEqual(
            response.data["collected_amount"],
            "0.00",
        )
        self.assertEqual(
            response.data["recorded_payments"],
            "0.00",
        )

    def test_collections_by_period_api(self):
        self.authenticate()

        response = self.client.get(
            (
                "/api/v1/revenue-intelligence/"
                "collections-by-period/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)

        period = response.data[0]

        self.assertEqual(
            period["payment_intake_amount"],
            "4000.00",
        )
        self.assertEqual(period["payment_count"], 2)
        self.assertEqual(
            period["allocated_collection_amount"],
            "2000.00",
        )
        self.assertEqual(period["allocation_count"], 1)

    def test_payment_method_mix_api(self):
        self.authenticate()

        response = self.client.get(
            (
                "/api/v1/revenue-intelligence/"
                "payment-method-mix/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        payment_mix = {
            item["payment_method"]: item
            for item in response.data
        }

        self.assertEqual(
            payment_mix[Payment.Method.CASH]["amount"],
            "3000.00",
        )
        self.assertEqual(
            payment_mix[Payment.Method.CASH]["payment_count"],
            1,
        )

        self.assertEqual(
            payment_mix[
                Payment.Method.MOBILE_WALLET
            ]["amount"],
            "1000.00",
        )

    def test_outstanding_receivables_api(self):
        self.authenticate()

        response = self.client.get(
            (
                "/api/v1/revenue-intelligence/"
                "outstanding-receivables/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)

        receivable = response.data[0]

        self.assertEqual(
            receivable["invoice_number"],
            "REV-INV-001",
        )
        self.assertEqual(
            receivable["customer_number"],
            "REV-CUST-001",
        )
        self.assertEqual(
            receivable["service_number"],
            "REV-SRV-001",
        )
        self.assertEqual(
            receivable["total_amount"],
            "5000.00",
        )
        self.assertEqual(
            receivable["paid_amount"],
            "2000.00",
        )
        self.assertEqual(
            receivable["outstanding_amount"],
            "3000.00",
        )

    def test_outstanding_receivables_are_tenant_scoped(self):
        self.authenticate(
            user=self.other_owner,
            organization=self.other_organization,
        )

        response = self.client.get(
            (
                "/api/v1/revenue-intelligence/"
                "outstanding-receivables/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        invoice_numbers = [
            item["invoice_number"]
            for item in response.data
        ]

        self.assertIn(
            "OTHER-REV-INV",
            invoice_numbers,
        )
        self.assertNotIn(
            "REV-INV-001",
            invoice_numbers,
        )

    def test_unauthenticated_revenue_intelligence_is_blocked(self):
        endpoints = [
            "/api/v1/revenue-intelligence/overview/",
            (
                "/api/v1/revenue-intelligence/"
                "collections-by-period/"
            ),
            (
                "/api/v1/revenue-intelligence/"
                "payment-method-mix/"
            ),
            (
                "/api/v1/revenue-intelligence/"
                "outstanding-receivables/"
            ),
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)

            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
            )