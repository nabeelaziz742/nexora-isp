from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase

from customers import test_dealer_portal as portal_tests
from customers.models import Dealer
from tenancy.models import AuditLog

FIRST_PASSWORD = "Dl-FirstPass42"
SECOND_PASSWORD = "Dl-SecondPass77"
OWN_PASSWORD = "My-Own-Pass!7302"
whatsapp_ok = portal_tests.whatsapp_ok
MODULE = "customers.dealer_login_whatsapp"


class DealerLoginSentToDealerTests(TestCase):
    """The system makes the dealer's password and sends it by email, and on WhatsApp when connected."""

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

    def no_whatsapp(self, password=FIRST_PASSWORD):
        return (
            patch(f"{MODULE}.whatsapp_provider", return_value=None),
            patch(f"{MODULE}.generate_password", return_value=password),
        )

    def test_without_whatsapp_the_password_goes_by_email(self):
        self.as_owner()
        no_wa, fixed = self.no_whatsapp()
        with no_wa, fixed:
            response = self.add_dealer(portal_email="Test.Dealer@Example.com")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["login_sent_to"], "email t***@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["test.dealer@example.com"])
        self.assertIn(FIRST_PASSWORD, mail.outbox[0].body)
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

    def test_with_whatsapp_it_goes_to_both(self):
        self.as_owner()
        with whatsapp_ok(FIRST_PASSWORD) as sent:
            response = self.add_dealer(portal_email="td@example.com")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["login_sent_to"], "email t***@example.com and WhatsApp 0300****567")
        self.assertEqual(sent[0]["phone"], "03001234567")
        self.assertIn(FIRST_PASSWORD, sent[0]["template_message"]["parameters"])
        self.assertIn(FIRST_PASSWORD, mail.outbox[0].body)

    def test_whatsapp_alone_is_enough_when_email_fails(self):
        self.as_owner()
        with whatsapp_ok(FIRST_PASSWORD), patch(f"{MODULE}.send_email", return_value=False):
            response = self.add_dealer(portal_email="td@example.com")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["login_sent_to"], "WhatsApp 0300****567")

    def test_nothing_is_created_when_nothing_can_be_sent(self):
        self.as_owner()
        before = Dealer.objects.count()
        no_wa, fixed = self.no_whatsapp()
        with no_wa, fixed, patch(f"{MODULE}.send_email", return_value=False):
            response = self.add_dealer(portal_email="td@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Nothing was changed", str(response.data))
        self.assertEqual(Dealer.objects.count(), before)

    def test_resend_sends_a_new_password_and_the_old_one_stops(self):
        self.as_owner()
        no_wa, fixed = self.no_whatsapp(FIRST_PASSWORD)
        with no_wa, fixed:
            self.add_dealer(portal_email="td@example.com")
        dealer = Dealer.objects.get(name="Test Dealer")
        no_wa, fixed = self.no_whatsapp(SECOND_PASSWORD)
        with no_wa, fixed:
            response = self.resend(dealer)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["sent_to"], "email t***@example.com")
        self.assertIn(SECOND_PASSWORD, mail.outbox[-1].body)
        self.assertNotIn(SECOND_PASSWORD, str(response.data))
        self.assertEqual(self.sign_in("td@example.com", FIRST_PASSWORD).status_code, 400)
        self.assertEqual(self.sign_in("td@example.com", SECOND_PASSWORD).status_code, 200)

    def test_failed_resend_keeps_the_old_password(self):
        self.as_owner()
        no_wa, fixed = self.no_whatsapp(FIRST_PASSWORD)
        with no_wa, fixed:
            self.add_dealer(portal_email="td@example.com")
        dealer = Dealer.objects.get(name="Test Dealer")
        no_wa, fixed = self.no_whatsapp(SECOND_PASSWORD)
        with no_wa, fixed, patch(f"{MODULE}.send_email", return_value=False):
            response = self.resend(dealer)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.sign_in("td@example.com", FIRST_PASSWORD).status_code, 200)

    def test_operator_cannot_send_a_dealer_login(self):
        self.sign_in(self.staff.email, "StaffPass!2345")
        before = Dealer.objects.count()
        response = self.add_dealer(portal_email="op@example.com")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Dealer.objects.count(), before)

    def test_password_is_not_kept_in_audit_logs(self):
        self.as_owner()
        with whatsapp_ok(FIRST_PASSWORD):
            self.add_dealer(portal_email="td@example.com")
        self.assertIn("DEALER_LOGIN_SENT", list(AuditLog.objects.values_list("action", flat=True)))
        logs = " ".join(str(row) for row in AuditLog.objects.values_list("metadata", flat=True))
        self.assertNotIn(FIRST_PASSWORD, logs)
