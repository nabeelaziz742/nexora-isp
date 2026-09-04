from io import BytesIO
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from onboarding.models import ISPRegistration, PaymentSettings
from tenancy.models import OrganizationMembership


class ISPOnboardingFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        PaymentSettings.objects.create(
            bank_name="Test Bank",
            account_title="Nexora Test",
            account_number="123456789",
            iban="PK00TEST",
            amount="10000.00",
            instructions="Transfer the amount and upload your receipt.",
            is_active=True,
        )

    def make_receipt(self):
        buffer = BytesIO()
        Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
        return SimpleUploadedFile("receipt.png", buffer.getvalue(), content_type="image/png")

    def register(self, email="ali@example.com"):
        response = self.client.post(
            reverse("isp-register"),
            {
                "company_name": "ABC Fiber",
                "city": "Lahore",
                "first_name": "Ali",
                "last_name": "Ahmed",
                "email": email,
                "password": "StrongPassword!123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def submit_receipt(self, access_token):
        return self.client.post(
            reverse("registration-receipt", kwargs={"access_token": access_token}),
            {"receipt": self.make_receipt()},
            format="multipart",
        )

    def approve(self, registration_id):
        admin = User.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="AdminPassword!123",
        )
        self.client.force_authenticate(admin)
        return self.client.post(
            reverse("superadmin-registration-action", kwargs={"registration_id": registration_id, "action": "approve"}),
            format="json",
        )

    def test_registration_starts_pending_and_login_is_blocked(self):
        data = self.register()
        registration = ISPRegistration.objects.get(id=data["registration_id"])

        self.assertEqual(registration.status, ISPRegistration.Status.PENDING_PAYMENT)
        self.assertFalse(registration.owner.is_active)
        self.assertFalse(registration.organization.is_active)
        self.assertFalse(
            OrganizationMembership.objects.get(user=registration.owner, organization=registration.organization).is_active
        )

        login = self.client.post(
            reverse("tenant-login"),
            {"email": "ali@example.com", "password": "StrongPassword!123", "organization_code": registration.organization.code},
            format="json",
        )
        self.assertEqual(login.status_code, 400)

    def test_receipt_moves_registration_to_pending_verification(self):
        data = self.register()
        response = self.submit_receipt(data["access_token"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], ISPRegistration.Status.PENDING_VERIFICATION)

    def test_admin_can_approve_and_owner_can_login(self):
        data = self.register()
        self.assertEqual(self.submit_receipt(data["access_token"]).status_code, 200)
        response = self.approve(data["registration_id"])
        self.assertEqual(response.status_code, 200)

        registration = ISPRegistration.objects.get(id=data["registration_id"])
        registration.owner.refresh_from_db()
        registration.organization.refresh_from_db()
        membership = OrganizationMembership.objects.get(user=registration.owner, organization=registration.organization)

        self.assertEqual(registration.status, ISPRegistration.Status.ACTIVE)
        self.assertTrue(registration.owner.is_active)
        self.assertTrue(registration.owner.email_verified)
        self.assertTrue(registration.organization.is_active)
        self.assertTrue(membership.is_active)

        self.client.force_authenticate(user=None)
        login = self.client.post(
            reverse("tenant-login"),
            {"email": "ali@example.com", "password": "StrongPassword!123", "organization_code": registration.organization.code},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.json())

    def test_admin_reject_keeps_login_blocked_and_allows_resubmission(self):
        data = self.register()
        self.assertEqual(self.submit_receipt(data["access_token"]).status_code, 200)

        admin = User.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="AdminPassword!123",
        )
        self.client.force_authenticate(admin)
        response = self.client.post(
            reverse("superadmin-registration-action", kwargs={"registration_id": data["registration_id"], "action": "reject"}),
            {"reason": "Payment not found in bank statement."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        registration = ISPRegistration.objects.get(id=data["registration_id"])
        registration.owner.refresh_from_db()
        self.assertEqual(registration.status, ISPRegistration.Status.REJECTED)
        self.assertFalse(registration.owner.is_active)

        self.client.force_authenticate(user=None)
        login = self.client.post(
            reverse("tenant-login"),
            {"email": "ali@example.com", "password": "StrongPassword!123", "organization_code": registration.organization.code},
            format="json",
        )
        self.assertEqual(login.status_code, 400)

        resubmit = self.submit_receipt(data["access_token"])
        self.assertEqual(resubmit.status_code, 200)
        self.assertEqual(resubmit.json()["status"], ISPRegistration.Status.PENDING_VERIFICATION)

    def test_non_superuser_cannot_access_superadmin_api(self):
        staff = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="StaffPassword!123",
            is_staff=True,
        )
        self.client.force_authenticate(staff)
        response = self.client.get(reverse("superadmin-registrations"))
        self.assertEqual(response.status_code, 403)

    def test_superadmin_payment_settings_creates_default_when_no_record_exists(self):
        PaymentSettings.objects.all().delete()
        self.assertEqual(PaymentSettings.objects.count(), 0)

        admin = User.objects.create_superuser(
            username="superadmin_test@example.com",
            email="superadmin_test@example.com",
            password="AdminPassword!123",
        )
        self.client.force_authenticate(admin)
        response = self.client.get(reverse("superadmin-payment-settings"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["bank_name"], "HBL")
        self.assertEqual(data["account_title"], "Muhammad Nabeel")
        self.assertEqual(data["account_number"], "17877900894403")
        self.assertEqual(float(data["amount"]), 5000.00)
        self.assertTrue(data["is_active"])
        self.assertEqual(PaymentSettings.objects.count(), 1)

    def test_superadmin_payment_settings_returns_saved_settings(self):
        PaymentSettings.objects.all().delete()
        PaymentSettings.objects.create(
            bank_name="Meezan Bank",
            account_title="Nexora Custom Title",
            account_number="998877665544",
            iban="PK99MEZN0001",
            amount="7500.00",
            instructions="Custom deposit instructions.",
            is_active=True,
        )

        admin = User.objects.create_superuser(
            username="superadmin_test2@example.com",
            email="superadmin_test2@example.com",
            password="AdminPassword!123",
        )
        self.client.force_authenticate(admin)
        response = self.client.get(reverse("superadmin-payment-settings"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["bank_name"], "Meezan Bank")
        self.assertEqual(data["account_title"], "Nexora Custom Title")
        self.assertEqual(data["account_number"], "998877665544")

    def test_superadmin_put_updates_settings_without_duplicate_records(self):
        admin = User.objects.create_superuser(
            username="superadmin_test3@example.com",
            email="superadmin_test3@example.com",
            password="AdminPassword!123",
        )
        self.client.force_authenticate(admin)
        put_response = self.client.put(
            reverse("superadmin-payment-settings"),
            {
                "bank_name": "Faysal Bank",
                "account_title": "Nabeel Updated",
                "account_number": "112233445566",
                "iban": "PK11FAYS00001",
                "amount": "6000.00",
                "instructions": "Updated payment notice.",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(put_response.status_code, 200)
        self.assertEqual(put_response.json()["bank_name"], "Faysal Bank")
        self.assertEqual(PaymentSettings.objects.count(), 1)

    def test_registration_and_status_receive_default_payment_settings_when_unconfigured(self):
        PaymentSettings.objects.all().delete()
        data = self.register(email="new_isp_owner@example.com")
        self.assertIn("payment", data)
        self.assertEqual(data["payment"]["bank_name"], "HBL")
        self.assertEqual(data["payment"]["account_number"], "17877900894403")

        status_response = self.client.get(
            reverse("registration-status", kwargs={"access_token": data["access_token"]})
        )
        self.assertEqual(status_response.status_code, 200)
        status_data = status_response.json()
        self.assertIsNotNone(status_data["payment"])
        self.assertEqual(status_data["payment"]["bank_name"], "HBL")
        self.assertEqual(status_data["payment"]["account_title"], "Muhammad Nabeel")
        self.assertEqual(status_data["payment"]["account_number"], "17877900894403")

    def test_admin_approval_sends_activation_email_to_recipient(self):
        data = self.register(email="activation_recipient@example.com")
        self.assertEqual(self.submit_receipt(data["access_token"]).status_code, 200)

        response = self.approve(data["registration_id"])
        self.assertEqual(response.status_code, 200)

        registration = ISPRegistration.objects.get(id=data["registration_id"])
        self.assertEqual(registration.status, ISPRegistration.Status.ACTIVE)
        self.assertTrue(registration.owner.is_active)
        self.assertTrue(registration.organization.is_active)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ["activation_recipient@example.com"])
        self.assertEqual(sent_email.subject, "Nexora ISP account activated")
        self.assertIn(registration.organization.name, sent_email.body)
        self.assertIn(registration.organization.code, sent_email.body)
        self.assertIn("activated", sent_email.body)

    def test_admin_approval_handles_email_failure_without_breaking_activation(self):
        data = self.register(email="fail_email_test@example.com")
        self.assertEqual(self.submit_receipt(data["access_token"]).status_code, 200)

        with patch("onboarding.views.send_mail", side_effect=Exception("Simulated SMTP Connection Refused")):
            with self.assertLogs("onboarding.views", level="ERROR") as captured_logs:
                response = self.approve(data["registration_id"])

        self.assertEqual(response.status_code, 200)

        registration = ISPRegistration.objects.get(id=data["registration_id"])
        registration.owner.refresh_from_db()
        registration.organization.refresh_from_db()
        membership = OrganizationMembership.objects.get(user=registration.owner, organization=registration.organization)

        self.assertEqual(registration.status, ISPRegistration.Status.ACTIVE)
        self.assertTrue(registration.owner.is_active)
        self.assertTrue(registration.organization.is_active)
        self.assertTrue(membership.is_active)

        self.assertTrue(
            any("Failed to deliver activation email" in record for record in captured_logs.output),
            "Expected failure message in captured logs",
        )
        self.assertTrue(
            any(data["registration_id"] in record for record in captured_logs.output),
            "Expected registration ID in error log",
        )
        self.assertTrue(
            any("fail_email_test@example.com" in record for record in captured_logs.output),
            "Expected recipient email in error log",
        )
        for log_line in captured_logs.output:
            self.assertNotIn("password", log_line.lower())
            self.assertNotIn("secret", log_line.lower())


