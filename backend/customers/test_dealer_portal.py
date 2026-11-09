import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from billing.models import Payment
from customers.import_services import import_customers
from customers.models import Country, Dealer, InternetPackage, ServiceAccount
from tenancy.models import Organization, OrganizationMembership, StaffProfile
from tenancy.staff_services import get_or_create_staff_profile

PASSWORD = "DealerPass!2345"


class DealerPortalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name="Alpha Net", code="ALPHA", city="Lahore")
        self.owner = User.objects.create_user(
            username="owner@alpha.test", email="owner@alpha.test", password="OwnerPass!2345",
        )
        owner_membership = OrganizationMembership.objects.create(
            organization=self.org, user=self.owner, role=OrganizationMembership.Role.OWNER, is_active=True,
        )
        get_or_create_staff_profile(owner_membership)
        self.staff = User.objects.create_user(
            username="staff@alpha.test", email="staff@alpha.test", password="StaffPass!2345",
        )
        staff_membership = OrganizationMembership.objects.create(
            organization=self.org, user=self.staff, role=OrganizationMembership.Role.STAFF, is_active=True,
        )
        profile = get_or_create_staff_profile(staff_membership)
        profile.role = StaffProfile.Role.OPERATOR
        profile.save()

        country = Country.objects.create(organization=self.org, name="Pakistan", code="PK")
        common = dict(organization=self.org, country=country, city="Lahore", address_line="Shop 1",
                      commission_rate_percentage=Decimal("10"), joining_date=date(2025, 1, 1))
        self.dealer = Dealer.objects.create(dealer_code="DL-1", name="Bilal", phone="03000000001", **common)
        self.other_dealer = Dealer.objects.create(dealer_code="DL-2", name="Kashif", phone="03000000002", **common)
        InternetPackage.objects.create(organization=self.org, name="Family 20", code="F-20",
                                       download_speed_mbps=20, upload_speed_mbps=20, monthly_price=Decimal("2800"))

        expiry = (timezone.localdate() + timedelta(days=2)).isoformat()
        rows = [
            ("Ahmed", "03001111111", "DL-1", "MONTHLY", "", "2800"),
            ("Sana", "03001111112", "DL-1", "PREPAID", expiry, ""),
            ("Imran", "03001111113", "DL-2", "MONTHLY", "", "2800"),
        ]
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["first_name", "phone", "address", "city", "dealer_code", "package_code",
                         "billing_mode", "expiry_date", "opening_balance"])
        for name, phone, dealer, mode, exp, balance in rows:
            writer.writerow([name, phone, "House 1", "Lahore", dealer, "F-20", mode, exp, balance])
        result = import_customers(
            organization=self.org, actor=self.owner,
            uploaded_file=SimpleUploadedFile("c.csv", buffer.getvalue().encode(), content_type="text/csv"),
        )
        self.assertEqual(result.batch.imported_count, 3)
        self.ahmed = ServiceAccount.objects.get(customer__phone="03001111111")
        self.sana = ServiceAccount.objects.get(customer__phone="03001111112")
        self.imran = ServiceAccount.objects.get(customer__phone="03001111113")

    # -- helpers -------------------------------------------------------------

    def grant(self, user=None, email="bilal@dealer.test", dealer=None):
        self.client.force_authenticate(None)
        self.client.credentials()
        login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA",
            "email": (user or self.owner).email,
            "password": "OwnerPass!2345" if (user or self.owner) == self.owner else "StaffPass!2345",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        return self.client.post(
            f"/api/v1/customers/dealers/{(dealer or self.dealer).id}/portal-access/",
            {"email": email, "password": PASSWORD}, format="json",
        )

    def dealer_login(self, email="bilal@dealer.test"):
        self.client.credentials()
        response = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": email, "password": PASSWORD,
        }, format="json")
        if response.status_code == 200:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    # -- owner side ----------------------------------------------------------

    def test_owner_creates_dealer_login_and_dealer_signs_in(self):
        response = self.grant()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["is_enabled"])
        login = self.dealer_login()
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["role"], "DEALER")

    def test_operator_cannot_create_dealer_login(self):
        response = self.grant(user=self.staff)
        self.assertEqual(response.status_code, 403)

    def test_existing_account_email_is_refused(self):
        response = self.grant(email="staff@alpha.test")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_revoked_login_cannot_sign_in(self):
        self.grant()
        self.client.delete(f"/api/v1/customers/dealers/{self.dealer.id}/portal-access/")
        self.assertEqual(self.dealer_login().status_code, 400)

    # -- isolation -----------------------------------------------------------

    def test_dealer_token_is_refused_on_staff_apis(self):
        self.grant()
        self.dealer_login()
        for path in [
            "/api/v1/customers/",
            "/api/v1/customers/dealers/",
            "/api/v1/billing/invoices/",
            "/api/v1/customers/suspensions/eligibility/",
            "/api/v1/reports/collections/register/",
            "/api/v1/tenant/staff/",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403, path)

    def test_dealer_sees_only_own_customers(self):
        self.grant()
        self.dealer_login()
        response = self.client.get("/api/v1/dealer-portal/customers/")
        self.assertEqual(response.status_code, 200)
        names = sorted(row["customer_name"] for row in response.data["results"])
        self.assertEqual(names, ["Ahmed", "Sana"])

    def test_dealer_cannot_collect_for_another_dealers_customer(self):
        self.grant()
        self.dealer_login()
        response = self.client.post(
            f"/api/v1/dealer-portal/services/{self.imran.id}/payments/",
            {"amount": "2800", "payment_method": "CASH"}, format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Payment.objects.filter(service_account=self.imran).exists())

    def test_staff_token_cannot_use_dealer_portal(self):
        self.grant()
        self.assertEqual(self.client.get("/api/v1/dealer-portal/summary/").status_code, 403)

    def test_inactive_dealer_is_refused(self):
        self.grant()
        self.dealer.status = Dealer.Status.SUSPENDED
        self.dealer.save()
        self.dealer_login()
        self.assertEqual(self.client.get("/api/v1/dealer-portal/summary/").status_code, 403)

    # -- dealer work ---------------------------------------------------------

    def test_dealer_collects_payment_and_it_counts_for_commission(self):
        self.grant()
        self.dealer_login()
        response = self.client.post(
            f"/api/v1/dealer-portal/services/{self.ahmed.id}/payments/",
            {"amount": "2800", "payment_method": "CASH", "reference": "R-1"}, format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["service"]["outstanding"], "0.00")
        payment = Payment.objects.get(id=response.data["receipt"]["payment_id"])
        self.assertEqual(payment.received_by.email, "bilal@dealer.test")

        summary = self.client.get("/api/v1/dealer-portal/summary/").data
        self.assertEqual(summary["collected_by_me_this_month"], "2800.00")
        self.assertEqual(summary["commission_this_month"], "280.00")
        collections = self.client.get("/api/v1/dealer-portal/collections/").data
        self.assertEqual(collections["total_collected"], "2800.00")
        self.assertTrue(collections["results"][0]["collected_by_me"])

    def test_dealer_recharges_prepaid_only(self):
        self.grant()
        self.dealer_login()
        response = self.client.post(
            f"/api/v1/dealer-portal/services/{self.sana.id}/recharge/",
            {"months": 1, "payment_method": "MOBILE_WALLET"}, format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.sana.refresh_from_db()
        self.assertGreater(self.sana.expiry_date, timezone.localdate() + timedelta(days=20))

        response = self.client.post(
            f"/api/v1/dealer-portal/services/{self.ahmed.id}/recharge/",
            {"months": 1, "payment_method": "CASH"}, format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_due_and_expiring_filters(self):
        self.grant()
        self.dealer_login()
        due = self.client.get("/api/v1/dealer-portal/customers/", {"show": "due"}).data
        self.assertEqual([row["customer_name"] for row in due["results"]], ["Ahmed"])
        expiring = self.client.get("/api/v1/dealer-portal/customers/", {"show": "expiring"}).data
        self.assertEqual([row["customer_name"] for row in expiring["results"]], ["Sana"])


    # -- dealer adds a customer ----------------------------------------------

    def test_dealer_request_becomes_dealer_inquiry(self):
        from customers.models import Inquiry

        self.grant()
        self.dealer_login()
        listing = self.client.get("/api/v1/dealer-portal/requests/").data
        package_id = listing["packages"][0]["id"]
        response = self.client.post("/api/v1/dealer-portal/requests/", {
            "full_name": "Naveed Akhtar", "phone": "03009990001", "address_line": "House 9",
            "city": "Lahore", "area": "Johar Town", "preferred_package": package_id,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        inquiry = Inquiry.objects.get(id=response.data["id"])
        self.assertEqual(inquiry.dealer, self.dealer)
        self.assertEqual(inquiry.source, Inquiry.Source.DEALER)
        self.assertEqual(response.data["status_label"], "Pending with office")
        rows = self.client.get("/api/v1/dealer-portal/requests/").data["results"]
        self.assertEqual([row["full_name"] for row in rows], ["Naveed Akhtar"])

    def test_dealer_request_refuses_existing_phone(self):
        self.grant()
        self.dealer_login()
        response = self.client.post("/api/v1/dealer-portal/requests/", {
            "full_name": "Dup", "phone": "03001111113", "address_line": "x", "city": "Lahore",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.data)

    def test_dealer_can_change_own_password(self):
        self.grant()
        self.dealer_login()
        response = self.client.post("/api/v1/auth/change-password/", {
            "current_password": PASSWORD, "new_password": "Dealer!NewPass77"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/onboarding/subscription/").status_code, 403)
