from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounting.models import JournalEntry
from billing.models import Invoice, Payment
from billing.recharge_services import (
    calculate_recharge_period,
    change_billing_mode,
    expire_prepaid_services,
    get_expiring_services,
    recharge_service,
)
from billing.services import (
    BillingDomainError,
    generate_monthly_invoices,
    record_payment_with_allocations,
)
from billing.tasks import expire_prepaid_services_task
from customers.models import (
    BillingProfile,
    Customer,
    InternetPackage,
    ServiceAccount,
    ServiceSuspensionLog,
)
from customers.services import activate_customer_service
from tenancy.models import Organization, OrganizationMembership, StaffProfile


User = get_user_model()

TODAY = date(2026, 11, 3)


def frozen_today(value=TODAY):
    return patch("django.utils.timezone.localdate", return_value=value)


class PrepaidFixtureMixin:
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name="Prepaid ISP",
            code="PREPAID-ISP",
            city="Lahore",
            currency="PKR",
        )
        self.owner = User.objects.create_user(
            username="prepaid-owner",
            email="prepaid-owner@nexora.local",
            password="StrongTestPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )
        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="PP-CUST-001",
            first_name="Sara",
            last_name="Ahmed",
            phone="03005555551",
            address_line="Street 2",
            city="Lahore",
        )
        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 10",
            code="PP-10",
            download_speed_mbps=10,
            upload_speed_mbps=5,
            monthly_price="1500.00",
        )
        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="PP-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
            expiry_date=TODAY,
        )
        self.billing_profile = BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service,
            billing_cycle=BillingProfile.BillingCycle.PREPAID,
            billing_day=1,
            due_day=10,
        )

    def recharge(self, months=1, **kwargs):
        return recharge_service(
            organization=self.organization,
            actor=self.owner,
            service_account_id=self.service.id,
            months=months,
            payment_method=Payment.Method.CASH,
            **kwargs,
        )


class RechargePeriodTests(TestCase):
    def test_active_service_extends_from_day_after_expiry(self):
        start, end = calculate_recharge_period(expiry_date=date(2026, 11, 20), months=1, today=TODAY)
        self.assertEqual(start, date(2026, 11, 21))
        self.assertEqual(end, date(2026, 12, 20))

    def test_expired_service_starts_today(self):
        start, end = calculate_recharge_period(expiry_date=date(2026, 10, 1), months=1, today=TODAY)
        self.assertEqual(start, TODAY)
        self.assertEqual(end, date(2026, 12, 2))

    def test_month_end_is_clamped(self):
        start, end = calculate_recharge_period(expiry_date=None, months=1, today=date(2027, 1, 31))
        self.assertEqual(start, date(2027, 1, 31))
        self.assertEqual(end, date(2027, 2, 27))

    def test_multi_month_recharge(self):
        _, end = calculate_recharge_period(expiry_date=None, months=3, today=TODAY)
        self.assertEqual(end, date(2027, 2, 2))


class RechargeServiceTests(PrepaidFixtureMixin, TestCase):
    def test_recharge_creates_paid_invoice_and_extends_expiry(self):
        with frozen_today():
            result = self.recharge(months=1)

        self.service.refresh_from_db()
        self.assertEqual(result.amount, Decimal("1500.00"))
        self.assertEqual(result.previous_expiry_date, TODAY)
        self.assertEqual(result.new_expiry_date, date(2026, 12, 3))
        self.assertEqual(self.service.expiry_date, date(2026, 12, 3))
        self.assertEqual(result.invoice.status, Invoice.Status.PAID)
        self.assertEqual(result.invoice.billing_period_start, date(2026, 11, 4))
        self.assertEqual(result.invoice.billing_period_end, date(2026, 12, 3))
        self.assertEqual(result.payment.amount, Decimal("1500.00"))
        self.assertFalse(result.restored)

    def test_recharge_posts_invoice_and_payment_journal_entries(self):
        with frozen_today():
            result = self.recharge(months=2)

        self.assertTrue(
            JournalEntry.objects.filter(
                organization=self.organization,
                reference_id=str(result.invoice.id),
            ).exists()
        )
        self.assertTrue(
            JournalEntry.objects.filter(
                organization=self.organization,
                reference_id=str(result.payment.id),
            ).exists()
        )

    def test_early_recharges_stack_without_losing_days(self):
        with frozen_today():
            self.recharge(months=1)
            second = self.recharge(months=2)

        self.assertEqual(second.previous_expiry_date, date(2026, 12, 3))
        self.assertEqual(second.new_expiry_date, date(2027, 2, 3))
        self.assertEqual(second.amount, Decimal("3000.00"))

    def test_customer_advance_reduces_recharge_payment(self):
        with frozen_today():
            record_payment_with_allocations(
                organization=self.organization,
                actor=self.owner,
                service_account_id=self.service.id,
                amount="1000.00",
                payment_method=Payment.Method.CASH,
            )
            result = self.recharge(months=1)

        self.assertEqual(result.invoice.status, Invoice.Status.PAID)
        self.assertEqual(result.payment.amount, Decimal("500.00"))

    def test_fully_prepaid_by_advance_needs_no_payment(self):
        with frozen_today():
            record_payment_with_allocations(
                organization=self.organization,
                actor=self.owner,
                service_account_id=self.service.id,
                amount="1500.00",
                payment_method=Payment.Method.CASH,
            )
            result = self.recharge(months=1)

        self.assertIsNone(result.payment)
        self.assertEqual(result.invoice.status, Invoice.Status.PAID)

    def test_recharge_restores_expired_service(self):
        self.service.expiry_date = date(2026, 10, 31)
        self.service.save()

        with frozen_today():
            expire_prepaid_services(organization=self.organization)
            self.service.refresh_from_db()
            self.assertEqual(self.service.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)

            result = self.recharge(months=1)

        self.service.refresh_from_db()
        self.assertTrue(result.restored or self.service.status == ServiceAccount.Status.ACTIVE)
        self.assertEqual(self.service.status, ServiceAccount.Status.ACTIVE)
        self.assertEqual(self.service.expiry_date, date(2026, 12, 2))

    def test_monthly_service_cannot_be_recharged(self):
        self.billing_profile.billing_cycle = BillingProfile.BillingCycle.MONTHLY
        self.billing_profile.save()

        with self.assertRaisesMessage(BillingDomainError, "only available for prepaid"):
            self.recharge(months=1)

    def test_invalid_months_rejected(self):
        with self.assertRaises(BillingDomainError):
            self.recharge(months=0)
        with self.assertRaises(BillingDomainError):
            self.recharge(months=13)


class PrepaidExpiryTests(PrepaidFixtureMixin, TestCase):
    def test_expiry_day_is_still_usable(self):
        with frozen_today():
            result = expire_prepaid_services(organization=self.organization)

        self.assertEqual(result["suspended_count"], 0)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.ACTIVE)

    def test_service_is_suspended_the_day_after_expiry(self):
        with frozen_today(date(2026, 11, 4)):
            result = expire_prepaid_services(organization=self.organization)

        self.assertEqual(result["suspended_count"], 1)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)
        log = ServiceSuspensionLog.objects.get(service_account=self.service)
        self.assertEqual(log.trigger_type, ServiceSuspensionLog.TriggerType.PREPAID_EXPIRY)

    def test_expiry_run_is_idempotent(self):
        with frozen_today(date(2026, 11, 4)):
            expire_prepaid_services(organization=self.organization)
            second = expire_prepaid_services(organization=self.organization)

        self.assertEqual(second["suspended_count"], 0)
        self.assertEqual(ServiceSuspensionLog.objects.filter(service_account=self.service).count(), 1)

    def test_monthly_services_are_never_expired(self):
        self.billing_profile.billing_cycle = BillingProfile.BillingCycle.MONTHLY
        self.billing_profile.save()

        with frozen_today(date(2026, 12, 1)):
            result = expire_prepaid_services(organization=self.organization)

        self.assertEqual(result["suspended_count"], 0)

    def test_task_and_daily_command_run_expiry(self):
        with frozen_today(date(2026, 11, 4)):
            result = expire_prepaid_services_task()
        self.assertEqual(result["suspended_services"], 1)

        self.service.status = ServiceAccount.Status.ACTIVE
        self.service.save()
        ServiceSuspensionLog.objects.all().delete()

        with frozen_today(date(2026, 11, 4)):
            call_command("run_billing_automation", organization_code=self.organization.code, verbosity=0)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)

    def test_expiring_list_includes_expired_and_soon(self):
        other = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="PP-SRV-002",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
            expiry_date=date(2026, 12, 30),
        )
        BillingProfile.objects.create(
            organization=self.organization,
            service_account=other,
            billing_cycle=BillingProfile.BillingCycle.PREPAID,
            billing_day=1,
            due_day=10,
        )

        with frozen_today(date(2026, 11, 2)):
            results = get_expiring_services(organization=self.organization, days=3)

        self.assertEqual([item["service_number"] for item in results], ["PP-SRV-001"])
        self.assertEqual(results[0]["days_left"], 1)


class PrepaidBillingModeTests(PrepaidFixtureMixin, TestCase):
    def test_monthly_run_skips_prepaid_services(self):
        result = generate_monthly_invoices(
            organization=self.organization,
            actor=self.owner,
            billing_year=2026,
            billing_month=11,
        )

        self.assertEqual(result.generated_invoices, 0)
        self.assertFalse(Invoice.objects.filter(service_account=self.service).exists())

    def test_switch_to_monthly_clears_expiry(self):
        service = change_billing_mode(
            organization=self.organization,
            actor=self.owner,
            service_account_id=self.service.id,
            billing_cycle=BillingProfile.BillingCycle.MONTHLY,
        )

        self.assertIsNone(service.expiry_date)
        self.billing_profile.refresh_from_db()
        self.assertEqual(self.billing_profile.billing_cycle, BillingProfile.BillingCycle.MONTHLY)

    def test_switch_to_prepaid_uses_given_expiry(self):
        self.billing_profile.billing_cycle = BillingProfile.BillingCycle.MONTHLY
        self.billing_profile.save()
        self.service.expiry_date = None
        self.service.save()

        service = change_billing_mode(
            organization=self.organization,
            actor=self.owner,
            service_account_id=self.service.id,
            billing_cycle=BillingProfile.BillingCycle.PREPAID,
            expiry_date=date(2026, 11, 30),
        )

        self.assertEqual(service.expiry_date, date(2026, 11, 30))

    def test_prepaid_activation_skips_first_month_invoice(self):
        result = activate_customer_service(
            organization=self.organization,
            actor=self.owner,
            internet_package_id=self.package.id,
            first_name="Prepaid",
            phone="03007777771",
            address_line="Street 9",
            city="Lahore",
            billing_day=1,
            due_day=10,
            billing_cycle=BillingProfile.BillingCycle.PREPAID,
        )

        self.assertEqual(result.billing_profile.billing_cycle, BillingProfile.BillingCycle.PREPAID)
        self.assertIsNotNone(result.service_account.expiry_date)
        self.assertFalse(Invoice.objects.filter(service_account=result.service_account).exists())


class PrepaidAPITests(PrepaidFixtureMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.login(self.owner)}")

    def login(self, user):
        response = self.client.post(
            reverse("tenant-login"),
            {
                "email": user.email,
                "password": "StrongTestPassword123!",
                "organization_code": self.organization.code,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["access"]

    def test_recharge_through_api(self):
        with frozen_today():
            response = self.client.post(
                reverse("billing-service-recharge", kwargs={"service_account_id": self.service.id}),
                {"months": 1, "payment_method": "CASH", "reference": "R-1"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["new_expiry_date"], "2026-12-03")
        self.assertEqual(response.data["amount"], "1500.00")
        self.assertIsNotNone(response.data["payment_number"])

    def test_recharge_monthly_service_returns_400(self):
        self.billing_profile.billing_cycle = BillingProfile.BillingCycle.MONTHLY
        self.billing_profile.save()

        response = self.client.post(
            reverse("billing-service-recharge", kwargs={"service_account_id": self.service.id}),
            {"months": 1, "payment_method": "CASH"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_billing_mode_and_expiring_list_through_api(self):
        response = self.client.put(
            reverse("billing-service-billing-mode", kwargs={"service_account_id": self.service.id}),
            {"billing_cycle": "PREPAID", "expiry_date": "2026-11-04"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with frozen_today():
            listed = self.client.get(reverse("billing-prepaid-expiring"), {"days": 3})

        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(listed.data["results"][0]["days_left"], 1)

    def test_customer_detail_exposes_expiry(self):
        response = self.client.get(reverse("customer-detail", kwargs={"customer_id": self.customer.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        service = response.data["service_accounts"][0]
        self.assertEqual(service["billing_profile"]["billing_cycle"], "PREPAID")
        self.assertEqual(str(service["expiry_date"]), "2026-11-03")

    def test_staff_without_billing_role_cannot_recharge(self):
        staff = User.objects.create_user(
            username="prepaid-tech",
            email="prepaid-tech@nexora.local",
            password="StrongTestPassword123!",
        )
        membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=staff,
            role=OrganizationMembership.Role.STAFF,
        )
        StaffProfile.objects.create(
            organization=self.organization,
            membership=membership,
            user=staff,
            staff_code="PREPAID-ISP-STF-0001",
            role=StaffProfile.Role.TECHNICIAN,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.login(staff)}")

        response = self.client.post(
            reverse("billing-service-recharge", kwargs={"service_account_id": self.service.id}),
            {"months": 1, "payment_method": "CASH"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
