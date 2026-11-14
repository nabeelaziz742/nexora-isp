from django.test import TestCase

from billing.models import Payment
from billing.services import reverse_payment
from customers import test_dealer_employees as employee_tests
from customers import test_dealer_portal as portal_tests
from customers.models import DealerCashHandover, DealerEmployee



class DealerEmployeeCashTests(TestCase):
    # Same ISP, dealers and customers as the dealer portal tests.
    setUp = portal_tests.DealerPortalTests.setUp
    grant = portal_tests.DealerPortalTests.grant
    dealer_login = portal_tests.DealerPortalTests.dealer_login
    as_dealer = employee_tests.DealerEmployeeTests.as_dealer
    add_employee = employee_tests.DealerEmployeeTests.add_employee
    employee_login = employee_tests.DealerEmployeeTests.employee_login

    def owner_login(self):
        self.client.credentials()
        login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": self.owner.email, "password": "OwnerPass!2345",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def collect(self, service, amount):
        response = self.client.post(f"/api/v1/dealer-portal/services/{service.id}/payments/",
                                    {"amount": amount, "payment_method": "CASH"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["receipt"]

    def employee_with_cash(self):
        """Ali collects 1000 + 500; the dealer collects 700 himself (not Ali's cash)."""
        self.as_dealer()
        row = self.add_employee(can_collect_payments=True)
        self.collect(self.ahmed, "700")
        self.employee_login()
        self.collect(self.ahmed, "1000")
        self.collect(self.sana, "500")
        return row

    def my_cash(self):
        return self.client.get("/api/v1/dealer-portal/cash/").data

    # -- employee sees their total -------------------------------------------

    def test_employee_sees_what_they_collected(self):
        self.employee_with_cash()
        self.assertEqual(self.my_cash()["cash_in_hand"], "1500.00")
        me = self.client.get("/api/v1/dealer-portal/summary/").data["me"]
        self.assertEqual(me["cash_in_hand"], "1500.00")

    def test_reversed_payment_comes_off_the_total(self):
        self.employee_with_cash()
        ali = DealerEmployee.objects.get().membership.user
        payment = Payment.objects.get(received_by=ali, amount=1000)
        reverse_payment(organization=self.org, actor=self.owner, payment_id=payment.id, reversal_reason="Wrong entry")
        self.assertEqual(self.my_cash()["cash_in_hand"], "500.00")

    # -- dealer receives the cash ----------------------------------------------

    def test_dealer_receives_cash_and_total_goes_to_zero(self):
        row = self.employee_with_cash()
        self.dealer_login()
        team = self.my_cash()
        self.assertEqual(team["total_cash_in_hand"], "1500.00")
        self.assertEqual(team["results"][0]["cash_in_hand"], "1500.00")

        response = self.client.post(f"/api/v1/dealer-portal/employees/{row['id']}/cash-received/", {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["handover"]["amount"], "1500.00")
        self.assertEqual(response.data["handover"]["received_by_type"], "DEALER")
        self.assertEqual(response.data["employee"]["cash_in_hand"], "0.00")

        # Nothing left: a second click records nothing.
        again = self.client.post(f"/api/v1/dealer-portal/employees/{row['id']}/cash-received/", {}, format="json")
        self.assertEqual(again.status_code, 400)
        self.assertEqual(DealerCashHandover.objects.count(), 1)

        # The employee sees zero, and who took the money.
        self.employee_login()
        cash = self.my_cash()
        self.assertEqual(cash["cash_in_hand"], "0.00")
        self.assertEqual(cash["history"][0]["amount"], "1500.00")
        self.assertEqual(cash["history"][0]["received_by"], "Bilal")
        me = self.client.get("/api/v1/dealer-portal/summary/").data["me"]
        self.assertEqual(me["cash_in_hand"], "0.00")
        self.assertEqual(me["last_cash_handover"]["amount"], "1500.00")

        # New collections start counting again from zero.
        self.collect(self.ahmed, "300")
        self.assertEqual(self.my_cash()["cash_in_hand"], "300.00")

    def test_employee_cannot_zero_their_own_cash(self):
        row = self.employee_with_cash()
        response = self.client.post(f"/api/v1/dealer-portal/employees/{row['id']}/cash-received/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.my_cash()["cash_in_hand"], "1500.00")

    def test_other_dealer_cannot_receive_this_employees_cash(self):
        row = self.employee_with_cash()
        self.assertEqual(self.grant(email="kashif@dealer.test", dealer=self.other_dealer).status_code, 200)
        self.dealer_login("kashif@dealer.test")
        response = self.client.post(f"/api/v1/dealer-portal/employees/{row['id']}/cash-received/", {}, format="json")
        self.assertEqual(response.status_code, 404)

    # -- ISP office receives the cash ------------------------------------------

    def test_isp_office_receives_cash(self):
        row = self.employee_with_cash()
        self.owner_login()
        base = f"/api/v1/customers/dealers/{self.dealer.id}"
        team = self.client.get(f"{base}/employee-cash/")
        self.assertEqual(team.status_code, 200)
        self.assertEqual(team.data["total_cash_in_hand"], "1500.00")

        response = self.client.post(f"{base}/employees/{row['id']}/cash-received/",
                                    {"notes": "Handed at office"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["handover"]["received_by_type"], "ISP")
        self.assertEqual(response.data["employee"]["cash_in_hand"], "0.00")

        # Wrong dealer in the URL: not found.
        wrong = self.client.post(
            f"/api/v1/customers/dealers/{self.other_dealer.id}/employees/{row['id']}/cash-received/", {}, format="json",
        )
        self.assertEqual(wrong.status_code, 404)

        self.employee_login()
        self.assertEqual(self.my_cash()["history"][0]["received_by_type"], "ISP")

    def test_operator_staff_cannot_zero_cash(self):
        row = self.employee_with_cash()
        self.client.credentials()
        login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": self.staff.email, "password": "StaffPass!2345",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self.client.post(
            f"/api/v1/customers/dealers/{self.dealer.id}/employees/{row['id']}/cash-received/", {}, format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(DealerCashHandover.objects.count(), 0)
