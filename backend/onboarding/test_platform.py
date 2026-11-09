from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from customers.models import Customer
from onboarding.models import ISPRegistration, ISPSubscription, ISPSubscriptionPayment, PaymentSettings
from onboarding.platform_services import enforce_subscription_expiry
from tenancy.models import Organization, OrganizationMembership


class SuperAdminPlatformTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        PaymentSettings.objects.create(
            bank_name="Test Bank", account_title="Nexora", account_number="1", amount="5000.00",
            is_active=True, subscription_grace_days=7,
        )
        self.admin = User.objects.create_superuser(
            username="root@example.com", email="root@example.com", password="AdminPassword!123",
        )
        self.org = Organization.objects.create(name="Alpha Net", code="ALPHA", city="Lahore")
        self.owner = User.objects.create_user(
            username="owner@alpha.test", email="owner@alpha.test", password="OwnerPassword!123", first_name="Ali",
        )
        OrganizationMembership.objects.create(
            organization=self.org, user=self.owner, role=OrganizationMembership.Role.OWNER, is_active=True,
        )
        Customer.objects.create(
            organization=self.org, customer_number="ALPHA-C1", first_name="Zain", phone="03001234567",
            address_line="House 1", city="Lahore",
        )

    def as_admin(self):
        self.client.force_authenticate(self.admin)

    def owner_login(self):
        self.client.force_authenticate(None)
        return self.client.post(
            "/api/v1/auth/login/",
            {"organization_code": "ALPHA", "email": "owner@alpha.test", "password": "OwnerPassword!123"},
            format="json",
        )

    def test_non_superuser_is_refused(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(reverse("superadmin-isps")).status_code, 403)
        self.assertEqual(self.client.get(reverse("superadmin-dashboard")).status_code, 403)

    def test_isp_list_shows_counts_but_no_customer_records(self):
        self.as_admin()
        response = self.client.get(reverse("superadmin-isps"))
        self.assertEqual(response.status_code, 200)
        item = next(row for row in response.data["results"] if row["code"] == "ALPHA")
        self.assertEqual(item["customer_count"], 1)
        self.assertEqual(item["staff_count"], 1)
        self.assertEqual(item["owner_email"], "owner@alpha.test")
        self.assertEqual(item["status"], "ACTIVE")
        detail = self.client.get(reverse("superadmin-isp-detail", kwargs={"organization_id": self.org.id}))
        self.assertNotIn("Zain", str(detail.data))
        self.assertNotIn("03001234567", str(detail.data))

    def test_suspend_blocks_login_and_activate_restores_it(self):
        self.as_admin()
        url = reverse("superadmin-isp-suspend", kwargs={"organization_id": self.org.id})
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)
        response = self.client.post(url, {"reason": "Fee not paid"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "SUSPENDED")

        login = self.owner_login()
        self.assertEqual(login.status_code, 400)
        self.assertIn("suspended", str(login.data).lower())

        self.as_admin()
        response = self.client.post(reverse("superadmin-isp-activate", kwargs={"organization_id": self.org.id}))
        self.assertEqual(response.data["status"], "ACTIVE")
        self.assertEqual(self.owner_login().status_code, 200)

    def test_payment_extends_paid_until_from_current_date(self):
        self.as_admin()
        url = reverse("superadmin-isp-subscription-payment", kwargs={"organization_id": self.org.id})
        today = timezone.localdate()
        response = self.client.post(url, {"amount": "5000", "months": 1, "method": "BANK_TRANSFER"}, format="json")
        self.assertEqual(response.status_code, 201)
        first_end = ISPSubscription.objects.get(organization=self.org).paid_until
        self.assertGreater(first_end, today + timedelta(days=26))

        # Paying again early continues from the day after the paid period.
        self.client.post(url, {"amount": "15000", "months": 3, "method": "CASH"}, format="json")
        payments = ISPSubscriptionPayment.objects.filter(organization=self.org).order_by("created_at")
        self.assertEqual(payments[1].period_start, first_end + timedelta(days=1))
        self.assertEqual(ISPSubscription.objects.get(organization=self.org).paid_until, payments[1].period_end)

    def test_expiry_locks_after_grace_and_payment_unlocks(self):
        subscription = ISPSubscription.objects.create(
            organization=self.org, monthly_fee=Decimal("5000"),
            paid_until=timezone.localdate() - timedelta(days=5),
        )
        # Inside the 7-day grace period: still open.
        self.assertEqual(enforce_subscription_expiry()["locked_count"], 0)

        subscription.paid_until = timezone.localdate() - timedelta(days=10)
        subscription.save()
        self.assertEqual(enforce_subscription_expiry()["locked"], ["ALPHA"])
        self.org.refresh_from_db()
        self.assertFalse(self.org.is_active)

        self.as_admin()
        self.client.post(
            reverse("superadmin-isp-subscription-payment", kwargs={"organization_id": self.org.id}),
            {"amount": "5000", "months": 1, "method": "MOBILE_WALLET"},
            format="json",
        )
        self.org.refresh_from_db()
        self.assertTrue(self.org.is_active)

    def test_manual_suspension_is_not_lifted_by_payment(self):
        self.as_admin()
        self.client.post(
            reverse("superadmin-isp-suspend", kwargs={"organization_id": self.org.id}),
            {"reason": "Terms violation"}, format="json",
        )
        self.client.post(
            reverse("superadmin-isp-subscription-payment", kwargs={"organization_id": self.org.id}),
            {"amount": "5000", "months": 1, "method": "CASH"}, format="json",
        )
        self.org.refresh_from_db()
        self.assertFalse(self.org.is_active)

    def test_isps_without_paid_until_are_never_auto_locked(self):
        ISPSubscription.objects.create(organization=self.org, paid_until=None)
        self.assertEqual(enforce_subscription_expiry()["locked_count"], 0)

    def test_dashboard_totals(self):
        ISPSubscription.objects.create(organization=self.org, monthly_fee=Decimal("5000"),
                                       paid_until=timezone.localdate() + timedelta(days=3))
        self.as_admin()
        data = self.client.get(reverse("superadmin-dashboard")).data
        self.assertEqual(data["total_isps"], 1)
        self.assertEqual(data["active_isps"], 1)
        self.assertEqual(data["expiring_soon"], 1)
        self.assertEqual(data["total_customers"], 1)
        self.assertEqual(data["monthly_recurring_revenue"], "5000.00")

    def test_subscription_filter_lists_expiring(self):
        ISPSubscription.objects.create(organization=self.org, paid_until=timezone.localdate() + timedelta(days=2))
        self.as_admin()
        expiring = self.client.get(reverse("superadmin-isps"), {"subscription": "expiring"}).data
        self.assertEqual([row["code"] for row in expiring["results"]], ["ALPHA"])
        expired = self.client.get(reverse("superadmin-isps"), {"subscription": "expired"}).data
        self.assertEqual(expired["count"], 0)

    def test_approval_starts_first_month(self):
        buffer = BytesIO()
        Image.new("RGB", (10, 10), "white").save(buffer, format="PNG")
        self.client.force_authenticate(None)
        created = self.client.post(reverse("isp-register"), {
            "company_name": "Beta Fiber", "city": "Karachi", "first_name": "Sara",
            "email": "sara@beta.test", "password": "StrongPassword!123",
        }, format="json").json()
        self.client.post(
            reverse("registration-receipt", kwargs={"access_token": created["access_token"]}),
            {"receipt": SimpleUploadedFile("r.png", buffer.getvalue(), content_type="image/png")},
            format="multipart",
        )
        self.as_admin()
        list_before = self.client.get(reverse("superadmin-isps"), {"status": "PENDING"}).data
        self.assertIn("Beta Fiber", [row["name"] for row in list_before["results"]])

        self.client.post(reverse("superadmin-registration-action", kwargs={
            "registration_id": created["registration_id"], "action": "approve"}))
        registration = ISPRegistration.objects.get(id=created["registration_id"])
        subscription = ISPSubscription.objects.get(organization=registration.organization)
        self.assertEqual(subscription.monthly_fee, Decimal("5000.00"))
        self.assertIsNotNone(subscription.paid_until)
        self.assertEqual(ISPSubscriptionPayment.objects.filter(organization=registration.organization).count(), 1)


class SubscriptionReminderAndPasswordTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = APIClient()
        PaymentSettings.objects.create(
            bank_name="Meezan", account_title="Nexora", account_number="0101", amount="5000.00",
            is_active=True, subscription_grace_days=7,
        )
        self.admin = User.objects.create_superuser(
            username="root@example.com", email="root@example.com", password="AdminPassword!123",
        )
        self.org = Organization.objects.create(name="Alpha Net", code="ALPHA", city="Lahore")
        self.owner = User.objects.create_user(
            username="owner@alpha.test", email="owner@alpha.test", password="OwnerPassword!123", first_name="Ali",
        )
        OrganizationMembership.objects.create(
            organization=self.org, user=self.owner, role=OrganizationMembership.Role.OWNER, is_active=True,
        )
        self.subscription = ISPSubscription.objects.create(organization=self.org, monthly_fee=Decimal("5000"))

    def set_days_left(self, days):
        self.subscription.paid_until = timezone.localdate() + timedelta(days=days)
        self.subscription.save()

    def test_each_reminder_stage_is_sent_once(self):
        from django.core import mail
        from onboarding.platform_services import send_subscription_reminders

        self.set_days_left(10)
        self.assertEqual(send_subscription_reminders()["sent_count"], 0)

        self.set_days_left(3)
        self.assertEqual(send_subscription_reminders()["sent"], ["ALPHA"])
        self.assertEqual(send_subscription_reminders()["sent_count"], 0)
        self.assertIn("is due on", mail.outbox[0].subject)
        self.assertIn("Meezan", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["owner@alpha.test"])

        today = timezone.localdate()
        self.assertEqual(send_subscription_reminders(today=today + timedelta(days=3))["sent_count"], 1)
        self.assertIn("due today", mail.outbox[1].subject)
        self.assertEqual(send_subscription_reminders(today=today + timedelta(days=4))["sent_count"], 1)
        self.assertIn("overdue", mail.outbox[2].subject)
        self.assertEqual(send_subscription_reminders(today=today + timedelta(days=5))["sent_count"], 0)

    def test_new_paid_period_starts_reminders_again(self):
        from onboarding.platform_services import send_subscription_reminders

        self.set_days_left(2)
        send_subscription_reminders()
        self.set_days_left(33)
        self.subscription.paid_until = timezone.localdate() + timedelta(days=1)
        self.subscription.save()
        self.assertEqual(send_subscription_reminders()["sent_count"], 1)

    def test_owner_sees_own_subscription_status(self):
        self.set_days_left(2)
        login = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": "owner@alpha.test", "password": "OwnerPassword!123",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        data = self.client.get(reverse("owner-subscription-status")).data
        self.assertTrue(data["show_notice"])
        self.assertEqual(data["days_left"], 2)
        self.assertEqual(data["payment"]["bank_name"], "Meezan")

    def test_super_admin_resets_owner_password(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("superadmin-isp-reset-owner-password", kwargs={"organization_id": self.org.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "owner@alpha.test")
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password(response.data["temporary_password"]))

    def test_super_admin_changes_own_password(self):
        self.client.force_authenticate(self.admin)
        url = reverse("superadmin-change-password")
        self.assertEqual(self.client.post(url, {
            "current_password": "wrong", "new_password": "Fresh!Admin987"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {
            "current_password": "AdminPassword!123", "new_password": "Fresh!Admin987"}, format="json").status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("Fresh!Admin987"))
