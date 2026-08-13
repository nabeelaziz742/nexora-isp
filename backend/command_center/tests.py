from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from command_center.copilot import CopilotAnswer

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
)
from customers.models import (
    BillingProfile,
    Customer,
    InternetPackage,
    ServiceAccount,
)
from inventory.models import InventoryDevice
from network.models import (
    NetworkAssignment,
    NetworkNode,
    ProvisioningRequest,
)
from notifications.models import NotificationJob
from tenancy.models import (
    AuditLog,
    Organization,
    OrganizationMembership,
)


class CommandCenterOperationalAPITests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Command Center ISP",
            code="COMMAND-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Command Center ISP",
            code="OTHER-COMMAND",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        User = get_user_model()

        self.owner = User.objects.create_user(
            username="command-center-owner",
            email="command-center-owner@nexora.test",
            password="StrongPass123!",
            first_name="Command",
            last_name="Owner",
        )

        self.other_owner = User.objects.create_user(
            username="other-command-owner",
            email="other-command-owner@nexora.test",
            password="StrongPass123!",
            first_name="Other",
            last_name="Owner",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )

        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_owner,
            role=OrganizationMembership.Role.OWNER,
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="CMD-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03007770001",
            address_line="Command Center Street",
            city="Lahore",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Command Fiber 50",
            code="CMD-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="CMD-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.network_node = NetworkNode.objects.create(
            organization=self.organization,
            name="Command Center OLT",
            code="CMD-OLT-001",
            node_type=NetworkNode.NodeType.OLT,
            management_ip="10.10.10.1",
            location="Lahore NOC",
            is_active=True,
        )

        self.network_assignment = (
            NetworkAssignment.objects.create(
                organization=self.organization,
                service_account=self.service,
                network_node=self.network_node,
                username="cmd-srv-001",
                ip_address="10.10.10.10",
                is_active=True,
            )
        )

        self.billing_profile = BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service,
            billing_day=1,
            due_day=10,
        )

        self.invoice = Invoice.objects.create(
            organization=self.organization,
            invoice_number="CMD-INV-001",
            service_account=self.service,
            billing_profile=self.billing_profile,
            billing_period_start=date(2026, 7, 1),
            billing_period_end=date(2026, 7, 31),
            issue_date=date(2026, 7, 1),
            due_date=date(2026, 7, 10),
            status=Invoice.Status.PARTIALLY_PAID,
        )

        InvoiceLine.objects.create(
            organization=self.organization,
            invoice=self.invoice,
            description="Monthly Internet Service",
            amount=Decimal("5000.00"),
        )

        self.payment = Payment.objects.create(
            organization=self.organization,
            payment_number="CMD-PAY-001",
            service_account=self.service,
            amount=Decimal("2000.00"),
            payment_method=Payment.Method.CASH,
            received_by=self.owner,
            paid_at="2026-07-05T10:00:00Z",
        )

        PaymentAllocation.objects.create(
            organization=self.organization,
            payment=self.payment,
            invoice=self.invoice,
            amount=Decimal("2000.00"),
        )

        self.device = InventoryDevice.objects.create(
            organization=self.organization,
            asset_tag="CMD-ONT-001",
            device_type=InventoryDevice.DeviceType.ONT,
            status=InventoryDevice.Status.FAULTY,
        )

        self.notification_job = NotificationJob.objects.create(
            organization=self.organization,
            customer=self.customer,
            service_account=self.service,
            channel=NotificationJob.Channel.SMS,
            status=NotificationJob.Status.FAILED,
            event_type="COMMAND_CENTER_TEST",
            recipient=self.customer.phone,
            message="Command center notification.",
            failure_reason="Provider rejected request.",
        )

        self.provisioning_request = (
            ProvisioningRequest.objects.create(
                organization=self.organization,
                service_account=self.service,
                network_assignment=self.network_assignment,
                action=ProvisioningRequest.Action.ACTIVATE,
                status=ProvisioningRequest.Status.FAILED,
                error_message=(
                    "Command Center provisioning test failure."
                ),
            )
        )

        AuditLog.objects.create(
            organization=self.organization,
            actor=self.owner,
            action="COMMAND_CENTER_TEST_EVENT",
            resource_type="ServiceAccount",
            resource_id=str(self.service.id),
            metadata={
                "service_number": self.service.service_number,
            },
        )

        other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-CMD-CUST",
            first_name="Other",
            last_name="Customer",
            phone="03007770002",
            address_line="Other Street",
            city="Karachi",
        )

        other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Other Fiber",
            code="OTHER-CMD-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="6000.00",
        )

        other_service = ServiceAccount.objects.create(
            organization=self.other_organization,
            service_number="OTHER-CMD-SRV",
            customer=other_customer,
            internet_package=other_package,
            status=ServiceAccount.Status.ACTIVE,
        )

        AuditLog.objects.create(
            organization=self.other_organization,
            actor=self.other_owner,
            action="OTHER_TENANT_EVENT",
            resource_type="ServiceAccount",
            resource_id=str(other_service.id),
            metadata={},
        )

        self.client = APIClient()

    def authenticate(
        self,
        *,
        user=None,
        organization=None,
    ):
        user = user or self.owner
        organization = organization or self.organization

        access_token = AccessToken.for_user(user)
        access_token["organization_id"] = str(
            organization.id
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {str(access_token)}"
            )
        )

    def test_command_center_summary_api(self):
        self.authenticate()

        response = self.client.get(
            "/api/v1/command-center/summary/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["total_customers"], 1)
        self.assertEqual(response.data["active_customers"], 1)

        self.assertEqual(response.data["total_services"], 1)
        self.assertEqual(response.data["active_services"], 1)

        self.assertEqual(
            response.data["total_inventory_devices"],
            1,
        )
        self.assertEqual(response.data["faulty_devices"], 1)

        self.assertEqual(response.data["total_invoices"], 1)
        self.assertEqual(
            response.data["partially_paid_invoices"],
            1,
        )

        self.assertEqual(
            response.data["invoiced_amount"],
            "5000.00",
        )
        self.assertEqual(
            response.data["collected_amount"],
            "2000.00",
        )
        self.assertEqual(
            response.data["outstanding_amount"],
            "3000.00",
        )

        self.assertEqual(
            response.data["failed_provisioning_requests"],
            1,
        )
        self.assertEqual(
            response.data["failed_notifications"],
            1,
        )

    def test_command_center_summary_is_tenant_scoped(self):
        self.authenticate(
            user=self.other_owner,
            organization=self.other_organization,
        )

        response = self.client.get(
            "/api/v1/command-center/summary/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["total_customers"], 1)
        self.assertEqual(response.data["total_services"], 1)
        self.assertEqual(response.data["total_invoices"], 0)
        self.assertEqual(
            response.data["failed_notifications"],
            0,
        )

    def test_operational_alerts_api(self):
        self.authenticate()

        response = self.client.get(
            "/api/v1/command-center/alerts/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        alert_types = {
            alert["alert_type"]
            for alert in response.data
        }

        self.assertIn(
            "PROVISIONING_FAILED",
            alert_types,
        )
        self.assertIn(
            "INVENTORY_DEVICE_ATTENTION",
            alert_types,
        )
        self.assertIn(
            "NOTIFICATION_FAILED",
            alert_types,
        )

    def test_operational_alerts_are_tenant_scoped(self):
        self.authenticate(
            user=self.other_owner,
            organization=self.other_organization,
        )

        response = self.client.get(
            "/api/v1/command-center/alerts/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data, [])

    def test_priority_queues_api(self):
        self.authenticate()

        response = self.client.get(
            "/api/v1/command-center/priority-queues/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data["failed_notifications"]),
            1,
        )
        self.assertEqual(
            len(response.data["inventory_attention"]),
            1,
        )

        self.assertEqual(
            len(response.data["pending_provisioning"]),
            0,
        )

    def test_recent_operational_activity_api(self):
        self.authenticate()

        response = self.client.get(
            "/api/v1/command-center/recent-activity/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        actions = [
            activity["action"]
            for activity in response.data
        ]

        self.assertIn(
            "COMMAND_CENTER_TEST_EVENT",
            actions,
        )
        self.assertNotIn(
            "OTHER_TENANT_EVENT",
            actions,
        )

    def test_recent_operational_activity_is_tenant_scoped(self):
        self.authenticate(
            user=self.other_owner,
            organization=self.other_organization,
        )

        response = self.client.get(
            "/api/v1/command-center/recent-activity/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        actions = [
            activity["action"]
            for activity in response.data
        ]

        self.assertIn(
            "OTHER_TENANT_EVENT",
            actions,
        )
        self.assertNotIn(
            "COMMAND_CENTER_TEST_EVENT",
            actions,
        )

    @patch(
        "command_center.views.ask_operations_copilot"
    )
    def test_operations_copilot_returns_grounded_answer(
        self,
        mock_ask_operations_copilot,
    ):
        self.authenticate()

        mock_ask_operations_copilot.return_value = CopilotAnswer(
            answer=(
                "One partially paid invoice requires "
                "collections attention."
            ),
            generated_at=timezone.now(),
            provider="OPENAI",
            model="gpt-5-mini",
        )

        response = self.client.post(
            "/api/v1/command-center/copilot/ask/",
            {
                "question": "What requires my attention?",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["provider"],
            "OPENAI",
        )

        mock_ask_operations_copilot.assert_called_once_with(
            organization=self.organization,
            question="What requires my attention?",
        )

    def test_operations_copilot_rejects_blank_question(self):
        self.authenticate()

        response = self.client.post(
            "/api/v1/command-center/copilot/ask/",
            {
                "question": "",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch(
        "command_center.views.ask_operations_copilot"
    )
    def test_operations_copilot_uses_request_tenant(
        self,
        mock_ask_operations_copilot,
    ):
        self.authenticate()

        mock_ask_operations_copilot.return_value = CopilotAnswer(
            answer="Tenant scoped answer.",
            generated_at=timezone.now(),
            provider="OPENAI",
            model="gpt-5-mini",
        )

        response = self.client.post(
            "/api/v1/command-center/copilot/ask/",
            {
                "question": "Summarize operations.",
                "organization": "UNTRUSTED-TENANT",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mock_ask_operations_copilot.assert_called_once_with(
            organization=self.organization,
            question="Summarize operations.",
        )

    def test_unauthenticated_command_center_is_blocked(self):
        endpoints = [
            "/api/v1/command-center/summary/",
            "/api/v1/command-center/alerts/",
            "/api/v1/command-center/priority-queues/",
            "/api/v1/command-center/recent-activity/",
            "/api/v1/command-center/copilot/ask/",
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)

            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
            )