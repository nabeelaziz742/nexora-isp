from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from onboarding.models import ISPSubscriptionPayment, PaymentSettings
from tenancy.models import Organization, OrganizationMembership


class SubscriptionReceiptTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        PaymentSettings.objects.create(
            bank_name="Meezan", account_title="Nexora", account_number="0101", amount="5000.00", is_active=True,
        )
        self.admin = User.objects.create_superuser(
            username="root@example.com", email="root@example.com", password="AdminPassword!123",
        )
        self.org = Organization.objects.create(name="Alpha & Sons Net", code="ALPHA", city="Lahore")
        self.owner = User.objects.create_user(
            username="owner@alpha.test", email="owner@alpha.test", password="OwnerPassword!123",
        )
        OrganizationMembership.objects.create(
            organization=self.org, user=self.owner, role=OrganizationMembership.Role.OWNER, is_active=True,
        )
        self.other = Organization.objects.create(name="Beta Net", code="BETA", city="Karachi")

    def pay(self, organization, amount="5000"):
        self.client.force_authenticate(self.admin)
        url = reverse("superadmin-isp-subscription-payment", kwargs={"organization_id": organization.id})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, {
                "amount": amount, "months": 1, "method": "BANK_TRANSFER", "reference": "TRX <991>",
            }, format="json")
        self.client.force_authenticate(None)
        self.assertEqual(response.status_code, 201)
        return ISPSubscriptionPayment.objects.filter(organization=organization).latest("created_at")

    def owner_client(self):
        login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "owner@alpha.test", "password": "OwnerPassword!123",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_payments_get_sequential_receipt_numbers(self):
        first = self.pay(self.org)
        second = self.pay(self.other)
        self.assertEqual(first.receipt_number, "NXR-000001")
        self.assertEqual(second.receipt_number, "NXR-000002")

    def test_receipt_is_emailed_to_owner_with_pdf(self):
        payment = self.pay(self.org)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["owner@alpha.test"])
        self.assertIn(payment.receipt_number, message.subject)
        filename, content, mimetype = message.attachments[0]
        self.assertEqual(filename, f"{payment.receipt_number}-ALPHA.pdf")
        self.assertEqual(mimetype, "application/pdf")
        self.assertTrue(content.startswith(b"%PDF-"))

    def test_super_admin_downloads_any_receipt(self):
        payment = self.pay(self.org)
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("superadmin-subscription-receipt", kwargs={"payment_id": payment.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn(payment.receipt_number, response["Content-Disposition"])

    def test_owner_downloads_only_own_receipts(self):
        own = self.pay(self.org)
        foreign = self.pay(self.other)
        self.owner_client()
        status_data = self.client.get(reverse("owner-subscription-status")).data
        self.assertEqual([row["receipt_number"] for row in status_data["payments"]], [own.receipt_number])

        ok = self.client.get(reverse("owner-subscription-receipt", kwargs={"payment_id": own.id}))
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.content.startswith(b"%PDF-"))
        blocked = self.client.get(reverse("owner-subscription-receipt", kwargs={"payment_id": foreign.id}))
        self.assertEqual(blocked.status_code, 404)

    def test_owner_cannot_use_super_admin_receipt_url(self):
        payment = self.pay(self.org)
        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse("superadmin-subscription-receipt", kwargs={"payment_id": payment.id}))
        self.assertEqual(response.status_code, 403)
