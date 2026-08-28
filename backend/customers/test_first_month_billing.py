import calendar
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from billing.models import Invoice
from billing.services import generate_monthly_invoices
from customers.models import InternetPackage
from customers.services import activate_customer_service
from tenancy.models import Organization, OrganizationMembership


User = get_user_model()


class FirstMonthBillingTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="First Month Billing ISP",
            code="FIRST-BILL",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )
        self.owner = User.objects.create_user(
            username="first-month-owner",
            email="first-month-owner@nexora.local",
            password="StrongTestPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )
        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 50",
            code="FIRST-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

    def test_activation_generates_first_month_invoice_and_next_month_is_normal(self):
        result = activate_customer_service(
            organization=self.organization,
            actor=self.owner,
            internet_package_id=self.package.id,
            first_name="First",
            last_name="Month",
            phone="03009998877",
            address_line="Test Street 1",
            city="Lahore",
            billing_day=1,
            due_day=10,
        )

        activation_date = timezone.localtime(result.service_account.activated_at).date()
        month_start = activation_date.replace(day=1)
        month_end = activation_date.replace(
            day=calendar.monthrange(activation_date.year, activation_date.month)[1]
        )

        current_month_invoices = Invoice.objects.filter(
            organization=self.organization,
            service_account=result.service_account,
            billing_period_start=month_start,
            billing_period_end=month_end,
        )

        self.assertEqual(current_month_invoices.count(), 1)
        first_invoice = current_month_invoices.get()
        self.assertEqual(first_invoice.issue_date, activation_date)
        self.assertEqual(first_invoice.total_amount, self.package.monthly_price)

        next_month = (
            date(activation_date.year + 1, 1, 1)
            if activation_date.month == 12
            else date(activation_date.year, activation_date.month + 1, 1)
        )
        next_month_result = generate_monthly_invoices(
            organization=self.organization,
            actor=self.owner,
            billing_year=next_month.year,
            billing_month=next_month.month,
        )

        self.assertEqual(next_month_result.generated_invoices, 1)
        self.assertEqual(
            Invoice.objects.filter(
                organization=self.organization,
                service_account=result.service_account,
            ).count(),
            2,
        )

        next_invoice = Invoice.objects.get(
            organization=self.organization,
            service_account=result.service_account,
            billing_period_start=next_month,
        )
        self.assertEqual(next_invoice.issue_date.day, 1)
        self.assertEqual(next_invoice.total_amount, self.package.monthly_price)
