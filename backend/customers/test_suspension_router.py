from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from billing.automation import process_invoice_collection
from billing.models import Invoice, InvoiceLine, Payment, PromiseToPay
from billing.recharge_services import expire_prepaid_services, recharge_service
from billing.tasks import run_suspension_cycle_task
from customers.models import (
    BillingProfile,
    Customer,
    InternetPackage,
    ServiceAccount,
    ServiceSuspensionLog,
)
from customers.suspension_services import (
    execute_service_restoration,
    execute_service_suspension,
    get_or_create_suspension_policy,
    retry_failed_restorations,
)
from network.models import NetworkAssignment, NetworkNode, ProvisioningRequest
from network.provisioning import execute_provisioning_request
from tenancy.models import Organization, OrganizationMembership


User = get_user_model()


class RouterSuspensionFixtureMixin:
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name="Router ISP",
            code="ROUTER-ISP",
            city="Lahore",
            currency="PKR",
        )
        self.owner = User.objects.create_user(
            username="router-owner",
            email="router-owner@nexora.local",
            password="StrongTestPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )
        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="RT-CUST-001",
            first_name="Usman",
            last_name="Ali",
            phone="03006666661",
            address_line="Street 3",
            city="Lahore",
        )
        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 15",
            code="RT-15",
            download_speed_mbps=15,
            upload_speed_mbps=5,
            monthly_price="2000.00",
        )
        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="RT-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )
        self.billing_profile = BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service,
            billing_day=1,
            due_day=10,
        )
        node = NetworkNode.objects.create(
            organization=self.organization,
            name="Lahore Router",
            code="RT-NODE-1",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.30.0.1",
        )
        self.assignment = NetworkAssignment.objects.create(
            organization=self.organization,
            service_account=self.service,
            network_node=node,
            username="usman-rt",
            ip_address="10.30.0.10",
        )

    def router_requests(self, action=None):
        requests = ProvisioningRequest.objects.filter(service_account=self.service)
        if action:
            requests = requests.filter(action=action)
        return requests

    def run_worker(self):
        for request in self.router_requests().filter(status=ProvisioningRequest.Status.PENDING):
            execute_provisioning_request(provisioning_request_id=request.id)
        self.service.refresh_from_db()

    def overdue_invoice(self, days_overdue=30, status=Invoice.Status.UNPAID):
        due_date = timezone.localdate() - timedelta(days=days_overdue)
        invoice = Invoice.objects.create(
            organization=self.organization,
            invoice_number=f"RT-INV-{Invoice.objects.count() + 1:04d}",
            service_account=self.service,
            billing_profile=self.billing_profile,
            billing_period_start=due_date - timedelta(days=9),
            billing_period_end=due_date + timedelta(days=20),
            issue_date=due_date - timedelta(days=9),
            due_date=due_date,
            status=status,
        )
        InvoiceLine.objects.create(
            organization=self.organization,
            invoice=invoice,
            description="Monthly internet service",
            amount=Decimal("2000.00"),
        )
        return invoice


class RouterSuspensionTests(RouterSuspensionFixtureMixin, TestCase):
    def test_suspension_is_queued_for_the_router_and_confirmed_by_worker(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            log = execute_service_suspension(
                service_account=self.service,
                trigger_type=ServiceSuspensionLog.TriggerType.SYSTEM_AUTOMATED,
                reason="Overdue",
            )

        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.SUSPENSION_PENDING)
        self.assertEqual(log.new_status, ServiceAccount.Status.SUSPENSION_PENDING)
        request = self.router_requests(ProvisioningRequest.Action.SUSPEND).get()
        self.assertEqual(request.status, ProvisioningRequest.Status.PENDING)
        self.assertEqual(len(callbacks), 1)

        self.run_worker()

        request.refresh_from_db()
        self.assertEqual(request.status, ProvisioningRequest.Status.SUCCEEDED)
        self.assertEqual(self.service.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)

    def test_repeated_suspension_does_not_queue_a_second_router_request(self):
        for _ in range(2):
            execute_service_suspension(
                service_account=self.service,
                trigger_type=ServiceSuspensionLog.TriggerType.SYSTEM_AUTOMATED,
                reason="Overdue",
            )
            self.service.refresh_from_db()

        self.assertEqual(self.router_requests(ProvisioningRequest.Action.SUSPEND).count(), 1)
        self.assertEqual(
            ServiceSuspensionLog.objects.filter(
                service_account=self.service,
                event_type=ServiceSuspensionLog.EventType.SUSPENSION,
            ).count(),
            1,
        )

    def test_restoration_is_queued_for_the_router_and_confirmed_by_worker(self):
        self.service.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.service.save()

        execute_service_restoration(
            service_account=self.service,
            trigger_type=ServiceSuspensionLog.TriggerType.MANUAL_STAFF,
            reason="Paid",
        )

        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.RESTORE_PENDING)

        self.run_worker()

        self.assertEqual(self.service.status, ServiceAccount.Status.ACTIVE)
        self.assertEqual(
            self.router_requests(ProvisioningRequest.Action.RESTORE).get().status,
            ProvisioningRequest.Status.SUCCEEDED,
        )

    def test_router_failure_reverts_suspension_so_the_next_run_retries(self):
        execute_service_suspension(
            service_account=self.service,
            trigger_type=ServiceSuspensionLog.TriggerType.SYSTEM_AUTOMATED,
            reason="Overdue",
        )

        with patch(
            "network.providers.stub.StubProvisioningProvider.execute",
            side_effect=Exception("router unreachable"),
        ):
            self.run_worker()

        self.assertEqual(self.service.status, ServiceAccount.Status.ACTIVE)
        self.assertEqual(
            self.router_requests(ProvisioningRequest.Action.SUSPEND).get().status,
            ProvisioningRequest.Status.FAILED,
        )

    def test_service_without_router_is_suspended_directly(self):
        self.assignment.delete()

        execute_service_suspension(
            service_account=self.service,
            trigger_type=ServiceSuspensionLog.TriggerType.MANUAL_STAFF,
            reason="Overdue",
        )

        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)
        self.assertFalse(self.router_requests().exists())


class RestoreRetryTests(RouterSuspensionFixtureMixin, TestCase):
    def test_failed_restore_is_retried(self):
        self.service.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.service.save()
        failed = ProvisioningRequest.objects.create(
            organization=self.organization,
            service_account=self.service,
            network_assignment=self.assignment,
            action=ProvisioningRequest.Action.RESTORE,
            status=ProvisioningRequest.Status.FAILED,
        )

        result = retry_failed_restorations(self.organization)

        self.assertEqual(result["retried_count"], 1)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.RESTORE_PENDING)
        retry = self.router_requests(ProvisioningRequest.Action.RESTORE).exclude(id=failed.id).get()
        self.assertEqual(retry.status, ProvisioningRequest.Status.PENDING)

    def test_deliberate_suspension_is_not_undone(self):
        self.service.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.service.save()
        ProvisioningRequest.objects.create(
            organization=self.organization,
            service_account=self.service,
            network_assignment=self.assignment,
            action=ProvisioningRequest.Action.SUSPEND,
            status=ProvisioningRequest.Status.SUCCEEDED,
        )

        result = retry_failed_restorations(self.organization)

        self.assertEqual(result["retried_count"], 0)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)


class PrepaidRouterTests(RouterSuspensionFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.billing_profile.billing_cycle = BillingProfile.BillingCycle.PREPAID
        self.billing_profile.save()
        self.service.expiry_date = timezone.localdate() - timedelta(days=1)
        self.service.save()

    def test_expiry_and_recharge_reach_the_router(self):
        result = expire_prepaid_services(organization=self.organization)

        self.assertEqual(result["suspended_count"], 1)
        self.assertEqual(result["failed_count"], 0)
        self.run_worker()
        self.assertEqual(self.service.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)

        recharge = recharge_service(
            organization=self.organization,
            actor=self.owner,
            service_account_id=self.service.id,
            months=1,
            payment_method=Payment.Method.CASH,
        )

        self.assertTrue(recharge.restored)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.RESTORE_PENDING)
        self.run_worker()
        self.assertEqual(self.service.status, ServiceAccount.Status.ACTIVE)


class PolicyDrivenSuspensionTests(RouterSuspensionFixtureMixin, TestCase):
    def test_daily_cycle_suspends_overdue_service_through_router(self):
        self.overdue_invoice(days_overdue=30)

        result = run_suspension_cycle_task(organization_id=str(self.organization.id))

        self.assertEqual(result["suspended_services"], 1)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.SUSPENSION_PENDING)
        self.assertEqual(
            self.router_requests(ProvisioningRequest.Action.SUSPEND).get().status,
            ProvisioningRequest.Status.PENDING,
        )

    def test_daily_cycle_respects_disabled_policy(self):
        policy = get_or_create_suspension_policy(self.organization)
        policy.auto_suspension_enabled = False
        policy.save()
        self.overdue_invoice(days_overdue=30)

        result = run_suspension_cycle_task(organization_id=str(self.organization.id))

        self.assertEqual(result["suspended_services"], 0)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.ACTIVE)

    def test_daily_command_runs_policy_cycle(self):
        self.overdue_invoice(days_overdue=30)

        call_command("run_billing_automation", organization_code=self.organization.code, verbosity=0)

        self.service.refresh_from_db()
        self.assertIn(
            self.service.status,
            [ServiceAccount.Status.SUSPENSION_PENDING, ServiceAccount.Status.SUSPENDED_NON_PAYMENT],
        )
        self.assertEqual(self.router_requests(ProvisioningRequest.Action.SUSPEND).count(), 1)


@patch("billing.automation.queue_customer_notification")
class CollectionPolicyTests(RouterSuspensionFixtureMixin, TestCase):
    def collect(self, invoice):
        return process_invoice_collection(
            organization=self.organization,
            invoice=invoice,
            as_of_date=timezone.localdate(),
            overdue_reminder_days=1,
            final_warning_days=7,
            suspension_days=15,
        )

    def with_final_warning(self, invoice):
        from notifications.models import NotificationJob

        NotificationJob.objects.create(
            organization=self.organization,
            customer=self.customer,
            service_account=self.service,
            channel=NotificationJob.Channel.WHATSAPP,
            event_type="FINAL_WARNING",
            recipient=self.customer.phone,
            message="Final warning",
            context={"invoice_id": str(invoice.id)},
        )

    def test_collections_do_not_suspend_when_policy_disabled(self, queue_notification):
        policy = get_or_create_suspension_policy(self.organization)
        policy.auto_suspension_enabled = False
        policy.save()
        invoice = self.overdue_invoice(days_overdue=20)
        self.with_final_warning(invoice)

        result = self.collect(invoice)

        self.assertEqual(result.reason, "AUTO_SUSPENSION_DISABLED")
        self.assertFalse(self.router_requests().exists())

    def test_collections_respect_promise_to_pay(self, queue_notification):
        invoice = self.overdue_invoice(days_overdue=20)
        self.with_final_warning(invoice)
        PromiseToPay.objects.create(
            organization=self.organization,
            promise_number="RT-PTP-1",
            customer=self.customer,
            service_account=self.service,
            invoice=invoice,
            outstanding_amount=Decimal("2000.00"),
            promised_amount=Decimal("2000.00"),
            promise_date=timezone.localdate(),
            deadline=timezone.localdate() + timedelta(days=3),
            status=PromiseToPay.Status.ACTIVE,
        )

        result = self.collect(invoice)

        self.assertEqual(result.reason, "PROMISE_TO_PAY_EXEMPT")

    def test_written_off_invoice_is_not_collected(self, queue_notification):
        invoice = self.overdue_invoice(days_overdue=20, status=Invoice.Status.WRITTEN_OFF)

        result = self.collect(invoice)

        self.assertEqual(result.reason, "INVOICE_NOT_COLLECTABLE")
        queue_notification.assert_not_called()
