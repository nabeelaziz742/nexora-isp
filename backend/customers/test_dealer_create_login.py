from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from customers import test_dealer_portal as portal_tests
from customers.models import Dealer
from tenancy.models import AuditLog

FIRST_PASSWORD = "Dl-FirstPass42"
SECOND_PASSWORD = "Dl-SecondPass77"
OWN_PASSWORD = "My-Own-Pass!7302"
whatsapp_ok = portal_tests.whatsapp_ok


class DealerLoginOnWhatsAppTests(TestCase):
    """The system makes the dealer's password and sends it only on WhatsApp."""

    setUp = portal_tests.DealerPortalTests.setUp

    def tearDown(self):
        cache.clear()

    def sign_in(self, email, password):
        self.client.credentials()
        response = self.client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
        if response.status_code == 200:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    def as_owner(self):
        self.sign_in(self.owner.email, "OwnerPass!2345")

    def add_dealer(self, **extra):
        body = {"name": "Test Dealer", "phone": "03001234567", "joining_date": "2026-11-01",
                "commission_type": "PERCENTAGE", "commission_rate_percentage": "10", **extra}
        return self.client.post("/api/v1/customers/dealers/", body, format="json")

    def resend(self, dealer):
        return self.client.post(f"/api/v1/customers/dealers/{dealer.id}/portal-access/", {}, format="json")

    def test_new_dealer_gets_password_on_whatsapp_then_changes_it(self):
        self.as_owner()
        with whatsapp_ok(FIRST_PASSWORD) as sent:
            response = self.add_dealer(portal_email="Test.Dealer@Example.com")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["login_sent_to"], "0300****567")
        # One message, to the dealer's phone, carrying the email and the password.
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["phone"], "03001234567")
        self.assertIn("test.dealer@example.com", sent[0]["text"])
        self.assertIn(FIRST_PASSWORD, sent[0]["text"])
        self.assertIn(FIRST_PASSWORD, sent[0]["template_message"]["parameters"])
        # The ISP never gets the password back.
        self.assertNotIn(FIRST_PASSWORD, str(response.data))

        login = self.sign_in("test.dealer@example.com", FIRST_PASSWORD)
        self.assertEqual(login.status_code, 200, login.data)
        self.assertEqual(login.data["role"], "DEALER")
        changed = self.client.post("/api/v1/auth/change-password/", {
            "current_password": FIRST_PASSWORD, "new_password": OWN_PASSWORD,
        }, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        self.assertEqual(self.sign_in("test.dealer@example.com", OWN_PASSWORD).status_code, 200)

    def test_resend_sends_a_new_password_and_the_old_one_stops(self):
        self.as_owner()
        with whatsapp_ok(FIRST_PASSWORD):
            self.add_dealer(portal_email="td@example.com")
        dealer = Dealer.objects.get(name="Test Dealer")
        with whatsapp_ok(SECOND_PASSWORD) as sent:
            response = self.resend(dealer)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["sent_to"], "0300****567")
        self.assertIn(SECOND_PASSWORD, sent[0]["text"])
        self.assertNotIn(SECOND_PASSWORD, str(response.data))
        self.assertEqual(self.sign_in("td@example.com", FIRST_PASSWORD).status_code, 400)
        self.assertEqual(self.sign_in("td@example.com", SECOND_PASSWORD).status_code, 200)

    def test_without_whatsapp_nothing_is_created(self):
        self.as_owner()
        before = Dealer.objects.count()
        with patch("customers.dealer_login_whatsapp.whatsapp_provider", return_value=None):
            response = self.add_dealer(portal_email="td@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("WhatsApp", str(response.data))
        self.assertEqual(Dealer.objects.count(), before)

    def test_failed_message_changes_nothing(self):
        self.as_owner()
        with whatsapp_ok(FIRST_PASSWORD):
            self.add_dealer(portal_email="td@example.com")
        dealer = Dealer.objects.get(name="Test Dealer")
        with (
            patch("customers.dealer_login_whatsapp.whatsapp_provider",
                  side_effect=portal_tests._test_whatsapp_provider),
            patch("customers.dealer_login_whatsapp.generate_password", return_value=SECOND_PASSWORD),
            patch("customers.dealer_login_whatsapp.send_whatsapp",
                  return_value={"success": False, "error": "Template not approved"}),
        ):
            response = self.resend(dealer)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Nothing was changed", str(response.data))
        # The password that reached the dealer still works.
        self.assertEqual(self.sign_in("td@example.com", FIRST_PASSWORD).status_code, 200)

    def test_dealer_without_login_needs_no_whatsapp(self):
        self.as_owner()
        with patch("customers.dealer_login_whatsapp.whatsapp_provider", return_value=None):
            self.assertEqual(self.add_dealer().status_code, 201)
        self.assertIsNone(Dealer.objects.get(name="Test Dealer").portal_membership)

    def test_operator_cannot_send_a_dealer_login(self):
        self.sign_in(self.staff.email, "StaffPass!2345")
        before = Dealer.objects.count()
        with whatsapp_ok():
            response = self.add_dealer(portal_email="op@example.com")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Dealer.objects.count(), before)

    def test_password_is_not_kept_in_audit_logs(self):
        self.as_owner()
        with whatsapp_ok(FIRST_PASSWORD):
            self.add_dealer(portal_email="td@example.com")
        logs = " ".join(str(row) for row in AuditLog.objects.values_list("metadata", flat=True))
        self.assertIn("DEALER_LOGIN_SENT_ON_WHATSAPP", " ".join(AuditLog.objects.values_list("action", flat=True)))
        self.assertNotIn(FIRST_PASSWORD, logs)
