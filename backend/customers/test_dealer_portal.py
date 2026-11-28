import csv
import io
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

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


def _test_whatsapp_provider(organization):
    from communications.models import CommunicationProvider

    return CommunicationProvider.objects.get_or_create(
        organization=organization,
        provider_type=CommunicationProvider.ProviderType.WHATSAPP,
        name="Test WhatsApp",
        defaults={"is_connected": True, "phone_number_id": "1", "access_token": "test"},
    )[0]


@contextmanager
def whatsapp_ok(password=PASSWORD):
    """Pretend the ISP's WhatsApp is connected and accepts every message."""
    sent = []
    with (
        patch("customers.dealer_login_whatsapp.whatsapp_provider", side_effect=_test_whatsapp_provider),
        patch("customers.dealer_login_whatsapp.generate_password", return_value=password),
        patch(
            "customers.dealer_login_whatsapp.send_whatsapp",
            side_effect=lambda **kwargs: sent.append(kwargs) or {"success": True},
        ),
    ):
        yield sent


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
        # The password is made by the system and sent on WhatsApp; in tests it is
        # fixed and the message is accepted without leaving the machine.
        with whatsapp_ok():
            return self.client.post(
                f"/api/v1/customers/dealers/{(dealer or self.dealer).id}/portal-access/",
                {"email": email}, format="json",
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

    # -- Phase 2: Dealer Areas & Packages ------------------------------------

    def test_dealer_areas_crud_isolation_and_isp_areas_unchanged(self):
        from customers.models import Area, DealerArea

        self.grant()
        self.grant(email="kashif@dealer.test", dealer=self.other_dealer)

        # ISP has its own area; it must stay separate from dealer areas.
        Area.objects.create(organization=self.org, name="ISP Official Zone")

        self.dealer_login()
        created = self.client.post(
            "/api/v1/dealer-portal/areas/",
            {"name": "Johar Block A", "city": "Lahore", "notes": "Main road"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        area_id = created.data["id"]

        # Duplicate name (case-insensitive) for same dealer is refused.
        dup = self.client.post("/api/v1/dealer-portal/areas/", {"name": "johar block a"}, format="json")
        self.assertEqual(dup.status_code, 400)

        # Dealer sees only their own dealer areas, never ISP Area.
        listed = self.client.get("/api/v1/dealer-portal/areas/").data["results"]
        self.assertEqual([a["name"] for a in listed], ["Johar Block A"])

        # Active dealer areas appear in customer request dropdown options.
        req_opts = self.client.get("/api/v1/dealer-portal/requests/").data
        self.assertEqual([a["name"] for a in req_opts["areas"]], ["Johar Block A"])

        # Edit and deactivate.
        edited = self.client.patch(
            f"/api/v1/dealer-portal/areas/{area_id}/",
            {"name": "Johar Block A-1", "city": "Lahore"},
            format="json",
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.data["name"], "Johar Block A-1")

        toggled = self.client.post(f"/api/v1/dealer-portal/areas/{area_id}/status/", {}, format="json")
        self.assertEqual(toggled.status_code, 200)
        self.assertFalse(toggled.data["is_active"])

        # Inactive areas are excluded from active dropdown options.
        self.assertEqual(self.client.get("/api/v1/dealer-portal/requests/").data["areas"], [])

        # Other dealer cannot see or touch this dealer's area, and can reuse same name.
        self.dealer_login("kashif@dealer.test")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/areas/").data["results"], [])
        self.assertEqual(
            self.client.patch(f"/api/v1/dealer-portal/areas/{area_id}/", {"name": "Hack"}, format="json").status_code,
            404,
        )
        other_create = self.client.post("/api/v1/dealer-portal/areas/", {"name": "Johar Block A-1"}, format="json")
        self.assertEqual(other_create.status_code, 201)

        # Owner sees dealer areas read-only on Dealer 360, while ISP Areas API never shows DealerArea.
        self.client.credentials()
        owner_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": self.owner.email, "password": "OwnerPass!2345",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_login.data['access']}")

        isp_areas = self.client.get("/api/v1/customers/areas/").data
        self.assertEqual([a["name"] for a in isp_areas], ["ISP Official Zone"])

        d360 = self.client.get(f"/api/v1/customers/dealers/{self.dealer.id}/360/").data
        self.assertEqual([a["name"] for a in d360["areas"]], ["Johar Block A-1"])
        self.assertEqual(DealerArea.objects.count(), 2)

    def test_dealer_areas_and_packages_rights_enforced(self):
        InternetPackage.objects.create(
            organization=self.org, name="Old Inactive", code="OLD-1",
            download_speed_mbps=5, upload_speed_mbps=5, monthly_price=Decimal("1000"), is_active=False,
        )
        self.grant()
        self.dealer_login()

        # Create area as dealer and check packages as dealer.
        area = self.client.post("/api/v1/dealer-portal/areas/", {"name": "Model Town"}, format="json").data
        pkgs = self.client.get("/api/v1/dealer-portal/packages/")
        self.assertEqual(pkgs.status_code, 200)
        self.assertEqual([p["name"] for p in pkgs.data["results"]], ["Family 20"])
        # Packages endpoint is read-only.
        self.assertEqual(self.client.post("/api/v1/dealer-portal/packages/", {}, format="json").status_code, 405)

        # Employee with view-only area right and no packages right.
        emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "Viewer", "email": "viewer@dealer.test", "password": "ViewerPass!123",
            "rights": {"can_view_areas": True, "can_manage_areas": False, "can_view_packages": False},
        }, format="json").data

        self.client.credentials()
        emp_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "viewer@dealer.test", "password": "ViewerPass!123",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")

        self.assertEqual(self.client.get("/api/v1/dealer-portal/areas/").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/dealer-portal/areas/", {"name": "X"}, format="json").status_code, 403)
        self.assertEqual(
            self.client.patch(f"/api/v1/dealer-portal/areas/{area['id']}/", {"name": "Y"}, format="json").status_code,
            403,
        )
        self.assertEqual(self.client.post(f"/api/v1/dealer-portal/areas/{area['id']}/status/", {}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/dealer-portal/packages/").status_code, 403)

        # Grant can_manage_areas and can_view_packages, drop can_view_areas.
        self.dealer_login()
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{emp['id']}/",
            {"rights": {"can_view_areas": False, "can_manage_areas": True, "can_view_packages": True}},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/areas/").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/dealer-portal/areas/", {"name": "Wapda Town"}, format="json").status_code, 201)
        self.assertEqual(self.client.get("/api/v1/dealer-portal/packages/").status_code, 200)

        # Without either area right -> 403 on GET /areas/.
        self.dealer_login()
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{emp['id']}/",
            {"rights": {"can_view_areas": False, "can_manage_areas": False}},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/areas/").status_code, 403)

    def test_phase3_assign_and_employee_customer_scoping(self):
        from customers.models import Customer, DealerEmployee

        self.grant()
        self.dealer_login()

        ahmed = Customer.objects.get(organization=self.org, first_name="Ahmed")
        sana = Customer.objects.get(organization=self.org, first_name="Sana")
        imran = Customer.objects.get(organization=self.org, first_name="Imran")
        ahmed_svc = ServiceAccount.objects.get(customer=ahmed)
        sana_svc = ServiceAccount.objects.get(customer=sana)

        # Create two employees: scoped (can_view_all_customers=False) and full-view.
        scoped = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "Scoped", "email": "scoped@dealer.test", "password": "ScopedPass!123",
            "rights": {
                "can_view_customers": True,
                "can_view_all_customers": False,
                "can_edit_customers": True,
                "can_deactivate_customers": True,
                "can_view_ledger": True,
                "can_export_customers": True,
                "can_collect_payments": True,
                "can_recharge": True,
            },
        }, format="json").data

        # Scoped employee cannot assign customers without can_manage_employees.
        self.client.credentials()
        scoped_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "scoped@dealer.test", "password": "ScopedPass!123",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {scoped_login.data['access']}")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/customers/assign-options/").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/v1/dealer-portal/customers/assign/",
                {"customer_ids": [str(ahmed.id)], "employee_id": scoped["id"]},
                format="json",
            ).status_code,
            403,
        )
        # Before assignment, scoped employee sees zero customers.
        self.assertEqual(self.client.get("/api/v1/dealer-portal/customers/").data["results"], [])

        # Dealer assigns Ahmed to scoped employee; refuses foreign customer Imran (404).
        self.dealer_login()
        self.assertEqual(
            self.client.post(
                "/api/v1/dealer-portal/customers/assign/",
                {"customer_ids": [str(imran.id)], "employee_id": scoped["id"]},
                format="json",
            ).status_code,
            404,
        )
        assign_res = self.client.post(
            "/api/v1/dealer-portal/customers/assign/",
            {"customer_ids": [str(ahmed.id)], "employee_id": scoped["id"]},
            format="json",
        )
        self.assertEqual(assign_res.status_code, 200)
        self.assertEqual(assign_res.data["assigned_count"], 1)

        # Log back in as scoped employee: sees only Ahmed, blocked from Sana everywhere.
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {scoped_login.data['access']}")
        cust_list = self.client.get("/api/v1/dealer-portal/customers/").data["results"]
        self.assertEqual([r["customer_name"] for r in cust_list], ["Ahmed"])
        summary = self.client.get("/api/v1/dealer-portal/summary/").data
        self.assertEqual(summary["total_customers"], 1)

        # Unassigned same-dealer customer Sana -> 404 on edit, deactivate, ledger, collect, recharge.
        self.assertEqual(
            self.client.patch(f"/api/v1/dealer-portal/customers/{sana.id}/", {"phone": "03009998887"}, format="json").status_code,
            404,
        )
        self.assertEqual(
            self.client.post(f"/api/v1/dealer-portal/customers/{sana.id}/deactivate/", {"reason": "Left"}, format="json").status_code,
            404,
        )
        self.assertEqual(self.client.get(f"/api/v1/dealer-portal/customers/{sana.id}/ledger/").status_code, 404)
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/services/{sana_svc.id}/payments/",
                {"amount": "100", "payment_method": "CASH"},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/services/{sana_svc.id}/recharge/",
                {"months": 1, "payment_method": "CASH"},
                format="json",
            ).status_code,
            404,
        )

        # Assigned customer Ahmed succeeds on ledger & payment.
        self.assertEqual(self.client.get(f"/api/v1/dealer-portal/customers/{ahmed.id}/ledger/").status_code, 200)
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/services/{ahmed_svc.id}/payments/",
                {"amount": "500", "payment_method": "CASH"},
                format="json",
            ).status_code,
            201,
        )

        # Grant can_view_all_customers=True -> sees both Ahmed and Sana (never Imran).
        self.dealer_login()
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{scoped['id']}/",
            {"rights": {"can_view_all_customers": True}},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {scoped_login.data['access']}")
        all_names = sorted(r["customer_name"] for r in self.client.get("/api/v1/dealer-portal/customers/").data["results"])
        self.assertEqual(all_names, ["Ahmed", "Sana"])

        # Dealer itself can unassign Ahmed.
        self.dealer_login()
        unassign = self.client.post(
            "/api/v1/dealer-portal/customers/assign/",
            {"customer_ids": [str(ahmed.id)], "employee_id": None},
            format="json",
        )
        self.assertEqual(unassign.status_code, 200)
        ahmed.refresh_from_db()
        self.assertIsNone(ahmed.assigned_dealer_employee_id)
        self.assertEqual(DealerEmployee.objects.filter(dealer=self.dealer).count(), 1)

    def test_phase3_edit_deactivate_restore_and_ledger(self):
        from customers.models import Customer, DealerArea
        from tenancy.models import AuditLog

        self.grant()
        self.dealer_login()

        area = self.client.post("/api/v1/dealer-portal/areas/", {"name": "Model Town"}, format="json").data
        ahmed = Customer.objects.get(organization=self.org, first_name="Ahmed")
        ahmed_svc = ServiceAccount.objects.get(customer=ahmed)
        imran = Customer.objects.get(organization=self.org, first_name="Imran")

        # Employee without edit/deactivate/ledger rights gets 403.
        emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "Limited", "email": "limited@dealer.test", "password": "LimitedPass!123",
            "rights": {"can_view_customers": True, "can_view_all_customers": True},
        }, format="json").data
        self.client.credentials()
        emp_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "limited@dealer.test", "password": "LimitedPass!123",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        self.assertEqual(
            self.client.patch(f"/api/v1/dealer-portal/customers/{ahmed.id}/", {"phone": "03007776665"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.post(f"/api/v1/dealer-portal/customers/{ahmed.id}/deactivate/", {"reason": "Moved"}, format="json").status_code,
            403,
        )
        self.assertEqual(self.client.get(f"/api/v1/dealer-portal/customers/{ahmed.id}/ledger/").status_code, 403)

        # Dealer updates contact fields + valid DealerArea; attempts to alter dealer or package price are ignored.
        self.dealer_login()
        bad_area = self.client.patch(
            f"/api/v1/dealer-portal/customers/{ahmed.id}/",
            {"area": "Nonexistent Zone"},
            format="json",
        )
        self.assertEqual(bad_area.status_code, 400)

        edit_res = self.client.patch(
            f"/api/v1/dealer-portal/customers/{ahmed.id}/",
            {
                "first_name": "Ahmed",
                "last_name": "Raza",
                "phone": "0300-7776665",
                "alternate_phone": "0321-1112223",
                "cnic": "3520212345671",
                "address_line": "Street 9, Model Town",
                "area": area["name"],
                "dealer": str(self.other_dealer.id),
            },
            format="json",
        )
        self.assertEqual(edit_res.status_code, 200)
        ahmed.refresh_from_db()
        ahmed_svc.refresh_from_db()
        self.assertEqual(ahmed.last_name, "Raza")
        self.assertEqual(ahmed.phone, "03007776665")
        self.assertEqual(ahmed.cnic, "35202-1234567-1")
        self.assertEqual(ahmed.area, "Model Town")
        self.assertEqual(ahmed.dealer_id, self.dealer.id)
        self.assertEqual(ahmed_svc.internet_package.monthly_price, Decimal("2800"))
        self.assertTrue(
            AuditLog.objects.filter(organization=self.org, action="DEALER_CUSTOMER_UPDATED", resource_id=str(ahmed.id)).exists()
        )
        # Other dealer customer cannot be edited.
        self.assertEqual(
            self.client.patch(f"/api/v1/dealer-portal/customers/{imran.id}/", {"phone": "03001112223"}, format="json").status_code,
            404,
        )

        # Record a payment and verify ledger shows invoice debit + payment credit + running balance.
        pay = self.client.post(
            f"/api/v1/dealer-portal/services/{ahmed_svc.id}/payments/",
            {"amount": "800", "payment_method": "CASH"},
            format="json",
        )
        self.assertEqual(pay.status_code, 201)
        ledger = self.client.get(f"/api/v1/dealer-portal/customers/{ahmed.id}/ledger/")
        self.assertEqual(ledger.status_code, 200)
        self.assertEqual(Decimal(ledger.data["current_balance"]), Decimal("2000.00"))
        self.assertGreaterEqual(len(ledger.data["entries"]), 2)

        # Deactivate requires reason; suspends service without deleting customer; ISP can restore.
        self.assertEqual(
            self.client.post(f"/api/v1/dealer-portal/customers/{ahmed.id}/deactivate/", {"reason": "   "}, format="json").status_code,
            400,
        )
        deact = self.client.post(
            f"/api/v1/dealer-portal/customers/{ahmed.id}/deactivate/",
            {"reason": "Customer requested disconnection"},
            format="json",
        )
        self.assertEqual(deact.status_code, 200)
        self.assertTrue(Customer.objects.filter(id=ahmed.id).exists())
        ahmed_svc.refresh_from_db()
        self.assertEqual(ahmed_svc.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)
        susp_log = ahmed_svc.suspension_logs.order_by("-created_at").first()
        self.assertIsNotNone(susp_log)
        self.assertIn("Customer requested disconnection", susp_log.reason)

        # ISP Owner restores the customer via existing ManualServiceRestoreView.
        self.client.credentials()
        owner_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": self.owner.email, "password": "OwnerPass!2345",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_login.data['access']}")
        restore = self.client.post(
            f"/api/v1/customers/services/{ahmed_svc.id}/restore/",
            {"reason": "Customer came back"},
            format="json",
        )
        self.assertEqual(restore.status_code, 200)
        ahmed_svc.refresh_from_db()
        self.assertEqual(ahmed_svc.status, ServiceAccount.Status.ACTIVE)

    def test_phase3_dealer_export_xlsx_and_pdf(self):
        from openpyxl import load_workbook
        from customers.models import Customer

        self.grant()
        self.dealer_login()

        ahmed = Customer.objects.get(organization=self.org, first_name="Ahmed")
        emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "Exporter", "email": "exp@dealer.test", "password": "ExportPass!123",
            "rights": {"can_export_customers": True, "can_view_all_customers": False},
        }, format="json").data
        self.client.post(
            "/api/v1/dealer-portal/customers/assign/",
            {"customer_ids": [str(ahmed.id)], "employee_id": emp["id"]},
            format="json",
        )

        # Dealer export includes both Ahmed and Sana, excludes Imran.
        xlsx_resp = self.client.get("/api/v1/dealer-portal/customers/export/?format=xlsx")
        self.assertEqual(xlsx_resp.status_code, 200)
        wb = load_workbook(io.BytesIO(xlsx_resp.content))
        names = [row[1] for row in wb.active.iter_rows(min_row=2, values_only=True)]
        self.assertEqual(sorted(names), ["Ahmed", "Sana"])

        pdf_resp = self.client.get("/api/v1/dealer-portal/customers/export/?format=pdf")
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertTrue(pdf_resp.content.startswith(b"%PDF-"))

        # Scoped employee export includes ONLY assigned Ahmed.
        self.client.credentials()
        emp_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "exp@dealer.test", "password": "ExportPass!123",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        emp_xlsx = self.client.get("/api/v1/dealer-portal/customers/export/?format=xlsx")
        self.assertEqual(emp_xlsx.status_code, 200)
        emp_wb = load_workbook(io.BytesIO(emp_xlsx.content))
        emp_names = [row[1] for row in emp_wb.active.iter_rows(min_row=2, values_only=True)]
        self.assertEqual(emp_names, ["Ahmed"])

        # Without can_export_customers -> 403.
        self.dealer_login()
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{emp['id']}/",
            {"rights": {"can_export_customers": False}},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/customers/export/?format=xlsx").status_code, 403)

    def test_phase4_backdated_payment_and_recharge(self):
        from customers.models import Customer
        from tenancy.models import AuditLog

        self.grant()
        self.dealer_login()
        ahmed = Customer.objects.get(organization=self.org, first_name="Ahmed")
        sana = Customer.objects.get(organization=self.org, first_name="Sana")
        ahmed_svc = ServiceAccount.objects.get(customer=ahmed)
        sana_svc = ServiceAccount.objects.get(customer=sana)

        emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "DateChecker", "email": "date@dealer.test", "password": "DatePass!1234",
            "rights": {
                "can_view_all_customers": True,
                "can_collect_payments": True,
                "can_recharge": True,
                "can_change_payment_date": False,
            },
        }, format="json").data

        self.client.credentials()
        emp_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "date@dealer.test", "password": "DatePass!1234",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")

        three_days_ago = (timezone.localdate() - timedelta(days=3)).isoformat()
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        ten_days_ago = (timezone.localdate() - timedelta(days=10)).isoformat()

        # Without can_change_payment_date -> 403 on backdating collect or recharge.
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/services/{ahmed_svc.id}/payments/",
                {"amount": "500", "payment_method": "CASH", "paid_at": three_days_ago},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/services/{sana_svc.id}/recharge/",
                {"months": 1, "payment_method": "CASH", "paid_at": three_days_ago},
                format="json",
            ).status_code,
            403,
        )

        # Grant can_change_payment_date -> 3 days back works; future & >7 days back rejected.
        self.dealer_login()
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{emp['id']}/",
            {"rights": {"can_change_payment_date": True}},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")

        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/services/{ahmed_svc.id}/payments/",
                {"amount": "500", "payment_method": "CASH", "paid_at": tomorrow},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/services/{ahmed_svc.id}/payments/",
                {"amount": "500", "payment_method": "CASH", "paid_at": ten_days_ago},
                format="json",
            ).status_code,
            400,
        )

        ok_pay = self.client.post(
            f"/api/v1/dealer-portal/services/{ahmed_svc.id}/payments/",
            {"amount": "500", "payment_method": "CASH", "paid_at": three_days_ago},
            format="json",
        )
        self.assertEqual(ok_pay.status_code, 201)
        p1 = Payment.objects.get(id=ok_pay.data["receipt"]["payment_id"])
        self.assertEqual(timezone.localtime(p1.paid_at).date().isoformat(), three_days_ago)

        ok_rech = self.client.post(
            f"/api/v1/dealer-portal/services/{sana_svc.id}/recharge/",
            {"months": 1, "payment_method": "CASH", "paid_at": three_days_ago},
            format="json",
        )
        self.assertEqual(ok_rech.status_code, 201)
        p2 = Payment.objects.get(id=ok_rech.data["receipt"]["payment_id"])
        self.assertEqual(timezone.localtime(p2.paid_at).date().isoformat(), three_days_ago)
        self.assertEqual(
            AuditLog.objects.filter(organization=self.org, action="DEALER_PAYMENT_BACKDATED").count(),
            2,
        )

    def test_phase4_reverse_payment_and_collections_visibility(self):
        from customers.models import Customer

        self.grant()
        self.dealer_login()
        ahmed = Customer.objects.get(organization=self.org, first_name="Ahmed")
        sana = Customer.objects.get(organization=self.org, first_name="Sana")
        imran = Customer.objects.get(organization=self.org, first_name="Imran")
        ahmed_svc = ServiceAccount.objects.get(customer=ahmed)
        sana_svc = ServiceAccount.objects.get(customer=sana)
        imran_svc = ServiceAccount.objects.get(customer=imran)

        # Dealer collects 400 from Sana; foreign dealer payment on Imran created directly.
        dealer_pay = self.client.post(
            f"/api/v1/dealer-portal/services/{sana_svc.id}/payments/",
            {"amount": "400", "payment_method": "CASH"},
            format="json",
        ).data["receipt"]
        from billing.services import record_payment_with_allocations
        imran_pay = record_payment_with_allocations(
            organization=self.org,
            actor=self.owner,
            service_account_id=imran_svc.id,
            amount=Decimal("200"),
            payment_method="CASH",
        )

        # Employee assigned only Ahmed, can_view_collections=True, can_view_all_collections=False, can_reverse_payments=False.
        emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "Collector", "email": "coll@dealer.test", "password": "CollPass!1234",
            "rights": {
                "can_view_customers": True,
                "can_view_all_customers": False,
                "can_collect_payments": True,
                "can_view_collections": True,
                "can_view_all_collections": False,
                "can_reverse_payments": False,
            },
        }, format="json").data
        self.client.post(
            "/api/v1/dealer-portal/customers/assign/",
            {"customer_ids": [str(ahmed.id)], "employee_id": emp["id"]},
            format="json",
        )

        self.client.credentials()
        emp_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "coll@dealer.test", "password": "CollPass!1234",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")

        emp_pay = self.client.post(
            f"/api/v1/dealer-portal/services/{ahmed_svc.id}/payments/",
            {"amount": "600", "payment_method": "CASH"},
            format="json",
        ).data["receipt"]

        # Without can_view_all_collections: sees ONLY own 600 payment, never Sana's 400 or commission.
        own_col = self.client.get("/api/v1/dealer-portal/collections/")
        self.assertEqual(own_col.status_code, 200)
        self.assertNotIn("commission", own_col.data)
        self.assertEqual([r["payment_id"] for r in own_col.data["results"]], [emp_pay["payment_id"]])
        self.assertEqual(Decimal(own_col.data["total_collected"]), Decimal("600.00"))

        # Without can_reverse_payments -> 403.
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/payments/{emp_pay['payment_id']}/reverse/",
                {"reason": "Wrong amount"},
                format="json",
            ).status_code,
            403,
        )

        # Grant can_view_all_collections + can_reverse_payments (still can_view_all_customers=False).
        self.dealer_login()
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{emp['id']}/",
            {"rights": {"can_view_all_collections": True, "can_reverse_payments": True}},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")

        all_col = self.client.get("/api/v1/dealer-portal/collections/")
        self.assertEqual(all_col.status_code, 200)
        self.assertNotIn("commission", all_col.data)
        self.assertEqual(Decimal(all_col.data["total_collected"]), Decimal("1000.00"))
        self.assertEqual(Decimal(all_col.data["collected_by_me"]), Decimal("600.00"))

        # Cannot reverse unassigned Sana's payment (404) or foreign dealer Imran's (404).
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/payments/{dealer_pay['payment_id']}/reverse/",
                {"reason": "No scope"},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/payments/{imran_pay.id}/reverse/",
                {"reason": "Foreign"},
                format="json",
            ).status_code,
            404,
        )

        # Cannot reverse without reason -> 400.
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/payments/{emp_pay['payment_id']}/reverse/",
                {"reason": "   "},
                format="json",
            ).status_code,
            400,
        )

        # Reverse own assigned customer's payment -> 200; duplicate reversal -> 400.
        rev = self.client.post(
            f"/api/v1/dealer-portal/payments/{emp_pay['payment_id']}/reverse/",
            {"reason": "Customer paid via bank instead"},
            format="json",
        )
        self.assertEqual(rev.status_code, 200)
        self.assertTrue(rev.data["is_reversed"])
        self.assertEqual(
            self.client.post(
                f"/api/v1/dealer-portal/payments/{emp_pay['payment_id']}/reverse/",
                {"reason": "Again"},
                format="json",
            ).status_code,
            400,
        )

        # Payment older than 7 days cannot be reversed -> 400.
        Payment.objects.filter(id=dealer_pay["payment_id"]).update(
            paid_at=timezone.now() - timedelta(days=9),
        )
        self.dealer_login()
        old_rev = self.client.post(
            f"/api/v1/dealer-portal/payments/{dealer_pay['payment_id']}/reverse/",
            {"reason": "Too old"},
            format="json",
        )
        self.assertEqual(old_rev.status_code, 400)

        # Reversed payment appears in ISP Reversals report.
        self.client.credentials()
        owner_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": self.owner.email, "password": "OwnerPass!2345",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_login.data['access']}")
        isp_reversals = self.client.get("/api/v1/reports/audit/reversals/")
        self.assertEqual(isp_reversals.status_code, 200)
        reasons = [row.get("reason", "") for row in isp_reversals.data["records"]]
        self.assertTrue(any("Customer paid via bank instead" in r for r in reasons))

    def test_phase5_dealer_complaints(self):
        from customers.models import Customer
        from support.models import Complaint

        self.grant()
        self.dealer_login()
        ahmed = Customer.objects.get(organization=self.org, first_name="Ahmed")
        sana = Customer.objects.get(organization=self.org, first_name="Sana")
        imran = Customer.objects.get(organization=self.org, first_name="Imran")

        # Employee without can_manage_complaints gets 403.
        emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "SupportEmp", "email": "support@dealer.test", "password": "SupportPass!123",
            "rights": {"can_manage_complaints": False, "can_view_all_customers": False},
        }, format="json").data
        self.client.post(
            "/api/v1/dealer-portal/customers/assign/",
            {"customer_ids": [str(ahmed.id)], "employee_id": emp["id"]},
            format="json",
        )

        self.client.credentials()
        emp_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "support@dealer.test", "password": "SupportPass!123",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/complaints/").status_code, 403)
        self.assertEqual(
            self.client.post("/api/v1/dealer-portal/complaints/", {
                "customer_id": str(ahmed.id),
                "category": "CONNECTIVITY",
                "priority": "MEDIUM",
                "subject": "No net",
                "description": "Down since morning",
            }, format="json").status_code,
            403,
        )

        # Dealer logs complaint for Sana, blocked on Imran (404).
        self.dealer_login()
        self.assertEqual(
            self.client.post("/api/v1/dealer-portal/complaints/", {
                "customer_id": str(imran.id),
                "category": "CONNECTIVITY",
                "priority": "MEDIUM",
                "subject": "Foreign",
                "description": "Should fail",
            }, format="json").status_code,
            404,
        )
        sana_cmp = self.client.post("/api/v1/dealer-portal/complaints/", {
            "customer_id": str(sana.id),
            "category": "SPEED",
            "priority": "HIGH",
            "subject": "Slow browsing",
            "description": "Under 2 Mbps since evening",
        }, format="json")
        self.assertEqual(sana_cmp.status_code, 201)
        self.assertEqual(sana_cmp.data["source"], Complaint.Source.DEALER)
        # Status cannot be changed via dealer portal.
        self.assertEqual(self.client.patch("/api/v1/dealer-portal/complaints/", {}, format="json").status_code, 405)

        # Grant can_manage_complaints to scoped employee -> sees only assigned Ahmed, blocked from Sana (404).
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{emp['id']}/",
            {"rights": {"can_manage_complaints": True}},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/complaints/").data["results"], [])
        self.assertEqual(
            self.client.post("/api/v1/dealer-portal/complaints/", {
                "customer_id": str(sana.id),
                "category": "CONNECTIVITY",
                "priority": "MEDIUM",
                "subject": "Unassigned",
                "description": "Not mine",
            }, format="json").status_code,
            404,
        )
        ahmed_cmp = self.client.post("/api/v1/dealer-portal/complaints/", {
            "customer_id": str(ahmed.id),
            "category": "CONNECTIVITY",
            "priority": "MEDIUM",
            "subject": "LOS red light",
            "description": "Customer ONU shows LOS blinking",
        }, format="json")
        self.assertEqual(ahmed_cmp.status_code, 201)
        self.assertEqual(
            [c["id"] for c in self.client.get("/api/v1/dealer-portal/complaints/").data["results"]],
            [ahmed_cmp.data["id"]],
        )

        # ISP Owner sees both DEALER complaints on Support API and resolves Ahmed's complaint.
        self.client.credentials()
        owner_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": self.owner.email, "password": "OwnerPass!2345",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_login.data['access']}")
        isp_list = self.client.get("/api/v1/support/complaints/?source=DEALER")
        self.assertEqual(isp_list.status_code, 200)
        self.assertEqual(len(isp_list.data), 2)

        Complaint.objects.filter(id=ahmed_cmp.data["id"]).update(
            status=Complaint.Status.RESOLVED,
            resolution_summary="Replaced patch cord",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        updated = self.client.get("/api/v1/dealer-portal/complaints/").data["results"][0]
        self.assertEqual(updated["status"], Complaint.Status.RESOLVED)
        self.assertEqual(updated["resolution_summary"], "Replaced patch cord")

    def test_phase6_accounts_journal_and_subdealer_note(self):
        from accounting.models import Account, DealerSettlement
        from customers.models import Country, Customer, DealerEmployeeExpense, DealerJournalEntry
        from openpyxl import load_workbook

        self.grant()
        self.dealer_login()
        ahmed = Customer.objects.get(organization=self.org, first_name="Ahmed")
        ahmed_svc = ServiceAccount.objects.get(customer=ahmed)
        today = timezone.localdate()

        # Collect 1000 from Ahmed, record an ISP payout settlement, and add an approved employee expense.
        self.client.post(
            f"/api/v1/dealer-portal/services/{ahmed_svc.id}/payments/",
            {"amount": "1000", "payment_method": "CASH"},
            format="json",
        )
        emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "AccEmp", "email": "acc@dealer.test", "password": "AccPass!1234",
            "rights": {"can_view_accounts": False, "can_view_journal": False, "can_add_journal_entries": False, "can_void_journal_entries": False},
        }, format="json").data
        from customers.models import DealerEmployee
        emp_obj = DealerEmployee.objects.get(id=emp["id"])
        DealerEmployeeExpense.objects.create(
            organization=self.org,
            dealer=self.dealer,
            employee=emp_obj,
            spent_on=today,
            category=DealerEmployeeExpense.Category.BIKE,
            amount=Decimal("250.00"),
            description="Bike fuel",
            status=DealerEmployeeExpense.Status.APPROVED,
            reviewed_by=self.owner,
            reviewed_at=timezone.now(),
        )
        asset_acc = Account.objects.filter(organization=self.org, category=Account.Category.ASSET).first()
        if asset_acc is None:
            asset_acc = Account.objects.create(
                organization=self.org, code="1099", name="Cash", category=Account.Category.ASSET,
            )
        DealerSettlement.objects.create(
            organization=self.org,
            settlement_number="SET-001",
            dealer=self.dealer,
            payment_account=asset_acc,
            amount=Decimal("100.00"),
            period_start=today.replace(day=1),
            period_end=today,
            settlement_date=today,
            notes="Monthly commission",
            created_by=self.owner,
        )

        # Employee without rights gets 403 on accounts & journal.
        self.client.credentials()
        emp_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "acc@dealer.test", "password": "AccPass!1234",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/accounts/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/dealer-portal/journal/").status_code, 403)
        self.assertEqual(
            self.client.post("/api/v1/dealer-portal/journal/", {
                "date": today.isoformat(), "kind": "EXPENSE", "amount": "150", "description": "Tea",
            }, format="json").status_code,
            403,
        )

        # Dealer views Accounts & Journal, adds a manual entry, exports Excel, voids manual entry (never hard deletes).
        self.dealer_login()
        add_res = self.client.post("/api/v1/dealer-portal/journal/", {
            "date": today.isoformat(), "kind": "EXPENSE", "amount": "300", "description": "Fiber connectors",
        }, format="json")
        self.assertEqual(add_res.status_code, 201)
        manual_id = add_res.data["id"]

        acc_res = self.client.get("/api/v1/dealer-portal/accounts/")
        self.assertEqual(acc_res.status_code, 200)
        self.assertEqual(Decimal(acc_res.data["collected_this_month"]), Decimal("1000.00"))
        self.assertEqual(Decimal(acc_res.data["commission_earned"]), Decimal("100.00"))
        self.assertEqual(Decimal(acc_res.data["payouts_received_this_month"]), Decimal("100.00"))
        self.assertEqual(Decimal(acc_res.data["approved_expenses_this_month"]), Decimal("250.00"))
        self.assertEqual(Decimal(acc_res.data["manual_expense_this_month"]), Decimal("300.00"))

        j_res = self.client.get("/api/v1/dealer-portal/journal/")
        self.assertEqual(j_res.status_code, 200)
        self.assertEqual(Decimal(j_res.data["total_income"]), Decimal("1100.00"))
        self.assertEqual(Decimal(j_res.data["total_expense"]), Decimal("550.00"))
        sources = {r["source"] for r in j_res.data["results"]}
        self.assertEqual(sources, {"MANUAL", "CUSTOMER_PAYMENT", "ISP_PAYOUT", "EMPLOYEE_EXPENSE"})

        # Void manual entry (requires reason), remains in DB and excluded from totals; system rows cannot be voided.
        self.assertEqual(
            self.client.post(f"/api/v1/dealer-portal/journal/{manual_id}/void/", {"reason": "  "}, format="json").status_code,
            400,
        )
        void_res = self.client.post(
            f"/api/v1/dealer-portal/journal/{manual_id}/void/",
            {"reason": "Duplicate bill"},
            format="json",
        )
        self.assertEqual(void_res.status_code, 200)
        self.assertTrue(DealerJournalEntry.objects.filter(id=manual_id, is_void=True).exists())
        j_after = self.client.get("/api/v1/dealer-portal/journal/")
        self.assertEqual(Decimal(j_after.data["total_expense"]), Decimal("250.00"))

        xlsx = self.client.get("/api/v1/dealer-portal/journal/export/")
        self.assertEqual(xlsx.status_code, 200)
        wb = load_workbook(io.BytesIO(xlsx.content))
        self.assertGreaterEqual(wb["Journal"].max_row, 5)

        # Sub-dealer Accounts card shows "Paid by <parent_dealer>".
        country = Country.objects.first()
        sub = Dealer.objects.create(
            organization=self.org, dealer_code="SUB-1", name="SubAli", phone="03000000099",
            country=country, city="Lahore", address_line="Street 2",
            parent_dealer=self.dealer, commission_rate_percentage=Decimal("0"), joining_date=date(2025, 1, 1),
        )
        from customers.dealer_portal import grant_portal_access
        grant_portal_access(
            organization=self.org, actor=self.owner, dealer_id=sub.id, email="sub@dealer.test", password=PASSWORD,
        )
        self.dealer_login("sub@dealer.test")
        sub_acc = self.client.get("/api/v1/dealer-portal/accounts/")
        self.assertEqual(sub_acc.status_code, 200)
        self.assertTrue(sub_acc.data["is_sub_dealer"])
        self.assertEqual(sub_acc.data["commission_note"], "Paid by Bilal")

    def test_phase7_sms_templates_send_broadcast_log_and_cancel(self):
        from communications.models import CommunicationQueue
        from customers.models import Customer

        self.grant()
        self.dealer_login()
        ahmed = Customer.objects.get(organization=self.org, first_name="Ahmed")
        imran = Customer.objects.get(organization=self.org, first_name="Imran")

        # Create template as dealer.
        tpl = self.client.post("/api/v1/dealer-portal/sms-templates/", {
            "name": "Due Reminder",
            "body": "Salam {name}, please clear PKR {due} for {package}.",
        }, format="json")
        self.assertEqual(tpl.status_code, 201)
        tpl_id = tpl.data["id"]

        # Send 1 SMS to Ahmed without gateway -> queued PENDING, never SENT, banner returned.
        send_res = self.client.post("/api/v1/dealer-portal/sms/send/", {
            "customer_id": str(ahmed.id),
            "template_id": tpl_id,
        }, format="json")
        self.assertEqual(send_res.status_code, 201)
        self.assertFalse(send_res.data["gateway_connected"])
        self.assertIn("ISP connects an SMS gateway", send_res.data["banner"])
        q1_id = send_res.data["entry"]["id"]
        q1 = CommunicationQueue.objects.get(id=q1_id)
        self.assertEqual(q1.status, CommunicationQueue.Status.PENDING)
        self.assertIn("Ahmed", q1.rendered_body)
        self.assertIn("2800", q1.rendered_body)

        # Cannot send to foreign dealer customer Imran (404).
        self.assertEqual(
            self.client.post("/api/v1/dealer-portal/sms/send/", {
                "customer_id": str(imran.id), "message": "Hi",
            }, format="json").status_code,
            404,
        )

        # Broadcast to EXPIRING (Sana expires in 2 days) -> queues 1 SMS.
        b_res = self.client.post("/api/v1/dealer-portal/sms/broadcast/", {
            "audience": "EXPIRING",
            "message": "Hi {name}, expires {expiry}.",
        }, format="json")
        self.assertEqual(b_res.status_code, 201)
        self.assertEqual(b_res.data["queued"], 1)

        # Scoped employee rights enforcement.
        emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "SmsEmp", "email": "sms@dealer.test", "password": "SmsPass!1234",
            "rights": {
                "can_view_all_customers": False,
                "can_manage_sms_templates": False,
                "can_send_sms": False,
                "can_broadcast_sms": False,
                "can_view_sms_log": True,
                "can_cancel_sms": False,
            },
        }, format="json").data
        self.client.post(
            "/api/v1/dealer-portal/customers/assign/",
            {"customer_ids": [str(ahmed.id)], "employee_id": emp["id"]},
            format="json",
        )

        self.client.credentials()
        emp_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "sms@dealer.test", "password": "SmsPass!1234",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")

        self.assertEqual(self.client.get("/api/v1/dealer-portal/sms-templates/").status_code, 403)
        self.assertEqual(
            self.client.post("/api/v1/dealer-portal/sms/send/", {"customer_id": str(ahmed.id), "message": "Hi"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.post("/api/v1/dealer-portal/sms/broadcast/", {"audience": "ALL", "message": "Hi"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.post(f"/api/v1/dealer-portal/sms-log/{q1_id}/cancel/", {}, format="json").status_code,
            403,
        )

        # Log sees only assigned Ahmed's SMS, not Sana's.
        log_res = self.client.get("/api/v1/dealer-portal/sms-log/")
        self.assertEqual(log_res.status_code, 200)
        self.assertEqual([r["id"] for r in log_res.data["results"]], [q1_id])

        # Grant can_cancel_sms -> cancels q1 cleanly (no hard delete); second cancel -> 400.
        self.dealer_login()
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{emp['id']}/",
            {"rights": {"can_cancel_sms": True}},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        c_res = self.client.post(f"/api/v1/dealer-portal/sms-log/{q1_id}/cancel/", {}, format="json")
        self.assertEqual(c_res.status_code, 200)
        self.assertEqual(c_res.data["status"], CommunicationQueue.Status.CANCELLED)
        self.assertEqual(
            self.client.post(f"/api/v1/dealer-portal/sms-log/{q1_id}/cancel/", {}, format="json").status_code,
            400,
        )

    def test_phase8_company_info_and_about(self):
        from tenancy.models import AuditLog

        self.org.phone = "042-111-222-333"
        self.org.email = "noc@alpha.test"
        self.org.address = "Gulberg III"
        self.org.save(update_fields=["phone", "email", "address"])

        self.grant()
        self.dealer_login()

        # Employee without can_edit_company_info can view both Company Info and About, but PATCH returns 403.
        emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "Viewer", "email": "info@dealer.test", "password": "InfoPass!1234",
            "rights": {"can_edit_company_info": False},
        }, format="json").data

        self.client.credentials()
        emp_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "info@dealer.test", "password": "InfoPass!1234",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")

        about = self.client.get("/api/v1/dealer-portal/about/")
        self.assertEqual(about.status_code, 200)
        self.assertEqual(about.data["organization"]["name"], "Alpha Net")
        self.assertEqual(about.data["organization"]["phone"], "042-111-222-333")
        self.assertEqual(about.data["powered_by"], "Powered by Nexora ISP")

        info = self.client.get("/api/v1/dealer-portal/company-info/")
        self.assertEqual(info.status_code, 200)
        self.assertFalse(info.data["can_edit"])

        self.assertEqual(
            self.client.patch("/api/v1/dealer-portal/company-info/", {"phone": "03001119999"}, format="json").status_code,
            403,
        )

        # Grant can_edit_company_info -> edits allowed fields, ignores commission_rate_percentage / status.
        self.dealer_login()
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{emp['id']}/",
            {"rights": {"can_edit_company_info": True}},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['access']}")
        upd = self.client.patch(
            "/api/v1/dealer-portal/company-info/",
            {
                "company_name": "Bilal Fiber Point",
                "phone": "03009998881",
                "alternate_phone": "03214445556",
                "email": "shop@bilalfiber.test",
                "address_line": "Main Boulevard Shop 4",
                "city": "Lahore",
                "area": "Gulberg",
                "commission_rate_percentage": "99",
                "dealer_code": "HACKED",
            },
            format="json",
        )
        self.assertEqual(upd.status_code, 200)
        self.assertEqual(upd.data["company_name"], "Bilal Fiber Point")
        self.dealer.refresh_from_db()
        self.assertEqual(self.dealer.phone, "03009998881")
        self.assertEqual(self.dealer.dealer_code, "DL-1")
        self.assertEqual(self.dealer.commission_rate_percentage, Decimal("10.00"))
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.org, action="DEALER_COMPANY_INFO_UPDATED", resource_id=str(self.dealer.id),
            ).exists()
        )

    def test_phase9_jump_impersonation(self):
        from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
        from customers.models import Customer
        from tenancy.models import AuditLog

        self.grant()

        # Staff/Operator CANNOT jump into a dealer (403).
        self.client.credentials()
        staff_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": self.staff.email, "password": "StaffPass!2345",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {staff_login.data['access']}")
        self.assertEqual(
            self.client.post(f"/api/v1/customers/dealers/{self.dealer.id}/jump/", {}, format="json").status_code,
            403,
        )

        # ISP OWNER cannot jump into dealer without portal login (400).
        self.client.credentials()
        owner_login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": self.owner.email, "password": "OwnerPass!2345",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_login.data['access']}")
        self.assertEqual(
            self.client.post(f"/api/v1/customers/dealers/{self.other_dealer.id}/jump/", {}, format="json").status_code,
            400,
        )

        # Verify dealers list exposes has_portal_login cleanly.
        dealers_list = self.client.get("/api/v1/customers/dealers/").data
        by_code = {d["dealer_code"]: d for d in dealers_list["results"] if "results" in dealers_list} if isinstance(dealers_list, dict) else {d["dealer_code"]: d for d in dealers_list}
        self.assertTrue(by_code["DL-1"]["has_portal_login"])
        self.assertFalse(by_code["DL-2"]["has_portal_login"])

        # ISP OWNER jumps into active dealer Bilal -> receives short-lived tokens with impersonated_by.
        jump_res = self.client.post(f"/api/v1/customers/dealers/{self.dealer.id}/jump/", {}, format="json")
        self.assertEqual(jump_res.status_code, 200)
        j_access = AccessToken(jump_res.data["access"])
        j_refresh = RefreshToken(jump_res.data["refresh"])
        self.assertEqual(j_access["impersonated_by"], str(self.owner.id))
        self.assertEqual(j_access["exp"] - j_access["iat"], 30 * 60)
        self.assertEqual(j_refresh["exp"] - j_refresh["iat"], 2 * 3600)
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.org, action="DEALER_PORTAL_JUMP_STARTED", resource_id=str(self.dealer.id),
            ).exists()
        )

        # Summary & payment notes & audit log record impersonation while using jumped token.
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {jump_res.data['access']}")
        summary = self.client.get("/api/v1/dealer-portal/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["me"]["impersonated_by"], str(self.owner.id))

        ahmed = Customer.objects.get(organization=self.org, first_name="Ahmed")
        ahmed_svc = ServiceAccount.objects.get(customer=ahmed)
        pay_res = self.client.post(
            f"/api/v1/dealer-portal/services/{ahmed_svc.id}/payments/",
            {"amount": "500", "payment_method": "CASH"},
            format="json",
        )
        self.assertEqual(pay_res.status_code, 201)
        payment = Payment.objects.get(id=pay_res.data["receipt"]["payment_id"])
        self.assertIn("via ", payment.notes)

        self.client.patch("/api/v1/dealer-portal/company-info/", {"area": "Model Town"}, format="json")
        comp_log = AuditLog.objects.filter(
            organization=self.org, action="DEALER_COMPANY_INFO_UPDATED", resource_id=str(self.dealer.id),
        ).order_by("-created_at").first()
        self.assertEqual(comp_log.metadata.get("impersonated_by"), str(self.owner.id))

        # Jumping back blacklists the jumped refresh token and writes IMPERSONATION_ENDED.
        back_res = self.client.post(
            "/api/v1/auth/jump/back/",
            {"refresh": jump_res.data["refresh"]},
            format="json",
        )
        self.assertEqual(back_res.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(organization=self.org, action="IMPERSONATION_ENDED").exists()
        )
        self.assertIn(
            self.client.post("/api/v1/auth/token/refresh/", {"refresh": jump_res.data["refresh"]}, format="json").status_code,
            (400, 401),
        )

        # Dealer jumps into own active employee, blocked from inactive employee or another employee doing jumps.
        self.dealer_login()
        active_emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "JumpTarget", "email": "jemp@dealer.test", "password": "JumpPass!123",
            "rights": {"can_view_customers": True, "can_view_all_customers": True, "can_collect_payments": True},
        }, format="json").data
        inactive_emp = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "OffEmp", "email": "off@dealer.test", "password": "JumpPass!123",
            "rights": {"can_view_customers": True},
        }, format="json").data
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{inactive_emp['id']}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(
            self.client.post(f"/api/v1/dealer-portal/employees/{inactive_emp['id']}/jump/", {}, format="json").status_code,
            400,
        )

        emp_jump = self.client.post(
            f"/api/v1/dealer-portal/employees/{active_emp['id']}/jump/", {}, format="json",
        )
        self.assertEqual(emp_jump.status_code, 200)
        self.assertEqual(emp_jump.data["jump_kind"], "DEALER_EMPLOYEE")
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.org, action="DEALER_EMPLOYEE_JUMP_STARTED", resource_id=active_emp["id"],
            ).exists()
        )

        # Employee themselves cannot jump into another employee (403).
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_jump.data['access']}")
        self.assertEqual(
            self.client.post(f"/api/v1/dealer-portal/employees/{active_emp['id']}/jump/", {}, format="json").status_code,
            403,
        )







