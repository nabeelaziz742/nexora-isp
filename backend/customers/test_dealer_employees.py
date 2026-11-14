from decimal import Decimal

from django.test import TestCase

from billing.models import Payment
from customers.models import DealerEmployee
from customers import test_dealer_portal as portal_tests
from tenancy.models import OrganizationMembership

EMPLOYEE_PASSWORD = "Collector!2345"


class DealerEmployeeTests(TestCase):
    # Same ISP, two dealers and three customers as the dealer portal tests.
    # (Borrowed through the module so the runner does not collect those tests twice.)
    setUp = portal_tests.DealerPortalTests.setUp
    grant = portal_tests.DealerPortalTests.grant
    dealer_login = portal_tests.DealerPortalTests.dealer_login

    def as_dealer(self):
        self.assertEqual(self.grant().status_code, 200)
        self.assertEqual(self.dealer_login().status_code, 200)

    def add_employee(self, email="ali@dealer.test", **rights):
        response = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "Ali", "last_name": "Collector", "phone": "03005555555",
            "email": email, "password": EMPLOYEE_PASSWORD, "rights": rights,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def employee_login(self, email="ali@dealer.test"):
        self.client.credentials()
        response = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": email, "password": EMPLOYEE_PASSWORD,
        }, format="json")
        if response.status_code == 200:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    # -- dealer manages employees ----------------------------------------------

    def test_dealer_adds_employee_who_can_sign_in(self):
        self.as_dealer()
        row = self.add_employee(can_collect_payments=True, can_recharge=False)
        self.assertEqual(row["full_name"], "Ali Collector")
        self.assertTrue(row["rights"]["can_collect_payments"])
        self.assertFalse(row["rights"]["can_recharge"])
        login = self.employee_login()
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["role"], "DEALER")
        me = self.client.get("/api/v1/dealer-portal/summary/").data["me"]
        self.assertFalse(me["is_dealer"])
        self.assertEqual(me["name"], "Ali Collector")

    def test_employee_is_not_isp_staff(self):
        self.as_dealer()
        self.add_employee()
        employee = DealerEmployee.objects.get()
        self.assertEqual(employee.membership.role, OrganizationMembership.Role.DEALER)
        self.employee_login()
        self.assertEqual(self.client.get("/api/v1/customers/").status_code, 403)

    def test_employee_cannot_manage_employees(self):
        self.as_dealer()
        self.add_employee()
        self.employee_login()
        self.assertEqual(self.client.get("/api/v1/dealer-portal/employees/").status_code, 403)
        response = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "X", "email": "x@dealer.test", "password": EMPLOYEE_PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_existing_email_is_refused(self):
        self.as_dealer()
        response = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "Ali", "email": "owner@alpha.test", "password": EMPLOYEE_PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_dealer_cannot_touch_another_dealers_employee(self):
        self.as_dealer()
        self.add_employee()
        employee = DealerEmployee.objects.get()
        self.assertEqual(self.grant(email="kashif@dealer.test", dealer=self.other_dealer).status_code, 200)
        self.dealer_login("kashif@dealer.test")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/employees/").data["results"], [])
        response = self.client.patch(f"/api/v1/dealer-portal/employees/{employee.id}/", {"is_active": False},
                                     format="json")
        self.assertEqual(response.status_code, 404)

    # -- rights ------------------------------------------------------------------

    def test_rights_decide_what_an_employee_can_do(self):
        self.as_dealer()
        self.add_employee(can_view_customers=True, can_collect_payments=True, can_recharge=False,
                          can_request_customers=False, can_view_collections=False)
        self.employee_login()

        customers = self.client.get("/api/v1/dealer-portal/customers/")
        self.assertEqual(customers.status_code, 200)
        self.assertEqual(
            sorted(row["customer_name"] for row in customers.data["results"]), ["Ahmed", "Sana"],
        )
        pay = self.client.post(f"/api/v1/dealer-portal/services/{self.ahmed.id}/payments/",
                               {"amount": "1000", "payment_method": "CASH"}, format="json")
        self.assertEqual(pay.status_code, 201, pay.data)

        refused = [
            self.client.post(f"/api/v1/dealer-portal/services/{self.sana.id}/recharge/",
                             {"months": 1, "payment_method": "CASH"}, format="json"),
            self.client.get("/api/v1/dealer-portal/requests/"),
            self.client.get("/api/v1/dealer-portal/collections/"),
        ]
        self.assertEqual([r.status_code for r in refused], [403, 403, 403])

        summary = self.client.get("/api/v1/dealer-portal/summary/").data
        self.assertNotIn("commission_this_month", summary)
        self.assertNotIn("collected_this_month", summary)
        self.assertFalse(summary["me"]["rights"]["can_recharge"])

    def test_dealer_changes_rights_and_they_apply_at_once(self):
        self.as_dealer()
        row = self.add_employee(can_recharge=False)
        self.client.patch(f"/api/v1/dealer-portal/employees/{row['id']}/",
                          {"rights": {"can_recharge": True}}, format="json")
        self.employee_login()
        response = self.client.post(f"/api/v1/dealer-portal/services/{self.sana.id}/recharge/",
                                    {"months": 1, "payment_method": "CASH"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)

    def test_employee_still_limited_to_own_dealers_customers(self):
        self.as_dealer()
        self.add_employee(can_collect_payments=True)
        self.employee_login()
        response = self.client.post(f"/api/v1/dealer-portal/services/{self.imran.id}/payments/",
                                    {"amount": "500", "payment_method": "CASH"}, format="json")
        self.assertEqual(response.status_code, 404)

    # -- switching off -----------------------------------------------------------

    def test_disabled_employee_cannot_sign_in(self):
        self.as_dealer()
        row = self.add_employee()
        self.client.patch(f"/api/v1/dealer-portal/employees/{row['id']}/", {"is_active": False}, format="json")
        self.assertNotEqual(self.employee_login().status_code, 200)

    def test_turning_off_dealer_login_locks_out_employees(self):
        self.as_dealer()
        self.add_employee()
        self.employee_login()
        self.assertEqual(self.client.get("/api/v1/dealer-portal/customers/").status_code, 200)
        self.grant()  # owner signs in again
        self.client.delete(f"/api/v1/customers/dealers/{self.dealer.id}/portal-access/")
        self.employee_login()
        self.assertEqual(self.client.get("/api/v1/dealer-portal/customers/").status_code, 403)

    def test_dealer_resets_employee_password(self):
        self.as_dealer()
        row = self.add_employee()
        response = self.client.post(f"/api/v1/dealer-portal/employees/{row['id']}/password/",
                                    {"password": "Fresh!Gate5521"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(self.employee_login().status_code, 200)
        employee = DealerEmployee.objects.get()
        self.assertTrue(employee.membership.user.check_password("Fresh!Gate5521"))

    # -- who collected what --------------------------------------------------------

    def test_collections_show_who_collected(self):
        self.as_dealer()
        self.add_employee(can_collect_payments=True, can_view_collections=True)
        self.client.post(f"/api/v1/dealer-portal/services/{self.ahmed.id}/payments/",
                         {"amount": "700", "payment_method": "CASH"}, format="json")
        self.employee_login()
        self.client.post(f"/api/v1/dealer-portal/services/{self.ahmed.id}/payments/",
                         {"amount": "300", "payment_method": "CASH"}, format="json")

        own = self.client.get("/api/v1/dealer-portal/collections/").data
        self.assertEqual([r["amount"] for r in own["results"]], ["300.00"])
        self.assertNotIn("commission", own)

        self.dealer_login()
        everything = self.client.get("/api/v1/dealer-portal/collections/").data
        self.assertEqual(everything["total_collected"], "1000.00")
        totals = {row["name"]: row["total"] for row in everything["by_person"]}
        self.assertEqual(totals["Ali Collector"], "300.00")
        self.assertEqual(sum(Decimal(v) for v in totals.values()), Decimal("1000.00"))
        payment = Payment.objects.get(amount=Decimal("300.00"))
        self.assertIn("Ali Collector for dealer DL-1", payment.notes)
