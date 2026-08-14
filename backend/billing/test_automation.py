from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from billing.automation import process_invoice_collection, run_collection_automation
from billing.models import Invoice, InvoiceLine
from customers.models import (
    BillingProfile,
    Customer,
    InternetPackage,
    NotificationPreference,
    ServiceAccount,
)
from tenancy.models import Organization


class CollectionAutomationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Automation ISP",
            code="AUTO-TEST",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )
        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="AUTO-CUST-001",
            first_name="Automation",
            phone="03001234567",
            address_line="Test Address",
            city="Lahore",
        )
        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Test Package",
            code="AUTO-PKG",
            download_speed_mbps=50,
            upload_speed_mbps=20,
            monthly_price=Decimal("2500.00"),
        )
        self.service_account = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="AUTO-SVC-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )
        self.billing_profile = BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service_account,
            billing_day=1,
            due_day=1,
            is_active=True,
        )
        NotificationPreference.objects.create(
            organization=self.organization,
            customer=self.customer,
            whatsapp_enabled=True,
            sms_enabled=False,
        )

    def _invoice(
        self,
        *,
        due_date,
        billing_period_start=date(2026, 8, 1),
        billing_period_end=date(2026, 8, 31),
    ):
        invoice = Invoice.objects.create(
            organization=self.organization,
            invoice_number=f"AUTO-{Invoice.objects.count() + 1:04d}",
            service_account=self.service_account,
            billing_profile=self.billing_profile,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            issue_date=billing_period_start,
            due_date=due_date,
            status=Invoice.Status.UNPAID,
        )
        InvoiceLine.objects.create(
            organization=self.organization,
            invoice=invoice,
            description="Monthly internet service",
            amount=Decimal("2500.00"),
        )
        return invoice

    @patch("billing.automation.queue_customer_notification")
    def test_overdue_invoice_queues_one_reminder(self, queue_notification):
        queue_notification.return_value = type(
            "Result",
            (),
            {"notification_job": object()},
        )()
        invoice = self._invoice(due_date=date(2026, 8, 9))

        result = process_invoice_collection(
            organization=self.organization,
            invoice=invoice,
            as_of_date=date(2026, 8, 10),
            overdue_reminder_days=1,
            final_warning_days=7,
            suspension_days=15,
        )

        self.assertEqual(result.action, "OVERDUE_REMINDER")
        self.assertEqual(result.reason, "QUEUED")
        queue_notification.assert_called_once()
        self.assertEqual(
            queue_notification.call_args.kwargs["event_type"],
            "OVERDUE_REMINDER",
        )

    @patch("billing.automation.queue_customer_notification")
    def test_final_warning_is_used_after_final_warning_threshold(self, queue_notification):
        queue_notification.return_value = type(
            "Result",
            (),
            {"notification_job": object()},
        )()
        invoice = self._invoice(due_date=date(2026, 8, 1))

        result = process_invoice_collection(
            organization=self.organization,
            invoice=invoice,
            as_of_date=date(2026, 8, 8),
            overdue_reminder_days=1,
            final_warning_days=7,
            suspension_days=15,
        )

        self.assertEqual(result.action, "FINAL_WARNING")
        queue_notification.assert_called_once()
        self.assertEqual(
            queue_notification.call_args.kwargs["event_type"],
            "FINAL_WARNING",
        )

    @patch("billing.automation.request_service_suspension")
    @patch("billing.automation._notification_exists", return_value=True)
    def test_suspension_is_requested_after_threshold_when_final_warning_exists(
        self,
        notification_exists,
        request_suspension,
    ):
        request_suspension.return_value = type(
            "Result",
            (),
            {"provisioning_request": type("Request", (), {"id": "request-1"})()},
        )()
        invoice = self._invoice(due_date=date(2026, 8, 1))

        result = process_invoice_collection(
            organization=self.organization,
            invoice=invoice,
            as_of_date=date(2026, 8, 16),
            overdue_reminder_days=1,
            final_warning_days=7,
            suspension_days=15,
        )

        self.assertEqual(result.action, "SUSPENSION_REQUESTED")
        self.assertEqual(result.reason, "SUSPENSION_REQUESTED")
        request_suspension.assert_called_once_with(
            organization=self.organization,
            service_account_id=self.service_account.id,
            requested_by=None,
        )
        notification_exists.assert_called_once()

    def test_collection_runner_skips_paid_invoices_and_future_due_dates(self):
        paid = self._invoice(due_date=date(2026, 8, 1))
        paid.status = Invoice.Status.PAID
        paid.save(update_fields=["status", "updated_at"])
        future = self._invoice(
            due_date=date(2026, 9, 20),
            billing_period_start=date(2026, 9, 1),
            billing_period_end=date(2026, 9, 30),
        )

        with patch("billing.automation.process_invoice_collection") as process:
            process.return_value = type(
                "Result",
                (),
                {"action": "SKIPPED"},
            )()

            result = run_collection_automation(
                organization=self.organization,
                as_of_date=date(2026, 8, 16),
                overdue_reminder_days=1,
                final_warning_days=7,
                suspension_days=15,
            )

        self.assertEqual(result.evaluated_invoices, 0)
        process.assert_not_called()
        self.assertTrue(paid.pk)
        self.assertTrue(future.pk)

    def test_collection_runner_rejects_invalid_threshold_order(self):
        with self.assertRaisesMessage(
            ValueError,
            "Collection thresholds must satisfy: overdue reminder < final warning < suspension.",
        ):
            run_collection_automation(
                organization=self.organization,
                as_of_date=date(2026, 8, 16),
                overdue_reminder_days=7,
                final_warning_days=7,
                suspension_days=15,
            )

    def test_collection_runner_rejects_inactive_organization(self):
        self.organization.is_active = False
        self.organization.save(update_fields=["is_active"])

        with self.assertRaisesMessage(
            ValueError,
            "Organization is not active.",
        ):
            run_collection_automation(
                organization=self.organization,
                as_of_date=date(2026, 8, 16),
                overdue_reminder_days=1,
                final_warning_days=7,
                suspension_days=15,
            )
