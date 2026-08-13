from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from billing.models import Payment
from billing.revenue_intelligence import (
    build_revenue_intelligence,
)
from billing.services import (
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
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class RevenueIntelligenceTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Revenue ISP",
            code="REV-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Revenue ISP",
                code="OTHER-REV",
                city="Karachi",
                timezone="Asia/Karachi",
                currency="PKR",
            )
        )

        self.owner = User.objects.create_user(
            username="revenue-owner",
            email="revenue-owner@nexora.local",
            password="StrongTestPassword123!",
        )

        self.technician = User.objects.create_user(
            username="revenue-technician",
            email=(
                "revenue-technician@nexora.local"
            ),
            password="StrongTestPassword123!",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.technician,
            role=(
                OrganizationMembership.Role.TECHNICIAN
            ),
        )

        self.basic_package = (
            InternetPackage.objects.create(
                organization=self.organization,
                name="Fiber 20",
                code="REV-20",
                download_speed_mbps=20,
                upload_speed_mbps=10,
                monthly_price="3000.00",
            )
        )

        self.next_package = (
            InternetPackage.objects.create(
                organization=self.organization,
                name="Fiber 50",
                code="REV-50",
                download_speed_mbps=50,
                upload_speed_mbps=25,
                monthly_price="5000.00",
            )
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="REV-CUST-001",
            first_name="Revenue",
            last_name="Customer",
            phone="03001112222",
            address_line="Revenue Street",
            city="Lahore",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="REV-SRV-001",
            customer=self.customer,
            internet_package=self.basic_package,
            status=ServiceAccount.Status.ACTIVE,
        )

        BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service,
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

    def authenticate(
        self,
        *,
        user,
    ):
        response = self.client.post(
            reverse("tenant-login"),
            {
                "email": user.email,
                "password": (
                    "StrongTestPassword123!"
                ),
                "organization_code": (
                    self.organization.code
                ),
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

    def test_service_returns_real_monthly_billed(self):
        result = build_revenue_intelligence(
            organization=self.organization,
            as_of=date(2026, 7, 9),
        )

        self.assertEqual(
            result["metrics"]["monthly_billed"],
            Decimal("3000.00"),
        )

        self.assertEqual(
            result["metrics"][
                "outstanding_exposure"
            ],
            Decimal("3000.00"),
        )

    def test_service_returns_real_collections(self):
        record_invoice_payment(
            organization=self.organization,
            actor=self.owner,
            invoice_id=self.invoice.id,
            amount="1000.00",
            payment_method=Payment.Method.CASH,
            paid_at="2026-07-09T10:00:00+05:00",
        )

        result = build_revenue_intelligence(
            organization=self.organization,
            as_of=date(2026, 7, 9),
        )

        self.assertEqual(
            result["metrics"]["collected_revenue"],
            Decimal("1000.00"),
        )

        self.assertEqual(
            result["metrics"][
                "outstanding_exposure"
            ],
            Decimal("2000.00"),
        )

    def test_upgrade_potential_uses_package_ladder(self):
        result = build_revenue_intelligence(
            organization=self.organization,
            as_of=date(2026, 7, 9),
        )

        self.assertEqual(
            result["metrics"]["upgrade_potential"],
            Decimal("2000.00"),
        )

        self.assertEqual(
            result["metrics"][
                "upgrade_candidate_count"
            ],
            1,
        )

    def test_suspension_risk_uses_service_state(self):
        self.service.status = (
            ServiceAccount.Status.SUSPENSION_PENDING
        )
        self.service.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        result = build_revenue_intelligence(
            organization=self.organization,
            as_of=date(2026, 7, 9),
        )

        self.assertEqual(
            result["metrics"][
                "suspension_risk_revenue"
            ],
            Decimal("3000.00"),
        )

        self.assertEqual(
            result["metrics"][
                "suspension_risk_service_count"
            ],
            1,
        )

    def test_empty_tenant_returns_zero_state(self):
        result = build_revenue_intelligence(
            organization=self.other_organization,
            as_of=date(2026, 7, 9),
        )

        self.assertEqual(
            result["metrics"]["monthly_billed"],
            Decimal("0.00"),
        )

        self.assertEqual(
            result["metrics"]["revenue_health"],
            0,
        )

        self.assertEqual(
            result["risk_signals"],
            [],
        )

        self.assertEqual(
            result["opportunities"],
            [],
        )

    def test_owner_can_access_revenue_intelligence(self):
        self.authenticate(user=self.owner)

        response = self.client.get(
            reverse(
                "billing-revenue-intelligence"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "metrics",
            response.data,
        )

        self.assertIn(
            "performance",
            response.data,
        )

    def test_technician_cannot_access_revenue_intelligence(
        self,
    ):
        self.authenticate(user=self.technician)

        response = self.client.get(
            reverse(
                "billing-revenue-intelligence"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )