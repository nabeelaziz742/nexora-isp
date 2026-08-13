from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from inventory.models import (
    DeviceAssignment,
    InventoryDevice,
)

from customers.models import (
    BillingProfile,
    Customer,
    InternetPackage,
    NotificationPreference,
    ServiceAccount,
)
from customers.services import (
    CustomerActivationError,
    activate_customer_service,
)
from network.models import (
    NetworkAssignment,
    NetworkNode,
    ProvisioningRequest,
)
from network.services import NetworkAssignmentError
from tenancy.models import (
    AuditLog,
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class CustomerActivationTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Activation ISP",
            code="ACTIVATION-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other ISP",
            code="OTHER-ISP",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.owner = User.objects.create_user(
            username="activation-owner",
            email="activation-owner@nexora.local",
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
            code="FIBER-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Other Fiber",
            code="OTHER-100",
            download_speed_mbps=100,
            upload_speed_mbps=50,
            monthly_price="8000.00",
        )

        self.network_node = NetworkNode.objects.create(
            organization=self.organization,
            name="Lahore Core Router",
            code="RTR-LHR-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.10.0.1",
        )

        self.other_network_node = NetworkNode.objects.create(
            organization=self.other_organization,
            name="Karachi Core Router",
            code="RTR-KHI-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.20.0.1",
        )

        self.device = InventoryDevice.objects.create(
            organization=self.organization,
            asset_tag="ACT-ONU-001",
            device_type=InventoryDevice.DeviceType.ONU,
            manufacturer="Huawei",
            model_name="HG8546M",
            serial_number="ACT-SERIAL-001",
            mac_address="AA:BB:CC:30:00:01",
        )

        self.other_device = InventoryDevice.objects.create(
            organization=self.other_organization,
            asset_tag="OTHER-ACT-ONU-001",
            device_type=InventoryDevice.DeviceType.ONU,
            serial_number="OTHER-ACT-SERIAL-001",
            mac_address="AA:BB:CC:40:00:01",
        )

    def activation_data(self):
        return {
            "internet_package_id": self.package.id,
            "network_node_id": self.network_node.id,
            "first_name": "Muhammad",
            "last_name": "Nabeel",
            "phone": "03001234567",
            "alternate_phone": "",
            "email": "customer@nexora.local",
            "address_line": "Test Street 1",
            "area": "Test Area",
            "city": "Lahore",
            "network_username": "nabeel-fiber",
            "network_ip_address": "10.10.10.2",
            "billing_day": 1,
            "due_day": 10,
            "sms_enabled": True,
            "whatsapp_enabled": True,
            "device_id": self.device.id,
            "device_assignment_notes": (
                "Installed during customer activation"
            ),
        }

    def authenticate_owner(self):
        login_response = self.client.post(
            reverse("tenant-login"),
            {
                "email": self.owner.email,
                "password": "StrongTestPassword123!",
                "organization_code": self.organization.code,
            },
            format="json",
        )

        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {login_response.data['access']}"
            )
        )

    def test_activation_creates_network_aware_customer_foundation(self):
        result = activate_customer_service(
            organization=self.organization,
            actor=self.owner,
            **self.activation_data(),
        )

        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(ServiceAccount.objects.count(), 1)
        self.assertEqual(BillingProfile.objects.count(), 1)
        self.assertEqual(NotificationPreference.objects.count(), 1)
        self.assertEqual(NetworkAssignment.objects.count(), 1)
        self.assertEqual(ProvisioningRequest.objects.count(), 1)
        self.assertEqual(AuditLog.objects.count(), 2)

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="INVENTORY_DEVICE_ASSIGNED",
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="CUSTOMER_SERVICE_ACTIVATED",
            ).exists()
        )

        self.assertEqual(
            result.network_assignment.network_node,
            self.network_node,
        )

        self.assertEqual(
            result.provisioning_request.action,
            ProvisioningRequest.Action.ACTIVATE,
        )

        self.assertEqual(
            result.provisioning_request.status,
            ProvisioningRequest.Status.PENDING,
        )

    def test_cross_tenant_package_is_rejected(self):
        data = self.activation_data()
        data["internet_package_id"] = self.other_package.id

        with self.assertRaises(CustomerActivationError):
            activate_customer_service(
                organization=self.organization,
                actor=self.owner,
                **data,
            )

        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)

    def test_cross_tenant_network_node_is_rejected_and_rolled_back(self):
        data = self.activation_data()
        data["network_node_id"] = self.other_network_node.id

        with self.assertRaises(CustomerActivationError):
            activate_customer_service(
                organization=self.organization,
                actor=self.owner,
                **data,
            )

        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)
        self.assertEqual(NetworkAssignment.objects.count(), 0)
        self.assertEqual(ProvisioningRequest.objects.count(), 0)
        self.assertEqual(BillingProfile.objects.count(), 0)
        self.assertEqual(NotificationPreference.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_duplicate_phone_is_rejected_per_organization(self):
        data = self.activation_data()

        activate_customer_service(
            organization=self.organization,
            actor=self.owner,
            **data,
        )

        with self.assertRaises(CustomerActivationError):
            activate_customer_service(
                organization=self.organization,
                actor=self.owner,
                **data,
            )

        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(ServiceAccount.objects.count(), 1)

    def test_activation_rolls_back_if_audit_creation_fails(self):
        data = self.activation_data()

        data["activation_metadata"] = {
            "invalid_json_value": {1, 2, 3},
        }

        with self.assertRaises(TypeError):
            activate_customer_service(
                organization=self.organization,
                actor=self.owner,
                **data,
            )

        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)
        self.assertEqual(NetworkAssignment.objects.count(), 0)
        self.assertEqual(ProvisioningRequest.objects.count(), 0)
        self.assertEqual(BillingProfile.objects.count(), 0)
        self.assertEqual(NotificationPreference.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    @patch(
        "customers.services.create_activation_network_request"
    )
    def test_activation_rolls_back_if_network_creation_fails(
        self,
        mocked_network_service,
    ):
        mocked_network_service.side_effect = NetworkAssignmentError(
            "Network assignment failed."
        )

        with self.assertRaises(CustomerActivationError):
            activate_customer_service(
                organization=self.organization,
                actor=self.owner,
                **self.activation_data(),
            )

        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)
        self.assertEqual(NetworkAssignment.objects.count(), 0)
        self.assertEqual(ProvisioningRequest.objects.count(), 0)
        self.assertEqual(BillingProfile.objects.count(), 0)
        self.assertEqual(NotificationPreference.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_owner_can_activate_customer_through_api(self):
        self.authenticate_owner()

        payload = self.activation_data()
        payload["internet_package_id"] = str(
            payload["internet_package_id"]
        )
        payload["network_node_id"] = str(
            payload["network_node_id"]
        )

        response = self.client.post(
            reverse("customer-activate"),
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["detail"],
            "CUSTOMER SERVICE ACTIVATION REQUESTED",
        )

        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(ServiceAccount.objects.count(), 1)
        self.assertEqual(NetworkAssignment.objects.count(), 1)
        self.assertEqual(ProvisioningRequest.objects.count(), 1)

        self.assertEqual(
            response.data["provisioning_request"]["status"],
            ProvisioningRequest.Status.PENDING,
        )

    def test_activation_api_requires_network_node(self):
        self.authenticate_owner()

        payload = self.activation_data()
        payload.pop("network_node_id")

        response = self.client.post(
            reverse("customer-activate"),
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(Customer.objects.count(), 0)

    def test_activation_api_rejects_cross_tenant_network_node(self):
        self.authenticate_owner()

        payload = self.activation_data()
        payload["network_node_id"] = str(
            self.other_network_node.id
        )
        payload["internet_package_id"] = str(
            self.package.id
        )

        response = self.client.post(
            reverse("customer-activate"),
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)
        self.assertEqual(NetworkAssignment.objects.count(), 0)
        self.assertEqual(ProvisioningRequest.objects.count(), 0)

    def test_customer_list_returns_only_current_tenant_customers(self):
        activate_customer_service(
            organization=self.organization,
            actor=self.owner,
            **self.activation_data(),
        )

        other_user = User.objects.create_user(
            username="other-owner",
            email="other-owner@nexora.local",
            password="StrongTestPassword123!",
        )

        other_data = self.activation_data()
        other_data["device_id"] = self.other_device.id
        other_data["internet_package_id"] = self.other_package.id
        other_data["network_node_id"] = self.other_network_node.id
        other_data["phone"] = "03111234567"

        activate_customer_service(
            organization=self.other_organization,
            actor=other_user,
            **other_data,
        )

        self.authenticate_owner()

        response = self.client.get(
            reverse("customer-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)

        self.assertEqual(
            response.data[0]["phone"],
            "03001234567",
        )

    def test_customer_detail_returns_customer_360_foundation(self):
        result = activate_customer_service(
            organization=self.organization,
            actor=self.owner,
            **self.activation_data(),
        )

        self.authenticate_owner()

        response = self.client.get(
            reverse(
                "customer-detail",
                kwargs={
                    "customer_id": result.customer.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["customer_number"],
            result.customer.customer_number,
        )

        service = response.data["service_accounts"][0]

        self.assertEqual(
            service["status"],
            ServiceAccount.Status.ACTIVE,
        )

        self.assertEqual(
            service["network_assignment"]["network_node_code"],
            self.network_node.code,
        )

    def test_customer_detail_blocks_cross_tenant_customer(self):
        other_user = User.objects.create_user(
            username="cross-tenant-owner",
            email="cross-tenant-owner@nexora.local",
            password="StrongTestPassword123!",
        )

        other_data = self.activation_data()
        other_data["device_id"] = self.other_device.id
        other_data["internet_package_id"] = self.other_package.id
        other_data["network_node_id"] = self.other_network_node.id
        other_data["phone"] = "03221234567"

        result = activate_customer_service(
            organization=self.other_organization,
            actor=other_user,
            **other_data,
        )

        self.authenticate_owner()

        response = self.client.get(
            reverse(
                "customer-detail",
                kwargs={
                    "customer_id": result.customer.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_activation_assigns_selected_inventory_device(self):
        result = activate_customer_service(
            organization=self.organization,
            actor=self.owner,
            **self.activation_data(),
        )

        self.device.refresh_from_db()

        self.assertEqual(
            DeviceAssignment.objects.count(),
            1,
        )

        self.assertEqual(
            self.device.status,
            InventoryDevice.Status.ASSIGNED,
        )

        self.assertIsNotNone(
            result.device_assignment,
        )

        self.assertEqual(
            result.device_assignment.service_account,
            result.service_account,
        )

    def test_cross_tenant_device_is_rejected_and_activation_rolls_back(
        self,
    ):
        data = self.activation_data()
        data["device_id"] = self.other_device.id

        with self.assertRaises(CustomerActivationError):
            activate_customer_service(
                organization=self.organization,
                actor=self.owner,
                **data,
            )

        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)
        self.assertEqual(NetworkAssignment.objects.count(), 0)
        self.assertEqual(ProvisioningRequest.objects.count(), 0)
        self.assertEqual(DeviceAssignment.objects.count(), 0)
        self.assertEqual(BillingProfile.objects.count(), 0)
        self.assertEqual(NotificationPreference.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

        self.device.refresh_from_db()
        self.other_device.refresh_from_db()

        self.assertEqual(
            self.device.status,
            InventoryDevice.Status.AVAILABLE,
        )

        self.assertEqual(
            self.other_device.status,
            InventoryDevice.Status.AVAILABLE,
        )

    def test_activation_api_returns_device_assignment(self):
        self.authenticate_owner()

        payload = self.activation_data()
        payload["internet_package_id"] = str(
            payload["internet_package_id"]
        )
        payload["network_node_id"] = str(
            payload["network_node_id"]
        )
        payload["device_id"] = str(
            payload["device_id"]
        )

        response = self.client.post(
            reverse("customer-activate"),
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertIsNotNone(
            response.data["device_assignment"],
        )

        self.assertEqual(
            response.data["device_assignment"]["asset_tag"],
            self.device.asset_tag,
        )

        self.assertEqual(
            response.data["device_assignment"]["device_status"],
            InventoryDevice.Status.ASSIGNED,
        )