from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from billing.automation import queue_invoice_generated_notification
from billing.models import Invoice
from customers.models import BillingProfile, Customer, InternetPackage, ServiceAccount
from tenancy.models import Organization


class InvoiceMessageBrandingTests(TestCase):
    """Customers hear from their own ISP, not from the software behind it."""

    def make_invoice(self, name, code):
        org = Organization.objects.create(name=name, code=code, city="Lahore")
        customer = Customer.objects.create(
            organization=org, customer_number=f"{code}-C1", first_name="Ali", phone="03001234567",
            address_line="House 1", city="Lahore",
        )
        package = InternetPackage.objects.create(
            organization=org, name="Home 20", code=f"{code}-H20", download_speed_mbps=20, upload_speed_mbps=20,
            monthly_price="2500",
        )
        service = ServiceAccount.objects.create(
            organization=org, customer=customer, service_number=f"{code}-S1", internet_package=package,
        )
        profile = BillingProfile.objects.create(organization=org, service_account=service, billing_day=1, due_day=10)
        today = timezone.localdate()
        invoice = Invoice.objects.create(
            organization=org, service_account=service, billing_profile=profile, invoice_number=f"{code}-INV-1",
            billing_period_start=today, billing_period_end=today + timedelta(days=29),
            issue_date=today, due_date=today + timedelta(days=10), status=Invoice.Status.UNPAID,
        )
        return org, invoice

    def message_for(self, org, invoice):
        with mock.patch("billing.automation._queue_invoice_notification") as queue:
            queue_invoice_generated_notification(organization=org, invoice=invoice)
        return queue.call_args.kwargs["message"]

    def test_each_isp_bill_message_uses_its_own_name(self):
        abc, abc_invoice = self.make_invoice("ABC Internet", "ABC")
        xyz, xyz_invoice = self.make_invoice("XYZ Broadband", "XYZ")

        abc_message = self.message_for(abc, abc_invoice)
        xyz_message = self.message_for(xyz, xyz_invoice)

        self.assertIn("Your ABC Internet invoice", abc_message)
        self.assertIn("Your XYZ Broadband invoice", xyz_message)
        for message in (abc_message, xyz_message):
            self.assertNotIn("NEXORA", message.upper())
        self.assertNotIn("XYZ", abc_message)
        self.assertNotIn("ABC", xyz_message)
