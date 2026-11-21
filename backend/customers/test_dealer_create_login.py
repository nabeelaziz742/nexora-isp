from django.core.cache import cache
from django.test import TestCase

from customers import test_dealer_portal as portal_tests
from customers.models import Dealer

START_PASSWORD = "Start-Pass!4821"
OWN_PASSWORD = "My-Own-Pass!7302"


class DealerCreatedWithLoginTests(TestCase):
    # ALPHA ISP with an owner and an operator, as in the dealer portal tests.
    setUp = portal_tests.DealerPortalTests.setUp

    def tearDown(self):
        cache.clear()

    def sign_in(self, email, password):
        self.client.credentials()
        response = self.client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
        if response.status_code == 200:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    def add_dealer(self, **extra):
        body = {"name": "Test Dealer", "phone": "03001234567", "joining_date": "2026-11-01",
                "commission_type": "PERCENTAGE", "commission_rate_percentage": "10", **extra}
        return self.client.post("/api/v1/customers/dealers/", body, format="json")

    def test_dealer_gets_login_when_added_and_changes_own_password(self):
        self.sign_in(self.owner.email, "OwnerPass!2345")
        response = self.add_dealer(portal_email="Test.Dealer@Example.com", portal_password=START_PASSWORD)
        self.assertEqual(response.status_code, 201, response.data)
        dealer = Dealer.objects.get(name="Test Dealer")
        self.assertIsNotNone(dealer.portal_membership)

        # The dealer signs in with just email + password and lands in the portal.
        login = self.sign_in("test.dealer@example.com", START_PASSWORD)
        self.assertEqual(login.status_code, 200, login.data)
        self.assertEqual(login.data["role"], "DEALER")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/summary/").status_code, 200)

        # ...and changes the password from their own panel.
        changed = self.client.post("/api/v1/auth/change-password/", {
            "current_password": START_PASSWORD, "new_password": OWN_PASSWORD,
        }, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        self.assertEqual(self.sign_in("test.dealer@example.com", START_PASSWORD).status_code, 400)
        self.assertEqual(self.sign_in("test.dealer@example.com", OWN_PASSWORD).status_code, 200)

    def test_dealer_without_login_still_works(self):
        self.sign_in(self.owner.email, "OwnerPass!2345")
        self.assertEqual(self.add_dealer().status_code, 201)
        self.assertIsNone(Dealer.objects.get(name="Test Dealer").portal_membership)

    def test_bad_login_details_add_nothing(self):
        self.sign_in(self.owner.email, "OwnerPass!2345")
        before = Dealer.objects.count()
        # Email already used by someone else.
        self.assertEqual(self.add_dealer(portal_email=self.owner.email, portal_password=START_PASSWORD).status_code, 400)
        # Email without a password, and a weak password.
        self.assertEqual(self.add_dealer(portal_email="a@example.com").status_code, 400)
        self.assertEqual(self.add_dealer(portal_email="a@example.com", portal_password="123").status_code, 400)
        self.assertEqual(Dealer.objects.count(), before)

    def test_operator_cannot_create_a_dealer_login(self):
        self.sign_in(self.staff.email, "StaffPass!2345")
        before = Dealer.objects.count()
        response = self.add_dealer(portal_email="op@example.com", portal_password=START_PASSWORD)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Dealer.objects.count(), before)
