from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from customers import test_dealer_cash as cash_tests
from customers.models import DealerEmployeeExpense


class DealerEmployeeExpenseTests(TestCase):
    # Same ISP, dealers, customers and helpers as the cash-in-hand tests.
    setUp = cash_tests.DealerEmployeeCashTests.setUp
    grant = cash_tests.DealerEmployeeCashTests.grant
    dealer_login = cash_tests.DealerEmployeeCashTests.dealer_login
    as_dealer = cash_tests.DealerEmployeeCashTests.as_dealer
    add_employee = cash_tests.DealerEmployeeCashTests.add_employee
    employee_login = cash_tests.DealerEmployeeCashTests.employee_login
    owner_login = cash_tests.DealerEmployeeCashTests.owner_login
    collect = cash_tests.DealerEmployeeCashTests.collect
    employee_with_cash = cash_tests.DealerEmployeeCashTests.employee_with_cash
    my_cash = cash_tests.DealerEmployeeCashTests.my_cash

    def ask(self, amount="800", category="BIKE", **extra):
        body = {"category": category, "amount": amount, "spent_on": timezone.localdate().isoformat(), **extra}
        return self.client.post("/api/v1/dealer-portal/expenses/", body, format="json")

    def review(self, expense_id, decision, note=""):
        return self.client.post(f"/api/v1/customers/dealer-expenses/{expense_id}/review/",
                                {"decision": decision, "note": note}, format="json")

    def test_approved_expense_comes_off_cash_in_hand(self):
        self.employee_with_cash()  # Ali holds 1500
        response = self.ask("800", "BIKE", description="Puncture and chain")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "PENDING")
        # Pending changes nothing yet.
        self.assertEqual(self.my_cash()["cash_in_hand"], "1500.00")

        self.owner_login()
        pending = self.client.get("/api/v1/customers/dealer-expenses/", {"status": "PENDING"}).data
        self.assertEqual(pending["counts"]["PENDING"], 1)
        self.assertEqual(pending["results"][0]["employee_name"], "Ali Collector")
        self.assertEqual(pending["results"][0]["dealer_code"], "DL-1")
        approved = self.review(response.data["id"], "APPROVE")
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data["status"], "APPROVED")

        self.employee_login()
        self.assertEqual(self.my_cash()["cash_in_hand"], "700.00")
        mine = self.client.get("/api/v1/dealer-portal/expenses/").data["results"]
        self.assertEqual(mine[0]["status"], "APPROVED")

    def test_rejected_expense_changes_nothing(self):
        self.employee_with_cash()
        expense_id = self.ask("2000", "FOOD").data["id"]
        self.owner_login()
        rejected = self.review(expense_id, "REJECT", note="Too much")
        self.assertEqual(rejected.data["status"], "REJECTED")
        self.assertEqual(rejected.data["review_note"], "Too much")
        # A decision is final.
        self.assertEqual(self.review(expense_id, "APPROVE").status_code, 400)
        self.employee_login()
        self.assertEqual(self.my_cash()["cash_in_hand"], "1500.00")

    def test_request_is_checked(self):
        self.as_dealer()
        self.add_employee()
        self.employee_login()
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assertEqual(self.ask(spent_on=tomorrow).status_code, 400)
        self.assertEqual(self.ask("0").status_code, 400)
        self.assertEqual(self.ask(category="OTHER").status_code, 400)  # needs a description
        self.assertEqual(self.ask(category="OTHER", description="Phone balance").status_code, 201)

    def test_dealer_sees_but_cannot_request_or_decide(self):
        self.as_dealer()
        self.add_employee()
        self.employee_login()
        expense_id = self.ask().data["id"]
        self.dealer_login()
        self.assertEqual(len(self.client.get("/api/v1/dealer-portal/expenses/").data["results"]), 1)
        self.assertEqual(self.ask().status_code, 403)
        # Office URLs are closed to dealer logins.
        self.assertEqual(self.review(expense_id, "APPROVE").status_code, 403)
        self.assertEqual(DealerEmployeeExpense.objects.get().status, "PENDING")

    def test_employee_sees_only_own_requests(self):
        self.as_dealer()
        self.add_employee()
        self.add_employee(email="usman@dealer.test")
        self.employee_login()
        self.ask()
        self.employee_login("usman@dealer.test")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/expenses/").data["results"], [])

    def test_operator_staff_cannot_decide(self):
        self.as_dealer()
        self.add_employee()
        self.employee_login()
        expense_id = self.ask().data["id"]
        self.client.credentials()
        login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": self.staff.email, "password": "StaffPass!2345",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(self.review(expense_id, "APPROVE").status_code, 403)
