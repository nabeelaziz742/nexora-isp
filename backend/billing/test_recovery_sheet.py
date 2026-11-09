import csv
import io
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from billing.models import Invoice, InvoiceLine
from customers.import_services import import_customers
from customers.models import InternetPackage, ServiceAccount
from tenancy.models import Organization, OrganizationMembership
from tenancy.staff_services import get_or_create_staff_profile


class RecoverySheetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name="Alpha Net", code="ALPHA", city="Lahore")
        self.owner = User.objects.create_user(username="o@alpha.test", email="o@alpha.test", password="OwnerPass!2345")
        membership = OrganizationMembership.objects.create(
            organization=self.org, user=self.owner, role=OrganizationMembership.Role.OWNER, is_active=True,
        )
        get_or_create_staff_profile(membership)
        InternetPackage.objects.create(organization=self.org, name="Family 20", code="F-20",
                                       download_speed_mbps=20, upload_speed_mbps=20, monthly_price=Decimal("2800"))
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["first_name", "last_name", "phone", "address", "area", "city", "package_code", "billing_mode"])
        writer.writerow(["Ahmed", "Raza", "03001111111", "House 12, Block R", "Johar Town", "Lahore", "F-20", "MONTHLY"])
        writer.writerow(["Sana", "Malik", "03001111112", "House 4, Block J", "Model Town", "Lahore", "F-20", "MONTHLY"])
        writer.writerow(["Imran", "Shah", "03001111113", "Flat 7", "Johar Town", "Lahore", "F-20", "MONTHLY"])
        import_customers(organization=self.org, actor=self.owner,
                         uploaded_file=SimpleUploadedFile("c.csv", buffer.getvalue().encode(), content_type="text/csv"))
        today = timezone.localdate()
        for phone, amount, days in [("03001111111", "2800", 40), ("03001111112", "5600", 10), ("03001111113", "2800", 5)]:
            service = ServiceAccount.objects.get(customer__phone=phone)
            invoice = Invoice.objects.create(
                organization=self.org, service_account=service, billing_profile=service.billing_profile,
                invoice_number=f"INV-{phone[-3:]}", billing_period_start=today - timedelta(days=60),
                billing_period_end=today - timedelta(days=31), issue_date=today - timedelta(days=days + 10),
                due_date=today - timedelta(days=days), status=Invoice.Status.UNPAID,
            )
            InvoiceLine.objects.create(organization=self.org, invoice=invoice, description="Internet",
                                       quantity=1, unit_price=Decimal(amount), amount=Decimal(amount))
        self.client.force_authenticate(self.owner)
        login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "o@alpha.test", "password": "OwnerPass!2345"}, format="json")
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_sheet_groups_by_area_with_address_and_totals(self):
        response = self.client.get("/api/v1/billing/defaulters/recovery-sheet/")
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["total_customers"], 3)
        self.assertEqual(data["total_overdue"], "11200.00")
        self.assertEqual([g["area"] for g in data["groups"]], ["Johar Town", "Model Town"])
        johar = data["groups"][0]
        self.assertEqual(johar["total"], "5600.00")
        self.assertEqual(johar["rows"][0]["address"], "House 12, Block R")
        self.assertEqual(johar["rows"][0]["package_name"], "Family 20")
        self.assertIsNone(johar["rows"][0]["last_payment_date"])
        self.assertEqual(data["areas"], ["Johar Town", "Model Town"])

    def test_sheet_filters_by_area_and_aging(self):
        by_area = self.client.get("/api/v1/billing/defaulters/recovery-sheet/", {"area": "Model Town"}).data
        self.assertEqual(by_area["total_customers"], 1)
        old = self.client.get("/api/v1/billing/defaulters/recovery-sheet/", {"aging_bucket": "31-60"}).data
        self.assertEqual([r["full_name"] for g in old["groups"] for r in g["rows"]], ["Ahmed Raza"])

    def test_defaulter_search_by_name_works(self):
        response = self.client.get("/api/v1/billing/defaulters/", {"search": "Sana"})
        self.assertEqual(response.status_code, 200)
        rows = response.data if isinstance(response.data, list) else response.data["results"]
        self.assertEqual([row["full_name"] for row in rows], ["Sana Malik"])
