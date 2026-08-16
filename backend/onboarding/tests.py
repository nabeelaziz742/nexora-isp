from io import BytesIO

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

    def register(self):
        response = self.client.post(
            reverse("isp-register"),
            {
                "company_name": "ABC Fiber",
                "city": "Lahore",
                "first_name": "Ali",
                "last_name": "Ahmed",
                "email": "ali@example.com",
                "password": "StrongPassword!123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_registration_starts_pending_and_login_is_blocked(self):
        data = self.register()
        registration = ISPRegistration.objects.get(id=data["registration_id"])

        self.assertEqual(registration.status, ISPRegistration.Status.PENDING_PAYMENT)
        self.assertFalse(registration.owner.is_active)
        self.assertFalse(registration.organization.is_active)
        self.assertFalse(
            OrganizationMembership.objects.get(user=registration.owner, organization=registration.organization).is_active
        )

    def test_receipt_moves_registration_to_pending_verification(self):
        data = self.register()
        response = self.client.post(
            reverse("registration-receipt", kwargs={"access_token": data["access_token"]}),
            {"receipt": self.make_receipt()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], ISPRegistration.Status.PENDING_VERIFICATION)

    def test_admin_can_approve_and_activate_owner(self):
        data = self.register()
        self.client.post(
            reverse("registration-receipt", kwargs={"access_token": data["access_token"]}),
            {"receipt": self.make_receipt()},
            format="multipart",
        )
        admin = User.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="AdminPassword!123",
        )
        self.client.force_authenticate(admin)
        response = self.client.post(
            reverse("superadmin-registration-action", kwargs={"registration_id": data["registration_id"], "action": "approve"}),
            format="json",
        )
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

    def test_admin_reject_keeps_login_blocked_and_allows_resubmission(self):
        data = self.register()
        self.client.post(
            reverse("registration-receipt", kwargs={"access_token": data["access_token"]}),
            {"receipt": self.make_receipt()},
            format="multipart",
        )
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

        resubmit = self.client.post(
            reverse("registration-receipt", kwargs={"access_token": data["access_token"]}),
            {"receipt": self.make_receipt()},
            format="multipart",
        )
        self.assertEqual(resubmit.status_code, 200)
        self.assertEqual(resubmit.json()["status"], ISPRegistration.Status.PENDING_VERIFICATION)
