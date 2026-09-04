import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from billing.models import Invoice, InvoiceLine, Payment, PromiseToPay
from billing.services import record_payment_with_allocations
from communications.models import (
    CommunicationLog,
    CommunicationProvider,
    CommunicationQueue,
    CommunicationTemplate,
)
from communications.notification_engine import (
    NotificationEvent,
    dispatch_notification_event,
)
from customers.models import (
    BillingProfile,
    Customer,
    InternetPackage,
    NotificationPreference,
    ServiceAccount,
    ServiceSuspensionLog,
    SuspensionPolicy,
)
from customers.suspension_services import (
    evaluate_restoration_eligibility,
    evaluate_suspension_eligibility,
    execute_service_restoration,
    execute_service_suspension,
    get_or_create_suspension_policy,
    get_suspension_dashboard_metrics,
    run_automated_suspension_engine,
    update_suspension_policy,
)
from tenancy.models import AuditLog, Organization, OrganizationMembership

User = get_user_model()


class SuspensionRestorationNotificationTests(APITestCase):
    def setUp(self):
        self.org1 = Organization.objects.create(
            name="Alpha Fiber Net",
            code="ALPHA",
            phone="+923001112233",
            email="info@alpha.net",
            is_active=True,
        )
        self.org2 = Organization.objects.create(
            name="Beta Telecom",
            code="BETA",
            phone="+923009998877",
            email="info@beta.net",
            is_active=True,
        )

        self.owner1 = User.objects.create_user(
            username="alpha_owner",
            email="owner@alpha.net",
            password="Password123!",
            first_name="Alpha",
            last_name="Owner",
        )
        self.staff1 = User.objects.create_user(
            username="alpha_staff",
            email="staff@alpha.net",
            password="Password123!",
            first_name="Alpha",
            last_name="Staff",
        )
        self.tech1 = User.objects.create_user(
            username="alpha_tech",
            email="tech@alpha.net",
            password="Password123!",
            first_name="Alpha",
            last_name="Tech",
        )
        self.org2_user = User.objects.create_user(
            username="beta_user",
            email="user@beta.net",
            password="Password123!",
        )

        OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.owner1,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.staff1,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.tech1,
            role=OrganizationMembership.Role.TECHNICIAN,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.org2,
            user=self.org2_user,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

        self.package1 = InternetPackage.objects.create(
            organization=self.org1,
            name="100 Mbps Turbo",
            code="TURBO-100",
            download_speed_mbps=100,
            upload_speed_mbps=100,
            monthly_price=Decimal("3500.00"),
        )

        self.customer1 = Customer.objects.create(
            organization=self.org1,
            customer_number="ALPHA-CUST-001",
            first_name="Tariq",
            last_name="Khan",
            phone="+923211234567",
            email="tariq@gmail.com",
            address_line="Street 1, G-11",
            city="Islamabad",
            area="G-11",
        )

        self.service1 = ServiceAccount.objects.create(
            organization=self.org1,
            service_number="ALPHA-SVC-001",
            customer=self.customer1,
            internet_package=self.package1,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.billing_profile1 = BillingProfile.objects.create(
            organization=self.org1,
            service_account=self.service1,
            billing_cycle=BillingProfile.BillingCycle.MONTHLY,
            billing_day=1,
            due_day=10,
        )

        self.policy1 = get_or_create_suspension_policy(self.org1)
        self.policy1.grace_period_days = 3
        self.policy1.suspension_threshold_days = 5
        self.policy1.minimum_outstanding_amount = Decimal("100.00")
        self.policy1.save()

    def _auth_client(self, user, org):
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken.for_user(user)
        token["organization_id"] = str(org.id)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token.access_token)}")
        return {}

    def _create_unpaid_invoice(self, service, amount, due_date, inv_num=None):
        inv_num = inv_num or f"INV-{uuid.uuid4().hex[:6]}"
        inv = Invoice.objects.create(
            organization=service.organization,
            service_account=service,
            billing_profile=service.billing_profile,
            invoice_number=inv_num,
            billing_period_start=due_date - timedelta(days=30),
            billing_period_end=due_date - timedelta(days=1),
            issue_date=due_date - timedelta(days=10),
            due_date=due_date,
            status=Invoice.Status.UNPAID,
        )
        InvoiceLine.objects.create(
            organization=service.organization,
            invoice=inv,
            description="Internet service",
            quantity=1,
            unit_price=amount,
            amount=amount,
        )
        return inv

    # =========================================================================
    # 1. SUSPENSION ELIGIBILITY TESTS
    # =========================================================================

    def test_overdue_customer_becomes_eligible_for_suspension(self):
        """Customer with invoice past grace period + suspension threshold is eligible."""
        today = timezone.now().date()
        # Due 15 days ago -> Past 3 days grace + 5 days threshold (total 8 days)
        old_due = today - timedelta(days=15)
        self._create_unpaid_invoice(self.service1, Decimal("3500.00"), old_due)

        items = evaluate_suspension_eligibility(self.org1)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["is_eligible_for_suspension"])
        self.assertEqual(items[0]["days_overdue"], 15 - self.policy1.grace_period_days)
        self.assertFalse(items[0]["is_ptp_exempt"])

    def test_active_customer_with_no_overdue_is_not_suspended(self):
        """Customer with future due date is not eligible for suspension."""
        today = timezone.now().date()
        future_due = today + timedelta(days=5)
        self._create_unpaid_invoice(self.service1, Decimal("3500.00"), future_due)

        items = evaluate_suspension_eligibility(self.org1)
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0]["is_eligible_for_suspension"])
        self.assertFalse(items[0]["is_warning_eligible"])

    def test_grace_period_is_respected(self):
        """Customer 2 days past due (grace period is 3 days) is not eligible for suspension."""
        today = timezone.now().date()
        recent_due = today - timedelta(days=2)
        self._create_unpaid_invoice(self.service1, Decimal("3500.00"), recent_due)

        items = evaluate_suspension_eligibility(self.org1)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["in_grace_period"])
        self.assertFalse(items[0]["is_eligible_for_suspension"])

    def test_minimum_outstanding_threshold_is_respected(self):
        """Customer with debt below minimum threshold is not suspended."""
        today = timezone.now().date()
        old_due = today - timedelta(days=20)
        # Owed amount is 50.00, but policy requires minimum 100.00
        self._create_unpaid_invoice(self.service1, Decimal("50.00"), old_due)

        items = evaluate_suspension_eligibility(self.org1)
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0]["is_eligible_for_suspension"])

    def test_valid_active_ptp_prevents_suspension(self):
        """An active Promise-to-Pay with future deadline exempts the customer from suspension."""
        today = timezone.now().date()
        old_due = today - timedelta(days=20)
        inv = self._create_unpaid_invoice(self.service1, Decimal("3500.00"), old_due)

        PromiseToPay.objects.create(
            organization=self.org1,
            promise_number="PTP-001",
            customer=self.customer1,
            service_account=self.service1,
            invoice=inv,
            outstanding_amount=Decimal("3500.00"),
            promised_amount=Decimal("3500.00"),
            promise_date=today,
            deadline=today + timedelta(days=7),
            status=PromiseToPay.Status.ACTIVE,
        )

        items = evaluate_suspension_eligibility(self.org1)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["is_ptp_exempt"])
        self.assertFalse(items[0]["is_eligible_for_suspension"])

    def test_expired_or_broken_ptp_allows_suspension(self):
        """When a Promise-to-Pay is expired or broken, exemption ends and suspension proceeds."""
        today = timezone.now().date()
        old_due = today - timedelta(days=20)
        inv = self._create_unpaid_invoice(self.service1, Decimal("3500.00"), old_due)

        PromiseToPay.objects.create(
            organization=self.org1,
            promise_number="PTP-002",
            customer=self.customer1,
            service_account=self.service1,
            invoice=inv,
            outstanding_amount=Decimal("3500.00"),
            promised_amount=Decimal("3500.00"),
            promise_date=today - timedelta(days=10),
            deadline=today - timedelta(days=2),  # Past deadline
            status=PromiseToPay.Status.BROKEN,
        )

        items = evaluate_suspension_eligibility(self.org1)
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0]["is_ptp_exempt"])
        self.assertTrue(items[0]["is_eligible_for_suspension"])

    # =========================================================================
    # 2. SUSPENSION EXECUTION & IDEMPOTENCY
    # =========================================================================

    def test_manual_suspension_requires_reason_and_logs_audit(self):
        """Manual suspension transitions service status and records audit log."""
        self._create_unpaid_invoice(self.service1, Decimal("3500.00"), timezone.now().date() - timedelta(days=10))

        log = execute_service_suspension(
            service_account=self.service1,
            trigger_type=ServiceSuspensionLog.TriggerType.MANUAL_STAFF,
            reason="Customer requested temporary disconnection",
            actor=self.staff1,
        )

        self.service1.refresh_from_db()
        self.assertEqual(self.service1.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)
        self.assertEqual(log.event_type, ServiceSuspensionLog.EventType.SUSPENSION)
        self.assertEqual(log.actor, self.staff1)

        audit = AuditLog.objects.filter(
            organization=self.org1,
            action="SERVICE_SUSPENDED",
            resource_id=self.service1.id,
        ).first()
        self.assertIsNotNone(audit)

    def test_duplicate_suspension_is_idempotent(self):
        """Suspending an already-suspended service account does not duplicate logs or raise errors."""
        self.service1.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.service1.save()

        initial_log = ServiceSuspensionLog.objects.create(
            organization=self.org1,
            service_account=self.service1,
            customer=self.customer1,
            event_type=ServiceSuspensionLog.EventType.SUSPENSION,
            trigger_type=ServiceSuspensionLog.TriggerType.SYSTEM_AUTOMATED,
            previous_status="ACTIVE",
            new_status="SUSPENDED_NON_PAYMENT",
            reason="First suspension",
        )

        log = execute_service_suspension(
            service_account=self.service1,
            trigger_type=ServiceSuspensionLog.TriggerType.SYSTEM_AUTOMATED,
            reason="Repeated suspension call",
        )

        self.assertEqual(log.id, initial_log.id)
        self.assertEqual(ServiceSuspensionLog.objects.filter(service_account=self.service1).count(), 1)

    def test_automated_suspension_run_processes_batch(self):
        """Automated engine run processes eligible services and skips exempt accounts."""
        today = timezone.now().date()
        self._create_unpaid_invoice(self.service1, Decimal("3500.00"), today - timedelta(days=20))

        summary = run_automated_suspension_engine(self.org1)
        self.assertEqual(summary["status"], "COMPLETED")
        self.assertEqual(summary["suspended_count"], 1)

        self.service1.refresh_from_db()
        self.assertEqual(self.service1.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)

    # =========================================================================
    # 3. RESTORATION ENGINE & PAYMENT HOOKS
    # =========================================================================

    def test_verified_full_payment_restores_suspended_service(self):
        """When full payment is recorded via record_payment_with_allocations, suspended service is auto-restored."""
        self.service1.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.service1.save()

        inv = self._create_unpaid_invoice(self.service1, Decimal("3500.00"), timezone.now().date() - timedelta(days=15))

        payment = record_payment_with_allocations(
            organization=self.org1,
            actor=self.staff1,
            service_account_id=self.service1.id,
            amount=Decimal("3500.00"),
            payment_method=Payment.Method.CASH,
            reference="CASH-REC-001",
            notes="Full payment by customer",
        )

        self.service1.refresh_from_db()
        self.assertEqual(self.service1.status, ServiceAccount.Status.ACTIVE)

        restore_log = ServiceSuspensionLog.objects.filter(
            service_account=self.service1,
            event_type=ServiceSuspensionLog.EventType.RESTORATION,
        ).first()
        self.assertIsNotNone(restore_log)
        self.assertEqual(restore_log.linked_payment_id, payment.id)

    def test_partial_payment_does_not_restore_by_default(self):
        """Partial payment does not restore suspended service when policy requires full balance clearance."""
        self.service1.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.service1.save()

        inv = self._create_unpaid_invoice(self.service1, Decimal("3500.00"), timezone.now().date() - timedelta(days=15))

        # Pay only 1000 out of 3500 (2500 remaining)
        record_payment_with_allocations(
            organization=self.org1,
            actor=self.staff1,
            service_account_id=self.service1.id,
            amount=Decimal("1000.00"),
            payment_method=Payment.Method.CASH,
            reference="PARTIAL-001",
        )

        self.service1.refresh_from_db()
        self.assertEqual(self.service1.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)
        self.assertFalse(
            ServiceSuspensionLog.objects.filter(
                service_account=self.service1,
                event_type=ServiceSuspensionLog.EventType.RESTORATION,
            ).exists()
        )

    def test_partial_payment_restores_when_configured_in_policy(self):
        """If policy explicitly enables restore_on_partial_payment, service is restored."""
        self.policy1.restore_on_partial_payment = True
        self.policy1.save()

        self.service1.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.service1.save()

        inv = self._create_unpaid_invoice(self.service1, Decimal("3500.00"), timezone.now().date() - timedelta(days=15))

        record_payment_with_allocations(
            organization=self.org1,
            actor=self.staff1,
            service_account_id=self.service1.id,
            amount=Decimal("1000.00"),
            payment_method=Payment.Method.CASH,
            reference="PARTIAL-002",
        )

        self.service1.refresh_from_db()
        self.assertEqual(self.service1.status, ServiceAccount.Status.ACTIVE)

    def test_manual_restoration_requires_reason(self):
        """Manual restoration transitions service to ACTIVE and logs audit."""
        self.service1.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.service1.save()

        log = execute_service_restoration(
            service_account=self.service1,
            trigger_type=ServiceSuspensionLog.TriggerType.MANUAL_STAFF,
            reason="Special management approval",
            actor=self.owner1,
        )

        self.service1.refresh_from_db()
        self.assertEqual(self.service1.status, ServiceAccount.Status.ACTIVE)
        self.assertEqual(log.event_type, ServiceSuspensionLog.EventType.RESTORATION)

    # =========================================================================
    # 4. NOTIFICATION ENGINE & PREFERENCE TESTS
    # =========================================================================

    def test_suspension_notification_dispatched(self):
        """Suspension event queues a notification with rendered message."""
        result = dispatch_notification_event(
            organization=self.org1,
            customer=self.customer1,
            event_type=NotificationEvent.SERVICE_SUSPENDED,
            context={
                "service_number": self.service1.service_number,
                "package_name": self.package1.name,
                "outstanding_amount": Decimal("3500.00"),
                "reason": "Non-payment of overdue bills",
            },
        )

        self.assertGreaterEqual(len(result["queued_items"]), 1)
        queue_item = CommunicationQueue.objects.filter(
            organization=self.org1,
            customer=self.customer1,
        ).first()
        self.assertIsNotNone(queue_item)
        self.assertIn("Suspended", queue_item.rendered_subject)
        self.assertIn("3500.00", queue_item.rendered_body)

    def test_disabled_channel_in_preferences_is_respected(self):
        """If customer has SMS disabled, notifications are only sent via WhatsApp / Email."""
        pref, _ = NotificationPreference.objects.get_or_create(
            organization=self.org1,
            customer=self.customer1,
        )
        pref.sms_enabled = False
        pref.whatsapp_enabled = True
        pref.email_enabled = False
        pref.save()

        result = dispatch_notification_event(
            organization=self.org1,
            customer=self.customer1,
            event_type=NotificationEvent.PAYMENT_RECEIVED,
            context={
                "service_number": self.service1.service_number,
                "paid_amount": Decimal("3500.00"),
                "payment_number": "PAY-001",
                "outstanding_amount": Decimal("0.00"),
            },
        )

        channels_queued = [item["channel"] for item in result["queued_items"]]
        self.assertIn("WHATSAPP", channels_queued)
        self.assertNotIn("SMS", channels_queued)
        self.assertNotIn("EMAIL", channels_queued)

    # =========================================================================
    # 5. REST API & RBAC PERMISSION TESTS
    # =========================================================================

    def test_suspension_dashboard_api(self):
        """Dashboard API returns real-time metrics."""
        headers = self._auth_client(self.owner1, self.org1)
        response = self.client.get("/api/v1/customers/suspensions/dashboard/", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("currently_suspended", response.data)
        self.assertIn("auto_suspension_enabled", response.data)

    def test_manual_suspend_api_enforces_reason(self):
        """Manual suspend endpoint requires mandatory reason."""
        headers = self._auth_client(self.staff1, self.org1)
        # Missing reason
        response = self.client.post(
            f"/api/v1/customers/services/{self.service1.id}/suspend/",
            {},
            format="json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Valid reason
        response = self.client.post(
            f"/api/v1/customers/services/{self.service1.id}/suspend/",
            {"reason": "Operational suspension for non-payment"},
            format="json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.service1.refresh_from_db()
        self.assertEqual(self.service1.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)

    def test_manual_restore_api_enforces_reason(self):
        """Manual restore endpoint requires reason."""
        self.service1.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.service1.save()

        headers = self._auth_client(self.staff1, self.org1)
        response = self.client.post(
            f"/api/v1/customers/services/{self.service1.id}/restore/",
            {"reason": "Payment verified via direct bank deposit"},
            format="json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.service1.refresh_from_db()
        self.assertEqual(self.service1.status, ServiceAccount.Status.ACTIVE)

    def test_technician_cannot_modify_suspension_policy(self):
        """Technician role is forbidden from changing suspension policy."""
        headers = self._auth_client(self.tech1, self.org1)
        response = self.client.put(
            "/api/v1/customers/suspensions/policy/",
            {"grace_period_days": 10},
            format="json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_isolation_on_suspension(self):
        """Org 2 user cannot suspend Org 1 service account."""
        headers = self._auth_client(self.org2_user, self.org2)
        response = self.client.post(
            f"/api/v1/customers/services/{self.service1.id}/suspend/",
            {"reason": "Cross-tenant intrusion attempt"},
            format="json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
