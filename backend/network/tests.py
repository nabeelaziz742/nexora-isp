from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import (
    Customer,
    InternetPackage,
    ServiceAccount,
)
from network.models import (
    NetworkAssignment,
    NetworkNode,
    ProvisioningRequest,
)
from tenancy.models import (
    AuditLog,
    Organization,
    OrganizationMembership,
)

from network.services import (
    ServiceLifecycleError,
    request_package_change,
    request_service_restore,
    request_service_suspension,
)


User = get_user_model()


class NetworkTenantIsolationTests(TestCase):
    def setUp(self):
        self.organization_a = Organization.objects.create(
            name="ISP A",
            code="ISP-A",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.organization_b = Organization.objects.create(
            name="ISP B",
            code="ISP-B",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.customer_a = Customer.objects.create(
            organization=self.organization_a,
            customer_number="CUS-A-001",
            first_name="Ali",
            last_name="A",
            phone="03000000001",
            address_line="Address A",
            area="Area A",
            city="Lahore",
        )

        self.customer_b = Customer.objects.create(
            organization=self.organization_b,
            customer_number="CUS-B-001",
            first_name="Ahmed",
            last_name="B",
            phone="03000000002",
            address_line="Address B",
            area="Area B",
            city="Karachi",
        )

        self.package_a = InternetPackage.objects.create(
            organization=self.organization_a,
            name="ISP A 20 Mbps",
            code="A-20",
            download_speed_mbps=20,
            upload_speed_mbps=10,
            monthly_price="2500.00",
        )

        self.package_b = InternetPackage.objects.create(
            organization=self.organization_b,
            name="ISP B 30 Mbps",
            code="B-30",
            download_speed_mbps=30,
            upload_speed_mbps=15,
            monthly_price="3500.00",
        )

        self.service_a = ServiceAccount.objects.create(
            organization=self.organization_a,
            service_number="SRV-A-001",
            customer=self.customer_a,
            internet_package=self.package_a,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.service_b = ServiceAccount.objects.create(
            organization=self.organization_b,
            service_number="SRV-B-001",
            customer=self.customer_b,
            internet_package=self.package_b,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.node_a = NetworkNode.objects.create(
            organization=self.organization_a,
            name="Lahore Core Router",
            code="RTR-A-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.10.0.1",
        )

        self.node_b = NetworkNode.objects.create(
            organization=self.organization_b,
            name="Karachi Core Router",
            code="RTR-B-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.20.0.1",
        )

    def test_network_node_queryset_is_tenant_scoped(self):
        nodes = NetworkNode.objects.for_organization(
            self.organization_a
        )

        self.assertEqual(nodes.count(), 1)
        self.assertEqual(nodes.first(), self.node_a)
        self.assertNotIn(self.node_b, nodes)

    def test_duplicate_network_node_code_is_rejected_per_org(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NetworkNode.objects.create(
                    organization=self.organization_a,
                    name="Duplicate Router",
                    code="RTR-A-01",
                    node_type=NetworkNode.NodeType.ROUTER,
                )

    def test_same_network_node_code_is_allowed_across_tenants(self):
        node = NetworkNode.objects.create(
            organization=self.organization_b,
            name="ISP B Router With Same Code",
            code="RTR-A-01",
            node_type=NetworkNode.NodeType.ROUTER,
        )

        self.assertEqual(
            node.organization,
            self.organization_b,
        )

    def test_tenant_assignment_can_be_created(self):
        assignment = NetworkAssignment.objects.create(
            organization=self.organization_a,
            service_account=self.service_a,
            network_node=self.node_a,
            username="ali-a",
            ip_address="10.10.10.2",
        )

        self.assertEqual(
            assignment.organization,
            self.organization_a,
        )
        self.assertEqual(
            assignment.service_account,
            self.service_a,
        )
        self.assertEqual(
            assignment.network_node,
            self.node_a,
        )

    def test_provisioning_request_starts_pending(self):
        assignment = NetworkAssignment.objects.create(
            organization=self.organization_a,
            service_account=self.service_a,
            network_node=self.node_a,
        )

        provisioning_request = ProvisioningRequest.objects.create(
            organization=self.organization_a,
            service_account=self.service_a,
            network_assignment=assignment,
            action=ProvisioningRequest.Action.ACTIVATE,
        )

        self.assertEqual(
            provisioning_request.status,
            ProvisioningRequest.Status.PENDING,
        )

        self.assertNotEqual(
            provisioning_request.status,
            ProvisioningRequest.Status.SUCCEEDED,
        )


class NetworkOperationalAPITests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Network ISP",
            code="NETWORK-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Network ISP",
            code="OTHER-NETWORK",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.owner = User.objects.create_user(
            username="network-owner",
            email="network-owner@nexora.local",
            password="StrongTestPassword123!",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="NET-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03001234567",
            address_line="Test Street",
            city="Lahore",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 50",
            code="FIBER-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="NET-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.node = NetworkNode.objects.create(
            organization=self.organization,
            name="Lahore Core Router",
            code="RTR-LHR-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.10.0.1",
        )

        self.other_node = NetworkNode.objects.create(
            organization=self.other_organization,
            name="Karachi Router",
            code="RTR-KHI-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.20.0.1",
        )

        self.assignment = NetworkAssignment.objects.create(
            organization=self.organization,
            service_account=self.service,
            network_node=self.node,
            username="nabeel-fiber",
            ip_address="10.10.10.2",
        )

        self.provisioning_request = (
            ProvisioningRequest.objects.create(
                organization=self.organization,
                service_account=self.service,
                network_assignment=self.assignment,
                action=ProvisioningRequest.Action.ACTIVATE,
            )
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

    def test_node_list_returns_only_current_tenant_nodes(self):
        response = self.client.get(
            reverse("network-node-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["code"],
            self.node.code,
        )

    def test_node_detail_blocks_cross_tenant_node(self):
        response = self.client.get(
            reverse(
                "network-node-detail",
                kwargs={
                    "node_id": self.other_node.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_assignment_list_is_tenant_scoped(self):
        response = self.client.get(
            reverse("network-assignment-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["service_number"],
            self.service.service_number,
        )

    def test_provisioning_queue_is_tenant_scoped(self):
        response = self.client.get(
            reverse("provisioning-request-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["status"],
            ProvisioningRequest.Status.PENDING,
        )


class ServiceLifecycleDomainTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Lifecycle ISP",
            code="LIFECYCLE-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Lifecycle ISP",
            code="OTHER-LIFECYCLE",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="LIFE-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03001112222",
            address_line="Lifecycle Street",
            city="Lahore",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 50",
            code="LIFE-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.target_package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 100",
            code="LIFE-100",
            download_speed_mbps=100,
            upload_speed_mbps=50,
            monthly_price="8000.00",
        )

        self.other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Other Fiber 200",
            code="OTHER-200",
            download_speed_mbps=200,
            upload_speed_mbps=100,
            monthly_price="12000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="LIFE-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.node = NetworkNode.objects.create(
            organization=self.organization,
            name="Lifecycle Core Router",
            code="LIFE-RTR-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.30.0.1",
        )

        self.assignment = NetworkAssignment.objects.create(
            organization=self.organization,
            service_account=self.service,
            network_node=self.node,
            username="lifecycle-user",
            ip_address="10.30.10.2",
        )

    def test_suspension_request_moves_service_to_pending(self):
        result = request_service_suspension(
            organization=self.organization,
            service_account_id=self.service.id,
        )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.status,
            ServiceAccount.Status.SUSPENSION_PENDING,
        )
        self.assertEqual(
            result.provisioning_request.action,
            ProvisioningRequest.Action.SUSPEND,
        )
        self.assertEqual(
            result.provisioning_request.status,
            ProvisioningRequest.Status.PENDING,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="SERVICE_SUSPENSION_REQUESTED",
            ).exists()
        )

    def test_suspension_request_requires_allowed_status(self):
        self.service.status = (
            ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        )
        self.service.save(update_fields=["status"])

        with self.assertRaises(ServiceLifecycleError):
            request_service_suspension(
                organization=self.organization,
                service_account_id=self.service.id,
            )

    def test_conflicting_pending_request_blocks_suspension(self):
        ProvisioningRequest.objects.create(
            organization=self.organization,
            service_account=self.service,
            network_assignment=self.assignment,
            action=ProvisioningRequest.Action.CHANGE_PACKAGE,
            status=ProvisioningRequest.Status.PENDING,
        )

        with self.assertRaises(ServiceLifecycleError):
            request_service_suspension(
                organization=self.organization,
                service_account_id=self.service.id,
            )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.status,
            ServiceAccount.Status.ACTIVE,
        )

    def test_restore_request_moves_service_to_restore_pending(self):
        self.service.status = (
            ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        )
        self.service.save(update_fields=["status"])

        result = request_service_restore(
            organization=self.organization,
            service_account_id=self.service.id,
        )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.status,
            ServiceAccount.Status.RESTORE_PENDING,
        )
        self.assertEqual(
            result.provisioning_request.action,
            ProvisioningRequest.Action.RESTORE,
        )
        self.assertEqual(
            result.provisioning_request.status,
            ProvisioningRequest.Status.PENDING,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="SERVICE_RESTORE_REQUESTED",
            ).exists()
        )

    def test_restore_request_rejects_active_service(self):
        with self.assertRaises(ServiceLifecycleError):
            request_service_restore(
                organization=self.organization,
                service_account_id=self.service.id,
            )

    def test_package_change_creates_pending_request(self):
        original_package_id = self.service.internet_package_id

        result = request_package_change(
            organization=self.organization,
            service_account_id=self.service.id,
            internet_package_id=self.target_package.id,
        )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.internet_package_id,
            original_package_id,
        )
        self.assertEqual(
            result.provisioning_request.action,
            ProvisioningRequest.Action.CHANGE_PACKAGE,
        )
        self.assertEqual(
            result.provisioning_request.status,
            ProvisioningRequest.Status.PENDING,
        )
        self.assertEqual(
            result.provisioning_request.requested_payload[
                "target_package_id"
            ],
            str(self.target_package.id),
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="SERVICE_PACKAGE_CHANGE_REQUESTED",
            ).exists()
        )

    def test_package_change_rejects_same_package(self):
        with self.assertRaises(ServiceLifecycleError):
            request_package_change(
                organization=self.organization,
                service_account_id=self.service.id,
                internet_package_id=self.package.id,
            )

    def test_package_change_blocks_cross_tenant_package(self):
        with self.assertRaises(ServiceLifecycleError):
            request_package_change(
                organization=self.organization,
                service_account_id=self.service.id,
                internet_package_id=self.other_package.id,
            )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.internet_package_id,
            self.package.id,
        )

    def test_lifecycle_blocks_cross_tenant_service(self):
        other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-LIFE-CUST",
            first_name="Other",
            last_name="Customer",
            phone="03009998888",
            address_line="Other Street",
            city="Karachi",
        )

        other_service = ServiceAccount.objects.create(
            organization=self.other_organization,
            service_number="OTHER-LIFE-SRV",
            customer=other_customer,
            internet_package=self.other_package,
            status=ServiceAccount.Status.ACTIVE,
        )

        with self.assertRaises(ServiceLifecycleError):
            request_service_suspension(
                organization=self.organization,
                service_account_id=other_service.id,
            )


class ServiceLifecycleOperationalAPITests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Lifecycle API ISP",
            code="LIFE-API",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Lifecycle API ISP",
            code="OTHER-LIFE-API",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.owner = User.objects.create_user(
            username="lifecycle-api-owner",
            email="lifecycle-api-owner@nexora.local",
            password="StrongTestPassword123!",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="LIFE-API-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03005551111",
            address_line="Lifecycle API Street",
            city="Lahore",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 50",
            code="LIFE-API-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.target_package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 100",
            code="LIFE-API-100",
            download_speed_mbps=100,
            upload_speed_mbps=50,
            monthly_price="8000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="LIFE-API-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.node = NetworkNode.objects.create(
            organization=self.organization,
            name="Lifecycle API Router",
            code="LIFE-API-RTR",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.40.0.1",
        )

        self.assignment = NetworkAssignment.objects.create(
            organization=self.organization,
            service_account=self.service,
            network_node=self.node,
            username="lifecycle-api-user",
            ip_address="10.40.10.2",
        )

        self.other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-API-CUST",
            first_name="Other",
            last_name="Customer",
            phone="03006662222",
            address_line="Other API Street",
            city="Karachi",
        )

        self.other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Other Fiber",
            code="OTHER-API-100",
            download_speed_mbps=100,
            upload_speed_mbps=50,
            monthly_price="9000.00",
        )

        self.other_service = ServiceAccount.objects.create(
            organization=self.other_organization,
            service_number="OTHER-API-SRV",
            customer=self.other_customer,
            internet_package=self.other_package,
            status=ServiceAccount.Status.ACTIVE,
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

    def test_suspension_request_api_creates_pending_request(self):
        response = self.client.post(
            reverse(
                "service-suspension-request",
                kwargs={
                    "service_account_id": self.service.id,
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["action"],
            ProvisioningRequest.Action.SUSPEND,
        )
        self.assertEqual(
            response.data["status"],
            ProvisioningRequest.Status.PENDING,
        )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.status,
            ServiceAccount.Status.SUSPENSION_PENDING,
        )

    def test_restore_request_api_creates_pending_request(self):
        self.service.status = (
            ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        )
        self.service.save(update_fields=["status"])

        response = self.client.post(
            reverse(
                "service-restore-request",
                kwargs={
                    "service_account_id": self.service.id,
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["action"],
            ProvisioningRequest.Action.RESTORE,
        )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.status,
            ServiceAccount.Status.RESTORE_PENDING,
        )

    def test_package_change_api_does_not_change_package_immediately(self):
        original_package_id = self.service.internet_package_id

        response = self.client.post(
            reverse(
                "service-package-change-request",
                kwargs={
                    "service_account_id": self.service.id,
                },
            ),
            {
                "internet_package_id": str(
                    self.target_package.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["action"],
            ProvisioningRequest.Action.CHANGE_PACKAGE,
        )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.internet_package_id,
            original_package_id,
        )

        self.assertEqual(
            response.data["requested_payload"][
                "target_package_id"
            ],
            str(self.target_package.id),
        )

    def test_lifecycle_api_blocks_cross_tenant_service(self):
        response = self.client.post(
            reverse(
                "service-suspension-request",
                kwargs={
                    "service_account_id": self.other_service.id,
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.other_service.refresh_from_db()

        self.assertEqual(
            self.other_service.status,
            ServiceAccount.Status.ACTIVE,
        )

    def test_package_change_api_requires_package_id(self):
        response = self.client.post(
            reverse(
                "service-package-change-request",
                kwargs={
                    "service_account_id": self.service.id,
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

class ProvisioningExecutionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Provisioning ISP",
            code="PROVISION-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="PROV-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03007770000",
            address_line="Provisioning Street",
            city="Lahore",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 50",
            code="PROV-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.target_package = (
            InternetPackage.objects.create(
                organization=self.organization,
                name="Fiber 100",
                code="PROV-100",
                download_speed_mbps=100,
                upload_speed_mbps=50,
                monthly_price="8000.00",
            )
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="PROV-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.node = NetworkNode.objects.create(
            organization=self.organization,
            name="Provisioning Core Router",
            code="PROV-RTR-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.50.0.1",
        )

        self.assignment = (
            NetworkAssignment.objects.create(
                organization=self.organization,
                service_account=self.service,
                network_node=self.node,
                username="provision-user",
                ip_address="10.50.10.2",
            )
        )

    def test_pending_activation_is_executed_successfully(self):
        from network.provisioning import (
            execute_provisioning_request,
        )

        provisioning_request = (
            ProvisioningRequest.objects.create(
                organization=self.organization,
                service_account=self.service,
                network_assignment=self.assignment,
                action=(
                    ProvisioningRequest.Action.ACTIVATE
                ),
                status=(
                    ProvisioningRequest.Status.PENDING
                ),
            )
        )

        result = execute_provisioning_request(
            provisioning_request_id=(
                provisioning_request.id
            ),
        )

        provisioning_request.refresh_from_db()
        self.service.refresh_from_db()

        self.assertTrue(result.processed)

        self.assertEqual(
            provisioning_request.status,
            ProvisioningRequest.Status.SUCCEEDED,
        )

        self.assertTrue(
            provisioning_request.provider_reference
        )

        self.assertIsNotNone(
            provisioning_request.started_at
        )

        self.assertIsNotNone(
            provisioning_request.completed_at
        )

        self.assertEqual(
            self.service.status,
            ServiceAccount.Status.ACTIVE,
        )

    def test_suspension_execution_moves_service_to_suspended(self):
        from network.provisioning import (
            execute_provisioning_request,
        )

        result = request_service_suspension(
            organization=self.organization,
            service_account_id=self.service.id,
        )

        execute_provisioning_request(
            provisioning_request_id=(
                result.provisioning_request.id
            ),
        )

        self.service.refresh_from_db()

        result.provisioning_request.refresh_from_db()

        self.assertEqual(
            self.service.status,
            ServiceAccount.Status.SUSPENDED_NON_PAYMENT,
        )

        self.assertEqual(
            result.provisioning_request.status,
            ProvisioningRequest.Status.SUCCEEDED,
        )

    def test_restore_execution_moves_service_to_active(self):
        from network.provisioning import (
            execute_provisioning_request,
        )

        self.service.status = (
            ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        )

        self.service.save(
            update_fields=["status"]
        )

        result = request_service_restore(
            organization=self.organization,
            service_account_id=self.service.id,
        )

        execute_provisioning_request(
            provisioning_request_id=(
                result.provisioning_request.id
            ),
        )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.status,
            ServiceAccount.Status.ACTIVE,
        )

    def test_package_change_applies_only_after_successful_execution(
        self,
    ):
        from network.provisioning import (
            execute_provisioning_request,
        )

        result = request_package_change(
            organization=self.organization,
            service_account_id=self.service.id,
            internet_package_id=self.target_package.id,
        )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.internet_package_id,
            self.package.id,
        )

        execute_provisioning_request(
            provisioning_request_id=(
                result.provisioning_request.id
            ),
        )

        self.service.refresh_from_db()

        self.assertEqual(
            self.service.internet_package_id,
            self.target_package.id,
        )

    def test_succeeded_request_is_not_processed_twice(self):
        from network.provisioning import (
            execute_provisioning_request,
        )

        provisioning_request = (
            ProvisioningRequest.objects.create(
                organization=self.organization,
                service_account=self.service,
                network_assignment=self.assignment,
                action=(
                    ProvisioningRequest.Action.ACTIVATE
                ),
            )
        )

        first_result = execute_provisioning_request(
            provisioning_request_id=(
                provisioning_request.id
            ),
        )

        second_result = execute_provisioning_request(
            provisioning_request_id=(
                provisioning_request.id
            ),
        )

        self.assertTrue(first_result.processed)
        self.assertFalse(second_result.processed)

        provisioning_request.refresh_from_db()

        self.assertEqual(
            provisioning_request.status,
            ProvisioningRequest.Status.SUCCEEDED,
        )

    def test_successful_execution_creates_audit_log(self):
        from network.provisioning import (
            execute_provisioning_request,
        )

        provisioning_request = (
            ProvisioningRequest.objects.create(
                organization=self.organization,
                service_account=self.service,
                network_assignment=self.assignment,
                action=(
                    ProvisioningRequest.Action.ACTIVATE
                ),
            )
        )

        execute_provisioning_request(
            provisioning_request_id=(
                provisioning_request.id
            ),
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="PROVISIONING_REQUEST_SUCCEEDED",
                resource_id=provisioning_request.id,
            ).exists()
        )