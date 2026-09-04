from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from billing.models import Invoice
from inventory.models import (
    DeviceAssignment,
    InventoryDevice,
)

from customers.models import (
    BillingProfile,
    Customer,
    Dealer,
    FeasibilityAssessment,
    Inquiry,
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
            "device_assignment_notes": "Installed during customer activation",
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
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
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
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(AuditLog.objects.count(), 4)
        self.assertTrue(AuditLog.objects.filter(organization=self.organization, action="INVENTORY_DEVICE_ASSIGNED").exists())
        self.assertTrue(AuditLog.objects.filter(organization=self.organization, action="CUSTOMER_SERVICE_ACTIVATED").exists())
        self.assertTrue(AuditLog.objects.filter(organization=self.organization, action="BILLING_INVOICE_GENERATED").exists())
        self.assertEqual(result.network_assignment.network_node, self.network_node)
        self.assertEqual(result.provisioning_request.action, ProvisioningRequest.Action.ACTIVATE)
        self.assertEqual(result.provisioning_request.status, ProvisioningRequest.Status.PENDING)

    def test_cross_tenant_package_is_rejected(self):
        data = self.activation_data()
        data["internet_package_id"] = self.other_package.id
        with self.assertRaises(CustomerActivationError):
            activate_customer_service(organization=self.organization, actor=self.owner, **data)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)

    def test_cross_tenant_network_node_is_rejected_and_rolled_back(self):
        data = self.activation_data()
        data["network_node_id"] = self.other_network_node.id
        with self.assertRaises(CustomerActivationError):
            activate_customer_service(organization=self.organization, actor=self.owner, **data)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)
        self.assertEqual(NetworkAssignment.objects.count(), 0)
        self.assertEqual(ProvisioningRequest.objects.count(), 0)
        self.assertEqual(BillingProfile.objects.count(), 0)
        self.assertEqual(NotificationPreference.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_duplicate_phone_is_rejected_per_organization(self):
        data = self.activation_data()
        activate_customer_service(organization=self.organization, actor=self.owner, **data)
        with self.assertRaises(CustomerActivationError):
            activate_customer_service(organization=self.organization, actor=self.owner, **data)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(ServiceAccount.objects.count(), 1)

    def test_activation_rolls_back_if_audit_creation_fails(self):
        data = self.activation_data()
        data["activation_metadata"] = {"invalid_json_value": {1, 2, 3}}
        with self.assertRaises(TypeError):
            activate_customer_service(organization=self.organization, actor=self.owner, **data)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)
        self.assertEqual(NetworkAssignment.objects.count(), 0)
        self.assertEqual(ProvisioningRequest.objects.count(), 0)
        self.assertEqual(BillingProfile.objects.count(), 0)
        self.assertEqual(NotificationPreference.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    @patch("customers.services.create_activation_network_request")
    def test_activation_rolls_back_if_network_creation_fails(self, mocked_network_service):
        mocked_network_service.side_effect = NetworkAssignmentError("Network assignment failed.")
        with self.assertRaises(CustomerActivationError):
            activate_customer_service(organization=self.organization, actor=self.owner, **self.activation_data())
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)
        self.assertEqual(NetworkAssignment.objects.count(), 0)
        self.assertEqual(ProvisioningRequest.objects.count(), 0)
        self.assertEqual(BillingProfile.objects.count(), 0)
        self.assertEqual(NotificationPreference.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_owner_can_activate_customer_through_api(self):
        self.authenticate_owner()
        payload = self.activation_data()
        payload["internet_package_id"] = str(payload["internet_package_id"])
        payload["network_node_id"] = str(payload["network_node_id"])
        response = self.client.post(reverse("customer-activate"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["detail"], "CUSTOMER SERVICE ACTIVATION REQUESTED")
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(ServiceAccount.objects.count(), 1)
        self.assertEqual(NetworkAssignment.objects.count(), 1)
        self.assertEqual(ProvisioningRequest.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(response.data["provisioning_request"]["status"], ProvisioningRequest.Status.PENDING)

    def test_activation_api_requires_network_node(self):
        self.authenticate_owner()
        payload = self.activation_data()
        payload.pop("network_node_id")
        response = self.client.post(reverse("customer-activate"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Customer.objects.count(), 0)

    def test_activation_api_rejects_cross_tenant_network_node(self):
        self.authenticate_owner()
        payload = self.activation_data()
        payload["network_node_id"] = str(self.other_network_node.id)
        payload["internet_package_id"] = str(self.package.id)
        response = self.client.post(reverse("customer-activate"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)
        self.assertEqual(NetworkAssignment.objects.count(), 0)
        self.assertEqual(ProvisioningRequest.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_customer_list_returns_only_current_tenant_customers(self):
        activate_customer_service(organization=self.organization, actor=self.owner, **self.activation_data())
        other_user = User.objects.create_user(username="other-owner", email="other-owner@nexora.local", password="StrongTestPassword123!")
        other_data = self.activation_data()
        other_data["device_id"] = self.other_device.id
        other_data["internet_package_id"] = self.other_package.id
        other_data["network_node_id"] = self.other_network_node.id
        other_data["phone"] = "03111234567"
        activate_customer_service(organization=self.other_organization, actor=other_user, **other_data)
        self.authenticate_owner()
        response = self.client.get(reverse("customer-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["phone"], "03001234567")

    def test_customer_detail_returns_customer_360_foundation(self):
        result = activate_customer_service(organization=self.organization, actor=self.owner, **self.activation_data())
        self.authenticate_owner()
        response = self.client.get(reverse("customer-detail", kwargs={"customer_id": result.customer.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["customer_number"], result.customer.customer_number)
        service = response.data["service_accounts"][0]
        self.assertEqual(service["status"], ServiceAccount.Status.ACTIVE)
        self.assertEqual(service["network_assignment"]["network_node_code"], self.network_node.code)

    def test_customer_detail_blocks_cross_tenant_customer(self):
        other_user = User.objects.create_user(username="cross-tenant-owner", email="cross-tenant-owner@nexora.local", password="StrongTestPassword123!")
        other_data = self.activation_data()
        other_data["device_id"] = self.other_device.id
        other_data["internet_package_id"] = self.other_package.id
        other_data["network_node_id"] = self.other_network_node.id
        other_data["phone"] = "03221234567"
        result = activate_customer_service(organization=self.other_organization, actor=other_user, **other_data)
        self.authenticate_owner()
        response = self.client.get(reverse("customer-detail", kwargs={"customer_id": result.customer.id}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_activation_assigns_selected_inventory_device(self):
        result = activate_customer_service(organization=self.organization, actor=self.owner, **self.activation_data())
        self.device.refresh_from_db()
        self.assertEqual(DeviceAssignment.objects.count(), 1)
        self.assertEqual(self.device.status, InventoryDevice.Status.ASSIGNED)
        self.assertIsNotNone(result.device_assignment)
        self.assertEqual(result.device_assignment.service_account, result.service_account)

    def test_cross_tenant_device_is_rejected_and_activation_rolls_back(self):
        data = self.activation_data()
        data["device_id"] = self.other_device.id
        with self.assertRaises(CustomerActivationError):
            activate_customer_service(organization=self.organization, actor=self.owner, **data)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(ServiceAccount.objects.count(), 0)
        self.assertEqual(NetworkAssignment.objects.count(), 0)
        self.assertEqual(ProvisioningRequest.objects.count(), 0)
        self.assertEqual(DeviceAssignment.objects.count(), 0)
        self.assertEqual(BillingProfile.objects.count(), 0)
        self.assertEqual(NotificationPreference.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)
        self.device.refresh_from_db()
        self.other_device.refresh_from_db()
        self.assertEqual(self.device.status, InventoryDevice.Status.AVAILABLE)
        self.assertEqual(self.other_device.status, InventoryDevice.Status.AVAILABLE)

    def test_activation_api_returns_device_assignment(self):
        self.authenticate_owner()
        payload = self.activation_data()
        payload["internet_package_id"] = str(payload["internet_package_id"])
        payload["network_node_id"] = str(payload["network_node_id"])
        payload["device_id"] = str(payload["device_id"])
        response = self.client.post(reverse("customer-activate"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["device_assignment"])
        self.assertEqual(response.data["device_assignment"]["asset_tag"], self.device.asset_tag)
        self.assertEqual(response.data["device_assignment"]["device_status"], InventoryDevice.Status.ASSIGNED)


class Batch3GeographicAndPackageTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Alpha Telecom",
            code="ALPHA-TEL",
            city="Islamabad",
            timezone="Asia/Karachi",
            currency="PKR",
        )
        self.other_organization = Organization.objects.create(
            name="Beta Telecom",
            code="BETA-TEL",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )
        self.owner = User.objects.create_user(
            username="alpha-owner@nexora.local",
            email="alpha-owner@nexora.local",
            password="StrongPassword123!",
        )
        self.staff = User.objects.create_user(
            username="alpha-staff@nexora.local",
            email="alpha-staff@nexora.local",
            password="StrongPassword123!",
        )
        self.other_owner = User.objects.create_user(
            username="beta-owner@nexora.local",
            email="beta-owner@nexora.local",
            password="StrongPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.staff,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

    def auth(self, user, org):
        login_res = self.client.post(
            reverse("tenant-login"),
            {
                "organization_code": org.code,
                "email": user.email,
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # ==================== COUNTRY TESTS ====================
    def test_country_crud_and_tenant_isolation(self):
        self.auth(self.owner, self.organization)

        # Create
        res = self.client.post(
            reverse("country-list-create"),
            {"name": "Pakistan", "code": "PK"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        country_id = res.data["id"]

        # List
        res = self.client.get(reverse("country-list-create"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], "Pakistan")

        # Update
        res = self.client.put(
            reverse("country-detail", kwargs={"country_id": country_id}),
            {"name": "Islamic Republic of Pakistan", "code": "PK"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Islamic Republic of Pakistan")

        # Toggle Status
        res = self.client.patch(
            reverse("country-status-toggle", kwargs={"country_id": country_id})
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["is_active"])

        # Other tenant isolation check
        self.auth(self.other_owner, self.other_organization)
        res = self.client.get(reverse("country-list-create"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

        # Other tenant cannot retrieve
        res = self.client.get(reverse("country-detail", kwargs={"country_id": country_id}))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ==================== CITY & AREA TESTS ====================
    def test_city_and_area_hierarchy_with_delete_protection(self):
        self.auth(self.owner, self.organization)

        # Create Country
        c_res = self.client.post(
            reverse("country-list-create"),
            {"name": "Pakistan", "code": "PK"},
            format="json",
        )
        country_id = c_res.data["id"]

        # Create City
        city_res = self.client.post(
            reverse("city-list-create"),
            {"name": "Islamabad", "code": "ISB", "country": country_id},
            format="json",
        )
        self.assertEqual(city_res.status_code, status.HTTP_201_CREATED)
        city_id = city_res.data["id"]

        # Country cannot be deleted while city is attached
        del_c = self.client.delete(reverse("country-detail", kwargs={"country_id": country_id}))
        self.assertEqual(del_c.status_code, status.HTTP_400_BAD_REQUEST)

        # Create Area
        area_res = self.client.post(
            reverse("area-list-create"),
            {"name": "Sector F-10", "code": "F10", "postal_code": "44000", "city": city_id},
            format="json",
        )
        self.assertEqual(area_res.status_code, status.HTTP_201_CREATED)
        area_id = area_res.data["id"]

        # City cannot be deleted while area is attached
        del_city = self.client.delete(reverse("city-detail", kwargs={"city_id": city_id}))
        self.assertEqual(del_city.status_code, status.HTTP_400_BAD_REQUEST)

        # Delete Area
        del_area = self.client.delete(reverse("area-detail", kwargs={"area_id": area_id}))
        self.assertEqual(del_area.status_code, status.HTTP_204_NO_CONTENT)

        # Now City can be deleted
        del_city2 = self.client.delete(reverse("city-detail", kwargs={"city_id": city_id}))
        self.assertEqual(del_city2.status_code, status.HTTP_204_NO_CONTENT)

        # Now Country can be deleted
        del_c2 = self.client.delete(reverse("country-detail", kwargs={"country_id": country_id}))
        self.assertEqual(del_c2.status_code, status.HTTP_204_NO_CONTENT)

    # ==================== PACKAGE TESTS ====================
    def test_package_crud_and_dependency_protection(self):
        self.auth(self.owner, self.organization)

        # Create Package
        pkg_res = self.client.post(
            reverse("internet-package-list"),
            {
                "name": "Fiber Turbo 50M",
                "code": "TURBO-50",
                "description": "Ultra fast broadband with unlimited data",
                "download_speed_mbps": 50,
                "upload_speed_mbps": 50,
                "monthly_price": "4500.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(pkg_res.status_code, status.HTTP_201_CREATED)
        pkg_id = pkg_res.data["id"]
        self.assertEqual(pkg_res.data["subscribers_count"], 0)

        # Retrieve Package Detail
        detail_res = self.client.get(
            reverse("internet-package-detail", kwargs={"package_id": pkg_id})
        )
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.data["name"], "Fiber Turbo 50M")

        # Update Package
        update_res = self.client.put(
            reverse("internet-package-detail", kwargs={"package_id": pkg_id}),
            {
                "name": "Fiber Turbo 60M",
                "code": "TURBO-60",
                "description": "Upgraded speed",
                "download_speed_mbps": 60,
                "upload_speed_mbps": 60,
                "monthly_price": "5000.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        self.assertEqual(update_res.data["name"], "Fiber Turbo 60M")
        self.assertEqual(update_res.data["download_speed_mbps"], 60)

        # Toggle Status
        toggle_res = self.client.patch(
            reverse("internet-package-status-toggle", kwargs={"package_id": pkg_id})
        )
        self.assertEqual(toggle_res.status_code, status.HTTP_200_OK)
        self.assertFalse(toggle_res.data["is_active"])

        # Filter active vs inactive
        active_list = self.client.get(reverse("internet-package-list") + "?status=active")
        self.assertEqual(len(active_list.data), 0)

        inactive_list = self.client.get(reverse("internet-package-list") + "?status=inactive")
        self.assertEqual(len(inactive_list.data), 1)

        # Safe Delete when no subscribers exist
        del_res = self.client.delete(
            reverse("internet-package-detail", kwargs={"package_id": pkg_id})
        )
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)


class CustomerManagementAndLifecycleTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Apex Networks",
            code="APEX-NET",
            city="Islamabad",
            timezone="Asia/Karachi",
            currency="PKR",
        )
        self.other_organization = Organization.objects.create(
            name="Rival Networks",
            code="RIVAL-NET",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )
        self.owner = User.objects.create_user(
            username="apex-owner@nexora.local",
            email="apex-owner@nexora.local",
            password="StrongPassword123!",
        )
        self.other_owner = User.objects.create_user(
            username="rival-owner@nexora.local",
            email="rival-owner@nexora.local",
            password="StrongPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Apex Fiber 100",
            code="APEX-100",
            download_speed_mbps=100,
            upload_speed_mbps=100,
            monthly_price="7500.00",
        )
        self.network_node = NetworkNode.objects.create(
            organization=self.organization,
            name="Islamabad Core Router 1",
            code="RTR-ISB-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="192.168.1.1",
        )
        self.device = InventoryDevice.objects.create(
            organization=self.organization,
            asset_tag="APEX-DEV-001",
            device_type=InventoryDevice.DeviceType.ONU,
            serial_number="APEX-SN-001",
            mac_address="AA:BB:CC:11:22:33",
        )

    def auth(self, user, org):
        login_res = self.client.post(
            reverse("tenant-login"),
            {
                "organization_code": org.code,
                "email": user.email,
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_res.data['access']}"
        )

    def _create_customer(self, phone="03001112233", first_name="Ahmed", city="Islamabad", area="F-10"):
        return activate_customer_service(
            organization=self.organization,
            actor=self.owner,
            internet_package_id=self.package.id,
            network_node_id=self.network_node.id,
            first_name=first_name,
            last_name="Khan",
            phone=phone,
            alternate_phone="03009998877",
            email=f"{first_name.lower()}@nexora.local",
            address_line="House 123, Street 45",
            area=area,
            city=city,
            billing_day=1,
            due_day=10,
            sms_enabled=True,
            whatsapp_enabled=True,
        )

    def test_owner_can_update_customer_details_via_put_and_patch(self):
        result = self._create_customer()
        self.auth(self.owner, self.organization)

        # PATCH partial update
        patch_res = self.client.patch(
            reverse("customer-detail", kwargs={"customer_id": result.customer.id}),
            {
                "first_name": "Ahmed Raza",
                "email": "ahmed.raza@nexora.local",
                "address_line": "Updated Street 99",
                "area": "F-11/1",
                "whatsapp_enabled": False,
            },
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["first_name"], "Ahmed Raza")
        self.assertEqual(patch_res.data["full_name"], "Ahmed Raza Khan")
        self.assertEqual(patch_res.data["email"], "ahmed.raza@nexora.local")
        self.assertEqual(patch_res.data["address_line"], "Updated Street 99")
        self.assertEqual(patch_res.data["area"], "F-11/1")
        self.assertFalse(patch_res.data["notification_preference"]["whatsapp_enabled"])
        self.assertTrue(patch_res.data["notification_preference"]["sms_enabled"])

        # Audit log verified
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="CUSTOMER_UPDATED",
                resource_id=result.customer.id,
            ).exists()
        )

    def test_customer_update_duplicate_phone_in_same_tenant_fails(self):
        res1 = self._create_customer(phone="03001111111", first_name="User1")
        res2 = self._create_customer(phone="03002222222", first_name="User2")
        self.auth(self.owner, self.organization)

        # Try to update user2 phone to user1's phone
        patch_res = self.client.patch(
            reverse("customer-detail", kwargs={"customer_id": res2.customer.id}),
            {"phone": "03001111111"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", patch_res.data)

    def test_cross_tenant_customer_update_returns_404(self):
        result = self._create_customer()
        self.auth(self.other_owner, self.other_organization)

        patch_res = self.client.patch(
            reverse("customer-detail", kwargs={"customer_id": result.customer.id}),
            {"first_name": "Hacked Name"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_404_NOT_FOUND)
        result.customer.refresh_from_db()
        self.assertEqual(result.customer.first_name, "Ahmed")

    def test_customer_status_toggle(self):
        result = self._create_customer()
        self.auth(self.owner, self.organization)

        # Toggle to inactive
        toggle_res = self.client.patch(
            reverse("customer-status-toggle", kwargs={"customer_id": result.customer.id})
        )
        self.assertEqual(toggle_res.status_code, status.HTTP_200_OK)
        self.assertFalse(toggle_res.data["is_active"])

        # Toggle back to active
        toggle_res2 = self.client.patch(
            reverse("customer-status-toggle", kwargs={"customer_id": result.customer.id})
        )
        self.assertEqual(toggle_res2.status_code, status.HTTP_200_OK)
        self.assertTrue(toggle_res2.data["is_active"])

    def test_customer_list_filters_by_city_area_package_status(self):
        res1 = self._create_customer(phone="03001110001", first_name="Ali", city="Islamabad", area="F-10")
        res2 = self._create_customer(phone="03001110002", first_name="Bilal", city="Rawalpindi", area="Saddar")
        self.auth(self.owner, self.organization)

        # Filter by city
        city_res = self.client.get(reverse("customer-list") + "?city=Islamabad")
        self.assertEqual(city_res.status_code, status.HTTP_200_OK)
        city_items = city_res.data.get("results", city_res.data) if isinstance(city_res.data, dict) else city_res.data
        self.assertEqual(len(city_items), 1)
        self.assertEqual(city_items[0]["full_name"], "Ali Khan")

        # Filter by area
        area_res = self.client.get(reverse("customer-list") + "?area=Saddar")
        self.assertEqual(area_res.status_code, status.HTTP_200_OK)
        area_items = area_res.data.get("results", area_res.data) if isinstance(area_res.data, dict) else area_res.data
        self.assertEqual(len(area_items), 1)
        self.assertEqual(area_items[0]["full_name"], "Bilal Khan")

        # Filter by package
        pkg_res = self.client.get(reverse("customer-list") + f"?package_id={self.package.id}")
        self.assertEqual(pkg_res.status_code, status.HTTP_200_OK)
        pkg_items = pkg_res.data.get("results", pkg_res.data) if isinstance(pkg_res.data, dict) else pkg_res.data
        self.assertEqual(len(pkg_items), 2)

        # Filter by status
        status_res = self.client.get(reverse("customer-list") + "?status=ACTIVE")
        self.assertEqual(status_res.status_code, status.HTTP_200_OK)
        status_items = status_res.data.get("results", status_res.data) if isinstance(status_res.data, dict) else status_res.data
        self.assertEqual(len(status_items), 2)


class InquiryAndFeasibilityLifecycleTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Alpha Fiber Net",
            code="ALPHA",
            is_active=True,
        )
        self.other_organization = Organization.objects.create(
            name="Beta Telecom",
            code="BETA",
            is_active=True,
        )
        self.owner = User.objects.create_user(
            username="alpha_owner@nexora.local",
            password="StrongPassword123!",
            email="alpha_owner@nexora.local",
        )
        self.other_owner = User.objects.create_user(
            username="beta_owner@nexora.local",
            password="StrongPassword123!",
            email="beta_owner@nexora.local",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Super Fiber 50",
            code="SF-50",
            download_speed_mbps=50,
            upload_speed_mbps=50,
            monthly_price=3500.00,
            is_active=True,
        )

    def auth(self, user, org):
        login_res = self.client.post(
            reverse("tenant-login"),
            {
                "organization_code": org.code,
                "email": user.email,
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_res.data['access']}"
        )

    def test_inquiry_crud_and_status_transition(self):
        self.auth(self.owner, self.organization)

        # 1. Create Inquiry
        create_res = self.client.post(
            reverse("inquiry-list-create"),
            {
                "full_name": "Tariq Mehmood",
                "phone": "03129998877",
                "email": "tariq@example.com",
                "address_line": "House 42, Street 7",
                "city": "Islamabad",
                "area": "G-11",
                "preferred_package": str(self.package.id),
                "connection_type": "FIBER",
                "source": "WALK_IN",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        inquiry_id = create_res.data["id"]
        self.assertTrue(create_res.data["inquiry_number"].startswith("ALPHA-INQ-"))
        self.assertEqual(create_res.data["status"], "NEW")

        # 2. List & Filter
        list_res = self.client.get(reverse("inquiry-list-create") + "?city=Islamabad")
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data), 1)

        # 3. Status Transition to CONTACTED
        trans_res = self.client.post(
            reverse("inquiry-status-transition", kwargs={"inquiry_id": inquiry_id}),
            {"status": "CONTACTED", "notes": "Called customer, interested in 50Mbps plan"},
            format="json",
        )
        self.assertEqual(trans_res.status_code, status.HTTP_200_OK)
        self.assertEqual(trans_res.data["status"], "CONTACTED")

    def test_feasibility_assessment_workflow(self):
        self.auth(self.owner, self.organization)

        # Create Inquiry
        inq = Inquiry.objects.create(
            organization=self.organization,
            inquiry_number="ALPHA-INQ-00001",
            full_name="Kashif Ali",
            phone="03335554433",
            address_line="Flat 2B, Plaza 9",
            city="Rawalpindi",
            area="Bahria Town",
            preferred_package=self.package,
        )

        # Create Feasibility Check
        fsb_res = self.client.post(
            reverse("feasibility-list-create"),
            {
                "inquiry": str(inq.id),
                "address_line": inq.address_line,
                "city": inq.city,
                "area": inq.area,
                "package": str(self.package.id),
                "connection_type": "FIBER",
                "status": "PENDING",
            },
            format="json",
        )
        self.assertEqual(fsb_res.status_code, status.HTTP_201_CREATED)
        fsb_id = fsb_res.data["id"]
        inq.refresh_from_db()
        self.assertEqual(inq.status, "FEASIBILITY_PENDING")

        # Test Not Feasible without reason -> Must Fail
        bad_update = self.client.patch(
            reverse("feasibility-detail", kwargs={"assessment_id": fsb_id}),
            {"status": "NOT_FEASIBLE", "not_feasible_reason": ""},
            format="json",
        )
        self.assertEqual(bad_update.status_code, status.HTTP_400_BAD_REQUEST)

        # Test Not Feasible with valid reason
        good_update = self.client.patch(
            reverse("feasibility-detail", kwargs={"assessment_id": fsb_id}),
            {
                "status": "NOT_FEASIBLE",
                "not_feasible_reason": "NO_COVERAGE",
                "not_feasible_details": "DP is 800m away, no direct optical drop possible.",
            },
            format="json",
        )
        self.assertEqual(good_update.status_code, status.HTTP_200_OK)
        inq.refresh_from_db()
        self.assertEqual(inq.status, "NOT_FEASIBLE")

        # Update to FEASIBLE
        feasible_update = self.client.patch(
            reverse("feasibility-detail", kwargs={"assessment_id": fsb_id}),
            {"status": "FEASIBLE", "remarks": "FAT installed, port 4 is available"},
            format="json",
        )
        self.assertEqual(feasible_update.status_code, status.HTTP_200_OK)
        inq.refresh_from_db()
        self.assertEqual(inq.status, "FEASIBLE")

    def test_inquiry_conversion_to_customer(self):
        self.auth(self.owner, self.organization)

        inq = Inquiry.objects.create(
            organization=self.organization,
            inquiry_number="ALPHA-INQ-00005",
            full_name="Hamza Saeed",
            phone="03451234567",
            email="hamza@gmail.local",
            address_line="Sector H-12, NUST",
            city="Islamabad",
            area="H-12",
            preferred_package=self.package,
            status=Inquiry.Status.FEASIBLE,
        )

        # Convert inquiry
        convert_res = self.client.post(
            reverse("inquiry-convert", kwargs={"inquiry_id": inq.id}),
            {
                "internet_package_id": str(self.package.id),
                "billing_day": 1,
                "due_day": 10,
            },
            format="json",
        )
        self.assertEqual(convert_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(convert_res.data["status"], "CONVERTED")

        # Verify Customer and Service Account created
        customer_id = convert_res.data["customer_id"]
        customer = Customer.objects.get(id=customer_id)
        self.assertEqual(customer.phone, "03451234567")
        self.assertEqual(customer.first_name, "Hamza")
        self.assertEqual(customer.last_name, "Saeed")
        self.assertEqual(customer.service_accounts.count(), 1)

        # Verify Inquiry updated and preserved
        inq.refresh_from_db()
        self.assertEqual(inq.status, "CONVERTED")
        self.assertEqual(inq.converted_customer_id, customer.id)
        self.assertIsNotNone(inq.converted_at)

        # Attempt converting again -> Must Fail
        repeat_convert = self.client.post(
            reverse("inquiry-convert", kwargs={"inquiry_id": inq.id}),
            {"internet_package_id": str(self.package.id)},
            format="json",
        )
        self.assertEqual(repeat_convert.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_tenant_inquiry_isolation(self):
        # Create inquiry in Beta Telecom
        beta_inq = Inquiry.objects.create(
            organization=self.other_organization,
            inquiry_number="BETA-INQ-00001",
            full_name="Secret Lead",
            phone="03009990000",
            address_line="Lahore Cantt",
            city="Lahore",
        )

        # Alpha Owner tries to view Beta inquiry -> 404
        self.auth(self.owner, self.organization)
        res = self.client.get(reverse("inquiry-detail", kwargs={"inquiry_id": beta_inq.id}))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class DealerManagementTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Alpha Fiber Net",
            code="ALPHA",
            is_active=True,
        )
        self.other_organization = Organization.objects.create(
            name="Beta Telecom",
            code="BETA",
            is_active=True,
        )
        self.owner = User.objects.create_user(
            username="alpha_owner@nexora.local",
            password="StrongPassword123!",
            email="alpha_owner@nexora.local",
        )
        self.other_owner = User.objects.create_user(
            username="beta_owner@nexora.local",
            password="StrongPassword123!",
            email="beta_owner@nexora.local",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Super Fiber 50",
            code="SF-50",
            download_speed_mbps=50,
            upload_speed_mbps=50,
            monthly_price=3500.00,
            is_active=True,
        )

    def auth(self, user, org):
        login_res = self.client.post(
            reverse("tenant-login"),
            {
                "organization_code": org.code,
                "email": user.email,
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_res.data['access']}"
        )

    def test_dealer_crud_and_360_view(self):
        self.auth(self.owner, self.organization)

        # 1. Create Dealer
        create_res = self.client.post(
            reverse("dealer-list-create"),
            {
                "name": "Naveed Enterprise",
                "company_name": "Naveed Cable & Net",
                "phone": "03001239876",
                "city": "Rawalpindi",
                "area": "Satellite Town",
                "commission_rate_percentage": 15.00,
                "commission_type": "PERCENTAGE",
                "joining_date": "2026-01-01",
                "status": "ACTIVE",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        dealer_id = create_res.data["id"]
        self.assertTrue(create_res.data["dealer_code"].startswith("ALPHA-DLR-"))

        # 2. Add customer linked to dealer
        result = activate_customer_service(
            organization=self.organization,
            actor=self.owner,
            internet_package_id=self.package.id,
            dealer_id=dealer_id,
            first_name="Zubair",
            last_name="Khan",
            phone="03008887766",
            address_line="Street 4",
            city="Rawalpindi",
            billing_day=1,
            due_day=10,
        )
        self.assertEqual(str(result.customer.dealer_id), str(dealer_id))

        # 3. View Dealer 360
        view_360_res = self.client.get(reverse("dealer-360", kwargs={"dealer_id": dealer_id}))
        self.assertEqual(view_360_res.status_code, status.HTTP_200_OK)
        metrics = view_360_res.data["metrics"]
        self.assertEqual(metrics["total_customers"], 1)
        self.assertEqual(metrics["active_customers"], 1)
        self.assertEqual(len(view_360_res.data["customers"]), 1)

        # 4. Status Toggle
        toggle_res = self.client.patch(reverse("dealer-status-toggle", kwargs={"dealer_id": dealer_id}))
        self.assertEqual(toggle_res.status_code, status.HTTP_200_OK)
        self.assertEqual(toggle_res.data["status"], "INACTIVE")

    def test_cross_tenant_dealer_isolation(self):
        beta_dealer = Dealer.objects.create(
            organization=self.other_organization,
            dealer_code="BETA-DLR-0001",
            name="Beta Sub-ISP",
            phone="03110001122",
            joining_date="2026-01-01",
        )

        self.auth(self.owner, self.organization)
        res = self.client.get(reverse("dealer-detail", kwargs={"dealer_id": beta_dealer.id}))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)




