from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
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


class ReportsOperationalAPITests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Reports ISP",
            code="REPORTS-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Reports ISP",
            code="OTHER-REPORTS",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        User = get_user_model()

        self.owner = User.objects.create_user(
            username="reports-owner",
            email="reports-owner@nexora.test",
            password="StrongPass123!",
            first_name="Reports",
            last_name="Owner",
        )

        self.other_owner = User.objects.create_user(
            username="other-reports-owner",
            email="other-reports-owner@nexora.test",
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
            customer_number="RPT-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03009990001",
            address_line="Reports Street",
            city="Lahore",
        )

        self.customer_without_service = Customer.objects.create(
            organization=self.organization,
            customer_number="RPT-CUST-002",
            first_name="No",
            last_name="Service",
            phone="03009990002",
            address_line="Reports Street",
            city="Lahore",
            is_active=False,
        )

        self.package_50 = InternetPackage.objects.create(
            organization=self.organization,
            name="Reports Fiber 50",
            code="RPT-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price=Decimal("5000.00"),
        )

        self.package_100 = InternetPackage.objects.create(
            organization=self.organization,
            name="Reports Fiber 100",
            code="RPT-100",
            download_speed_mbps=100,
            upload_speed_mbps=50,
            monthly_price=Decimal("8000.00"),
        )

        self.active_service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="RPT-SRV-001",
            customer=self.customer,
            internet_package=self.package_50,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.grace_service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="RPT-SRV-002",
            customer=self.customer,
            internet_package=self.package_100,
            status=ServiceAccount.Status.GRACE_PERIOD,
        )

        self.billing_profile = BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.active_service,
            billing_day=1,
            due_day=10,
        )

        self.invoice = Invoice.objects.create(
            organization=self.organization,
            invoice_number="RPT-INV-001",
            service_account=self.active_service,
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

        self.payment = Payment.objects.create(
            organization=self.organization,
            payment_number="RPT-PAY-001",
            service_account=self.active_service,
            amount=Decimal("2000.00"),
            payment_method=Payment.Method.CASH,
            received_by=self.owner,
            paid_at="2026-07-05T10:00:00Z",
        )

        PaymentAllocation.objects.create(
            organization=self.organization,
            payment=self.payment,
            invoice=self.invoice,
            amount=Decimal("2000.00"),
        )

        other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-RPT-CUST",
            first_name="Other",
            last_name="Customer",
            phone="03009990003",
            address_line="Other Reports Street",
            city="Karachi",
        )

        other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Other Reports Fiber",
            code="OTHER-RPT-200",
            download_speed_mbps=200,
            upload_speed_mbps=100,
            monthly_price=Decimal("15000.00"),
        )

        ServiceAccount.objects.create(
            organization=self.other_organization,
            service_number="OTHER-RPT-SRV",
            customer=other_customer,
            internet_package=other_package,
            status=ServiceAccount.Status.ACTIVE,
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

    def test_subscriber_overview_api(self):
        self.authenticate()

        response = self.client.get(
            "/api/v1/reports/subscriber-overview/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["total_customers"], 2)
        self.assertEqual(response.data["active_customers"], 1)
        self.assertEqual(response.data["inactive_customers"], 1)

        self.assertEqual(response.data["total_services"], 2)
        self.assertEqual(response.data["active_services"], 1)
        self.assertEqual(
            response.data["non_active_services"],
            1,
        )

        self.assertEqual(
            response.data["customers_with_services"],
            1,
        )
        self.assertEqual(
            response.data["customers_without_services"],
            1,
        )

        self.assertEqual(response.data["total_packages"], 2)
        self.assertEqual(response.data["active_packages"], 2)

    def test_service_status_distribution_api(self):
        self.authenticate()

        response = self.client.get(
            (
                "/api/v1/reports/"
                "service-status-distribution/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        distribution = {
            item["status"]: item["service_count"]
            for item in response.data
        }

        self.assertEqual(
            distribution[ServiceAccount.Status.ACTIVE],
            1,
        )

        self.assertEqual(
            distribution[
                ServiceAccount.Status.GRACE_PERIOD
            ],
            1,
        )

        self.assertEqual(
            distribution[
                ServiceAccount.Status.SUSPENSION_PENDING
            ],
            0,
        )

    def test_package_contribution_api(self):
        self.authenticate()

        response = self.client.get(
            "/api/v1/reports/package-contribution/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        packages = {
            item["package_code"]: item
            for item in response.data
        }

        self.assertEqual(
            packages["RPT-50"]["service_count"],
            1,
        )
        self.assertEqual(
            packages["RPT-50"]["active_service_count"],
            1,
        )

        self.assertEqual(
            packages["RPT-100"]["service_count"],
            1,
        )
        self.assertEqual(
            packages["RPT-100"]["active_service_count"],
            0,
        )

    def test_package_revenue_context_uses_real_ledger(self):
        self.authenticate()

        response = self.client.get(
            "/api/v1/reports/package-revenue-context/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        packages = {
            item["package_code"]: item
            for item in response.data
        }

        package_50 = packages["RPT-50"]

        self.assertEqual(
            package_50["invoiced_amount"],
            "5000.00",
        )
        self.assertEqual(
            package_50["collected_amount"],
            "2000.00",
        )
        self.assertEqual(
            package_50["outstanding_amount"],
            "3000.00",
        )

        package_100 = packages["RPT-100"]

        self.assertEqual(
            package_100["invoiced_amount"],
            "0.00",
        )
        self.assertEqual(
            package_100["collected_amount"],
            "0.00",
        )

    def test_reports_are_tenant_scoped(self):
        self.authenticate(
            user=self.other_owner,
            organization=self.other_organization,
        )

        overview_response = self.client.get(
            "/api/v1/reports/subscriber-overview/"
        )

        self.assertEqual(
            overview_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            overview_response.data["total_customers"],
            1,
        )

        self.assertEqual(
            overview_response.data["total_services"],
            1,
        )

        package_response = self.client.get(
            "/api/v1/reports/package-contribution/"
        )

        package_codes = [
            item["package_code"]
            for item in package_response.data
        ]

        self.assertIn(
            "OTHER-RPT-200",
            package_codes,
        )

        self.assertNotIn(
            "RPT-50",
            package_codes,
        )

        self.assertNotIn(
            "RPT-100",
            package_codes,
        )

    def test_package_revenue_context_is_tenant_scoped(self):
        self.authenticate(
            user=self.other_owner,
            organization=self.other_organization,
        )

        response = self.client.get(
            "/api/v1/reports/package-revenue-context/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        package_codes = [
            item["package_code"]
            for item in response.data
        ]

        self.assertEqual(
            package_codes,
            ["OTHER-RPT-200"],
        )

        self.assertEqual(
            response.data[0]["invoiced_amount"],
            "0.00",
        )

    def test_unauthenticated_reports_are_blocked(self):
        endpoints = [
            "/api/v1/reports/subscriber-overview/",
            (
                "/api/v1/reports/"
                "service-status-distribution/"
            ),
            "/api/v1/reports/package-contribution/",
            "/api/v1/reports/package-revenue-context/",
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)

            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
            )