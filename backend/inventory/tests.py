from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import (
    Customer,
    InternetPackage,
    ServiceAccount,
)
from inventory.models import (
    DeviceAssignment,
    InventoryDevice,
)
from inventory.services import (
    InventoryCustodyError,
    assign_device_to_service,
    return_device_from_service,
)
from tenancy.models import (
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class InventoryCustodyTests(TestCase):
    def setUp(self):
        self.organization_a = Organization.objects.create(
            name="ISP A",
            code="INV-ISP-A",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.organization_b = Organization.objects.create(
            name="ISP B",
            code="INV-ISP-B",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.actor = User.objects.create_user(
            username="inventory-owner",
            email="inventory-owner@nexora.local",
            password="StrongTestPassword123!",
        )

        self.customer_a = Customer.objects.create(
            organization=self.organization_a,
            customer_number="INV-CUST-A-001",
            first_name="Ali",
            phone="03000000011",
            address_line="Address A",
            city="Lahore",
        )

        self.customer_b = Customer.objects.create(
            organization=self.organization_b,
            customer_number="INV-CUST-B-001",
            first_name="Ahmed",
            phone="03000000012",
            address_line="Address B",
            city="Karachi",
        )

        self.package_a = InternetPackage.objects.create(
            organization=self.organization_a,
            name="Fiber 20",
            code="INV-A-20",
            download_speed_mbps=20,
            upload_speed_mbps=10,
            monthly_price="2500.00",
        )

        self.package_b = InternetPackage.objects.create(
            organization=self.organization_b,
            name="Fiber 30",
            code="INV-B-30",
            download_speed_mbps=30,
            upload_speed_mbps=15,
            monthly_price="3500.00",
        )

        self.service_a = ServiceAccount.objects.create(
            organization=self.organization_a,
            service_number="INV-SRV-A-001",
            customer=self.customer_a,
            internet_package=self.package_a,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.service_b = ServiceAccount.objects.create(
            organization=self.organization_b,
            service_number="INV-SRV-B-001",
            customer=self.customer_b,
            internet_package=self.package_b,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.device_a = InventoryDevice.objects.create(
            organization=self.organization_a,
            asset_tag="ONU-A-001",
            device_type=InventoryDevice.DeviceType.ONU,
            manufacturer="Huawei",
            model_name="HG8546M",
            serial_number="SERIAL-A-001",
            mac_address="AA:BB:CC:00:00:01",
        )

        self.device_b = InventoryDevice.objects.create(
            organization=self.organization_b,
            asset_tag="ONU-B-001",
            device_type=InventoryDevice.DeviceType.ONU,
            manufacturer="Huawei",
            model_name="HG8546M",
            serial_number="SERIAL-B-001",
            mac_address="AA:BB:CC:00:00:02",
        )

    def test_device_queryset_is_tenant_scoped(self):
        devices = InventoryDevice.objects.for_organization(
            self.organization_a
        )

        self.assertEqual(devices.count(), 1)
        self.assertEqual(devices.first(), self.device_a)
        self.assertNotIn(self.device_b, devices)

    def test_available_device_can_be_assigned(self):
        result = assign_device_to_service(
            organization=self.organization_a,
            actor=self.actor,
            device_id=self.device_a.id,
            service_account_id=self.service_a.id,
        )

        self.device_a.refresh_from_db()

        self.assertEqual(
            self.device_a.status,
            InventoryDevice.Status.ASSIGNED,
        )
        self.assertEqual(
            result.assignment.service_account,
            self.service_a,
        )
        self.assertIsNone(result.assignment.returned_at)

    def test_cross_tenant_service_assignment_is_blocked(self):
        with self.assertRaises(InventoryCustodyError):
            assign_device_to_service(
                organization=self.organization_a,
                actor=self.actor,
                device_id=self.device_a.id,
                service_account_id=self.service_b.id,
            )

        self.device_a.refresh_from_db()

        self.assertEqual(
            self.device_a.status,
            InventoryDevice.Status.AVAILABLE,
        )

        self.assertFalse(
            DeviceAssignment.objects.filter(
                device=self.device_a
            ).exists()
        )

    def test_cross_tenant_device_assignment_is_blocked(self):
        with self.assertRaises(InventoryCustodyError):
            assign_device_to_service(
                organization=self.organization_a,
                actor=self.actor,
                device_id=self.device_b.id,
                service_account_id=self.service_a.id,
            )

    def test_assigned_device_cannot_be_assigned_twice(self):
        assign_device_to_service(
            organization=self.organization_a,
            actor=self.actor,
            device_id=self.device_a.id,
            service_account_id=self.service_a.id,
        )

        with self.assertRaises(InventoryCustodyError):
            assign_device_to_service(
                organization=self.organization_a,
                actor=self.actor,
                device_id=self.device_a.id,
                service_account_id=self.service_a.id,
            )

    def test_good_return_makes_device_available(self):
        assignment_result = assign_device_to_service(
            organization=self.organization_a,
            actor=self.actor,
            device_id=self.device_a.id,
            service_account_id=self.service_a.id,
        )

        result = return_device_from_service(
            organization=self.organization_a,
            actor=self.actor,
            assignment_id=assignment_result.assignment.id,
            return_condition=(
                DeviceAssignment.ReturnCondition.GOOD
            ),
        )

        result.device.refresh_from_db()
        result.assignment.refresh_from_db()

        self.assertEqual(
            result.device.status,
            InventoryDevice.Status.AVAILABLE,
        )
        self.assertIsNotNone(result.assignment.returned_at)

    def test_faulty_return_marks_device_faulty(self):
        assignment_result = assign_device_to_service(
            organization=self.organization_a,
            actor=self.actor,
            device_id=self.device_a.id,
            service_account_id=self.service_a.id,
        )

        result = return_device_from_service(
            organization=self.organization_a,
            actor=self.actor,
            assignment_id=assignment_result.assignment.id,
            return_condition=(
                DeviceAssignment.ReturnCondition.FAULTY
            ),
        )

        result.device.refresh_from_db()

        self.assertEqual(
            result.device.status,
            InventoryDevice.Status.FAULTY,
        )

    def test_cross_tenant_assignment_return_is_blocked(self):
        assignment_result = assign_device_to_service(
            organization=self.organization_a,
            actor=self.actor,
            device_id=self.device_a.id,
            service_account_id=self.service_a.id,
        )

        with self.assertRaises(InventoryCustodyError):
            return_device_from_service(
                organization=self.organization_b,
                actor=self.actor,
                assignment_id=assignment_result.assignment.id,
                return_condition=(
                    DeviceAssignment.ReturnCondition.GOOD
                ),
            )


class InventoryOperationalAPITests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Inventory ISP",
            code="INVENTORY-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Inventory ISP",
            code="OTHER-INVENTORY",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.owner = User.objects.create_user(
            username="inventory-api-owner",
            email="inventory-api-owner@nexora.local",
            password="StrongTestPassword123!",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="API-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03009999991",
            address_line="Test Street",
            city="Lahore",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 50",
            code="API-FIBER-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="API-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.device = InventoryDevice.objects.create(
            organization=self.organization,
            asset_tag="API-ONU-001",
            device_type=InventoryDevice.DeviceType.ONU,
            manufacturer="Huawei",
            model_name="HG8546M",
            serial_number="API-SERIAL-001",
            mac_address="AA:BB:CC:10:00:01",
        )

        self.other_device = InventoryDevice.objects.create(
            organization=self.other_organization,
            asset_tag="OTHER-ONU-001",
            device_type=InventoryDevice.DeviceType.ONU,
            serial_number="OTHER-SERIAL-001",
            mac_address="AA:BB:CC:20:00:01",
        )

        self.authenticate_owner()

    def authenticate_owner(self):
        response = self.client.post(
            reverse("tenant-login"),
            {
                "email": self.owner.email,
                "password": "StrongTestPassword123!",
                "organization_code": self.organization.code,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {response.data['access']}"
            )
        )

    def test_device_list_returns_only_current_tenant_devices(self):
        response = self.client.get(
            reverse("inventory-device-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["asset_tag"],
            self.device.asset_tag,
        )

    def test_device_detail_blocks_cross_tenant_device(self):
        response = self.client.get(
            reverse(
                "inventory-device-detail",
                kwargs={
                    "device_id": self.other_device.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_assign_action_assigns_device(self):
        response = self.client.post(
            reverse("device-assignment-assign"),
            {
                "device_id": str(self.device.id),
                "service_account_id": str(self.service.id),
                "assignment_notes": "Installed at customer site",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.device.refresh_from_db()

        self.assertEqual(
            self.device.status,
            InventoryDevice.Status.ASSIGNED,
        )
        self.assertEqual(
            response.data["service_number"],
            self.service.service_number,
        )

    def test_assign_action_blocks_cross_tenant_device(self):
        response = self.client.post(
            reverse("device-assignment-assign"),
            {
                "device_id": str(self.other_device.id),
                "service_account_id": str(self.service.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_assignment_list_is_tenant_scoped(self):
        assign_device_to_service(
            organization=self.organization,
            actor=self.owner,
            device_id=self.device.id,
            service_account_id=self.service.id,
        )

        response = self.client.get(
            reverse("device-assignment-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["asset_tag"],
            self.device.asset_tag,
        )

    def test_return_action_returns_device(self):
        result = assign_device_to_service(
            organization=self.organization,
            actor=self.owner,
            device_id=self.device.id,
            service_account_id=self.service.id,
        )

        response = self.client.post(
            reverse(
                "device-assignment-return",
                kwargs={
                    "assignment_id": result.assignment.id,
                },
            ),
            {
                "return_condition": (
                    DeviceAssignment.ReturnCondition.GOOD
                ),
                "return_notes": "Device received",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.device.refresh_from_db()

        self.assertEqual(
            self.device.status,
            InventoryDevice.Status.AVAILABLE,
        )
        self.assertIsNotNone(response.data["returned_at"])