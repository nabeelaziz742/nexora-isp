from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from billing.services import cancel_invoice, reverse_payment, write_off_invoice
from billing.test_bad_debt_advance import BillingFixtureMixin, User
from tenancy.models import AuditLog, OrganizationMembership, StaffProfile
from tenancy.services import record_audit_log


class ReversalsReportTests(BillingFixtureMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("reports:reversals-report")
        self.cashier = self.make_staff("rev-cashier", StaffProfile.Role.OPERATOR, first_name="Kashif")

        # Owner: payment reversed (Rs 2500) + invoice written off.
        invoice = self.make_invoice(month=9)
        payment = self.pay("2500.00")
        reverse_payment(
            organization=self.organization,
            actor=self.owner,
            payment_id=payment.id,
            reversal_reason="Cheque bounced",
        )
        write_off_invoice(
            organization=self.organization,
            actor=self.owner,
            invoice_id=invoice.id,
            write_off_reason="Customer left the area",
        )

        # Cashier: invoice voided.
        voided = self.make_invoice(month=10)
        cancel_invoice(
            organization=self.organization,
            actor=self.cashier,
            invoice_id=voided.id,
            cancellation_reason="Duplicate bill",
        )

        # Customer deactivated, then reactivated (only the deactivation counts).
        customer = self.service.customer
        for is_active in (False, True):
            record_audit_log(
                organization=self.organization,
                actor=self.cashier,
                action="CUSTOMER_STATUS_TOGGLED",
                resource_type="Customer",
                resource_id=customer.id,
                metadata={"customer_number": customer.customer_number, "is_active": is_active},
            )

        self.login(self.owner)

    def make_staff(self, username, role, first_name=""):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@nexora.local",
            password="StrongTestPassword123!",
            first_name=first_name,
        )
        membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=user,
            role=OrganizationMembership.Role.STAFF,
        )
        StaffProfile.objects.create(
            organization=self.organization,
            membership=membership,
            user=user,
            staff_code=f"REV-{username}",
            role=role,
        )
        return user

    def login(self, user):
        response = self.client.post(
            reverse("tenant-login"),
            {"email": user.email, "password": "StrongTestPassword123!", "organization_code": self.organization.code},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_report_lists_each_event_with_who_why_and_amount(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_type = {r["event_type"]: r for r in response.data["records"]}
        self.assertEqual(
            set(by_type),
            {"PAYMENT_REVERSED", "INVOICE_WRITTEN_OFF", "INVOICE_VOIDED", "CUSTOMER_DEACTIVATED"},
        )
        reversed_payment = by_type["PAYMENT_REVERSED"]
        self.assertEqual(reversed_payment["amount"], "2500.00")
        self.assertEqual(reversed_payment["reason"], "Cheque bounced")
        self.assertEqual(reversed_payment["customer_number"], "BD-CUST-001")
        self.assertEqual(by_type["INVOICE_VOIDED"]["actor_name"], "Kashif")
        self.assertEqual(by_type["INVOICE_VOIDED"]["reason"], "Duplicate bill")
        self.assertEqual(response.data["total_count"], 4)

    def test_reactivation_is_not_reported_as_deletion(self):
        response = self.client.get(self.url, {"event_type": "CUSTOMER_DEACTIVATED"})

        self.assertEqual(response.data["total_count"], 1)

    def test_summary_groups_by_staff(self):
        response = self.client.get(self.url)

        actors = {row["actor_name"]: row for row in response.data["by_actor"]}
        self.assertEqual(actors["Kashif"]["count"], 2)
        self.assertEqual(actors[self.owner.email]["count"], 2)

    def test_filters_by_staff_type_and_date(self):
        by_staff = self.client.get(self.url, {"actor_id": str(self.cashier.id)})
        self.assertEqual(by_staff.data["total_count"], 2)

        by_type = self.client.get(self.url, {"event_type": "PAYMENT_REVERSED"})
        self.assertEqual(by_type.data["total_count"], 1)

        AuditLog.objects.filter(action="BILLING_PAYMENT_REVERSED").update(
            created_at=timezone.now() - timedelta(days=40)
        )
        recent = self.client.get(
            self.url,
            {"start_date": (timezone.localdate() - timedelta(days=7)).isoformat()},
        )
        self.assertNotIn("PAYMENT_REVERSED", {r["event_type"] for r in recent.data["records"]})

    def test_csv_export(self):
        response = self.client.get(self.url, {"format": "csv"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn(b"Cheque bounced", response.content)

    def test_cashier_cannot_view_oversight_report(self):
        self.login(self.cashier)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_tenant_events_are_not_included(self):
        from tenancy.models import Organization

        other = Organization.objects.create(name="Other", code="OTHER-REV", city="Lahore")
        record_audit_log(
            organization=other,
            actor=None,
            action="BILLING_PAYMENT_REVERSED",
            resource_type="Payment",
            resource_id="x",
            metadata={"payment_number": "OTHER-PAY", "amount": "999.00"},
        )

        response = self.client.get(self.url)

        self.assertNotIn("OTHER-PAY", {r["reference"] for r in response.data["records"]})
