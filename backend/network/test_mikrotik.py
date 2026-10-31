from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from routeros_api.exceptions import (
    RouterOsApiCommunicationError,
    RouterOsApiConnectionError,
)

from customers.models import Customer, InternetPackage, ServiceAccount
from network.credentials import (
    NetworkCredentialError,
    decrypt_secret,
    encrypt_secret,
)
from network.models import NetworkAssignment, NetworkNode, ProvisioningRequest
from network.providers import (
    MikroTikProvisioningProvider,
    StubProvisioningProvider,
    get_provisioning_provider,
)
from network.provisioning import execute_provisioning_request
from tenancy.models import Organization, OrganizationMembership


User = get_user_model()


class FakeRouterResource:
    def __init__(self, rows):
        self.rows = rows

    def get(self, **filters):
        return [
            dict(row)
            for row in self.rows
            if all(row.get(key) == value for key, value in filters.items())
        ]

    def add(self, **values):
        row = {"id": f"*{len(self.rows) + 1:X}", **values}
        self.rows.append(row)
        return [row]

    def set(self, *, id, **values):
        for row in self.rows:
            if row["id"] == id:
                row.update(values)
                return []
        raise RouterOsApiCommunicationError("no such item", b"no such item")

    def remove(self, *, id):
        self.rows[:] = [row for row in self.rows if row["id"] != id]
        return []


class FakeRouter:
    """In-memory stand-in for a MikroTik router reachable through RouterOS-api."""

    def __init__(self):
        self.tables = {
            "/ppp/secret": [],
            "/ppp/active": [],
            "/system/identity": [{"name": "NEXORA-CORE"}],
            "/system/resource": [{"version": "7.16.1 (stable)", "board-name": "CCR2004", "uptime": "3d4h"}],
        }
        self.connect_error = None
        self.logins = []

    def pool_factory(self, host, **kwargs):
        router = self

        class FakePool:
            socket_timeout = 15.0

            def get_api(self):
                if router.connect_error is not None:
                    raise router.connect_error
                router.logins.append({"host": host, **kwargs})
                return FakeApi(router)

            def disconnect(self):
                pass

        return FakePool()

    def secret(self, name):
        rows = [row for row in self.tables["/ppp/secret"] if row["name"] == name]
        return rows[0] if rows else None


class FakeApi:
    def __init__(self, router):
        self.router = router

    def get_resource(self, path):
        return FakeRouterResource(self.router.tables[path])


class MikroTikTestMixin:
    def setUp(self):
        super().setUp()
        self.router = FakeRouter()
        pool_patcher = patch(
            "network.providers.mikrotik.routeros_api.RouterOsApiPool",
            side_effect=self.router.pool_factory,
        )
        pool_patcher.start()
        self.addCleanup(pool_patcher.stop)

        self.organization = Organization.objects.create(
            name="MikroTik ISP",
            code="MKT-ISP",
            city="Lahore",
        )
        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 20",
            code="FIBER-20",
            download_speed_mbps=20,
            upload_speed_mbps=10,
            monthly_price="2500.00",
            router_profile="20M-PROFILE",
        )
        self.target_package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 50",
            code="FIBER-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="4500.00",
        )
        self.node = NetworkNode.objects.create(
            organization=self.organization,
            name="Model Town BRAS",
            code="BRAS-MDL-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.60.0.1",
            provisioning_backend=NetworkNode.ProvisioningBackend.MIKROTIK,
            router_api_username="nexora-api",
            router_api_password_encrypted=encrypt_secret("router-secret"),
        )

    def create_service(self, *, status=ServiceAccount.Status.ACTIVE, number="001"):
        customer = Customer.objects.create(
            organization=self.organization,
            customer_number=f"MKT-CUST-{number}",
            first_name="Ali",
            last_name="Khan",
            phone=f"0300555{number}",
            address_line="Street 1",
            city="Lahore",
        )
        service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number=f"MKT-SRV-{number}",
            customer=customer,
            internet_package=self.package,
            status=status,
        )
        assignment = NetworkAssignment.objects.create(
            organization=self.organization,
            service_account=service,
            network_node=self.node,
            username=f"ali-{number}",
            network_password_encrypted=encrypt_secret("pppoe-pass"),
        )
        return service, assignment

    def run_request(self, service, assignment, action, payload=None):
        request = ProvisioningRequest.objects.create(
            organization=self.organization,
            service_account=service,
            network_assignment=assignment,
            action=action,
            requested_payload=payload or {},
        )
        return execute_provisioning_request(provisioning_request_id=request.id).provisioning_request


class MikroTikProvisioningProviderTests(MikroTikTestMixin, TestCase):
    def test_provider_is_selected_from_node_backend(self):
        service, assignment = self.create_service()
        request = ProvisioningRequest.objects.create(
            organization=self.organization,
            service_account=service,
            network_assignment=assignment,
            action=ProvisioningRequest.Action.ACTIVATE,
        )
        self.assertIsInstance(get_provisioning_provider(provisioning_request=request), MikroTikProvisioningProvider)

        self.node.provisioning_backend = NetworkNode.ProvisioningBackend.MANUAL
        self.node.save()
        request.refresh_from_db()
        self.assertIsInstance(get_provisioning_provider(provisioning_request=request), StubProvisioningProvider)

    def test_activation_creates_pppoe_secret_on_router(self):
        service, assignment = self.create_service()

        request = self.run_request(service, assignment, ProvisioningRequest.Action.ACTIVATE)

        self.assertEqual(request.status, ProvisioningRequest.Status.SUCCEEDED, request.error_message)
        self.assertEqual(request.provider_reference, "MIKROTIK-BRAS-MDL-01-ACTIVATE-ali-001")
        secret = self.router.secret("ali-001")
        self.assertEqual(secret["password"], "pppoe-pass")
        self.assertEqual(secret["profile"], "20M-PROFILE")
        self.assertEqual(secret["service"], "pppoe")
        self.assertEqual(secret["comment"], "MKT-SRV-001")
        self.assertEqual(secret["disabled"], "no")
        self.assertEqual(self.router.logins[0]["host"], "10.60.0.1")
        self.assertEqual(self.router.logins[0]["username"], "nexora-api")
        self.assertEqual(self.router.logins[0]["password"], "router-secret")
        self.assertTrue(self.router.logins[0]["plaintext_login"])

    def test_activation_updates_existing_secret_instead_of_duplicating(self):
        service, assignment = self.create_service()
        self.router.tables["/ppp/secret"].append(
            {"id": "*9", "name": "ali-001", "password": "old", "profile": "default", "disabled": "yes"}
        )

        request = self.run_request(service, assignment, ProvisioningRequest.Action.ACTIVATE)

        self.assertEqual(request.status, ProvisioningRequest.Status.SUCCEEDED, request.error_message)
        self.assertEqual(len(self.router.tables["/ppp/secret"]), 1)
        secret = self.router.secret("ali-001")
        self.assertEqual(secret["password"], "pppoe-pass")
        self.assertEqual(secret["profile"], "20M-PROFILE")
        self.assertEqual(secret["disabled"], "no")

    def test_suspension_disables_secret_and_drops_live_session(self):
        service, assignment = self.create_service(status=ServiceAccount.Status.SUSPENSION_PENDING)
        self.router.tables["/ppp/secret"].append({"id": "*1", "name": "ali-001", "disabled": "no"})
        self.router.tables["/ppp/active"].append({"id": "*A1", "name": "ali-001"})
        self.router.tables["/ppp/active"].append({"id": "*A2", "name": "someone-else"})

        request = self.run_request(service, assignment, ProvisioningRequest.Action.SUSPEND)

        self.assertEqual(request.status, ProvisioningRequest.Status.SUCCEEDED, request.error_message)
        self.assertEqual(self.router.secret("ali-001")["disabled"], "yes")
        self.assertEqual([row["name"] for row in self.router.tables["/ppp/active"]], ["someone-else"])
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)

    def test_restore_reenables_secret(self):
        service, assignment = self.create_service(status=ServiceAccount.Status.RESTORE_PENDING)
        self.router.tables["/ppp/secret"].append({"id": "*1", "name": "ali-001", "disabled": "yes"})

        request = self.run_request(service, assignment, ProvisioningRequest.Action.RESTORE)

        self.assertEqual(request.status, ProvisioningRequest.Status.SUCCEEDED, request.error_message)
        self.assertEqual(self.router.secret("ali-001")["disabled"], "no")
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceAccount.Status.ACTIVE)

    def test_package_change_switches_profile_and_reconnects_subscriber(self):
        service, assignment = self.create_service()
        self.router.tables["/ppp/secret"].append({"id": "*1", "name": "ali-001", "profile": "20M-PROFILE"})
        self.router.tables["/ppp/active"].append({"id": "*A1", "name": "ali-001"})

        request = self.run_request(
            service,
            assignment,
            ProvisioningRequest.Action.CHANGE_PACKAGE,
            payload={"target_package_id": str(self.target_package.id)},
        )

        self.assertEqual(request.status, ProvisioningRequest.Status.SUCCEEDED, request.error_message)
        # Packages without an explicit router profile fall back to their code.
        self.assertEqual(self.router.secret("ali-001")["profile"], "FIBER-50")
        self.assertEqual(self.router.tables["/ppp/active"], [])
        service.refresh_from_db()
        self.assertEqual(service.internet_package, self.target_package)

    def test_unreachable_router_fails_request_and_keeps_service_active(self):
        service, assignment = self.create_service(status=ServiceAccount.Status.SUSPENSION_PENDING)
        self.router.connect_error = TimeoutError("timed out")

        request = self.run_request(service, assignment, ProvisioningRequest.Action.SUSPEND)

        self.assertEqual(request.status, ProvisioningRequest.Status.FAILED)
        self.assertIn("Could not reach router BRAS-MDL-01", request.error_message)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceAccount.Status.ACTIVE)

    def test_library_wrapped_timeout_is_reported_as_unreachable(self):
        service, assignment = self.create_service()
        self.router.connect_error = RouterOsApiConnectionError("timed out")

        request = self.run_request(service, assignment, ProvisioningRequest.Action.ACTIVATE)

        self.assertEqual(request.status, ProvisioningRequest.Status.FAILED)
        self.assertIn("Could not reach router BRAS-MDL-01", request.error_message)

    def test_rejected_login_fails_request_with_clear_message(self):
        service, assignment = self.create_service()
        self.router.connect_error = RouterOsApiCommunicationError(
            "invalid user name or password", b"invalid user name or password"
        )

        request = self.run_request(service, assignment, ProvisioningRequest.Action.ACTIVATE)

        self.assertEqual(request.status, ProvisioningRequest.Status.FAILED)
        self.assertIn("Could not log in to router BRAS-MDL-01", request.error_message)

    def test_activation_without_stored_password_cannot_create_secret(self):
        service, assignment = self.create_service()
        assignment.network_password_encrypted = ""
        assignment.save()

        request = self.run_request(service, assignment, ProvisioningRequest.Action.ACTIVATE)

        self.assertEqual(request.status, ProvisioningRequest.Status.FAILED)
        self.assertIn("no stored PPPoE password", request.error_message)
        self.assertEqual(self.router.tables["/ppp/secret"], [])


class MikroTikActivationAPITests(MikroTikTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.owner = User.objects.create_user(
            username="mkt-owner",
            email="mkt-owner@nexora.local",
            password="StrongTestPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )
        login = self.client.post(
            reverse("tenant-login"),
            {
                "email": self.owner.email,
                "password": "StrongTestPassword123!",
                "organization_code": self.organization.code,
            },
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def activation_payload(self, **overrides):
        payload = {
            "internet_package_id": str(self.package.id),
            "network_node_id": str(self.node.id),
            "first_name": "Sara",
            "last_name": "Ahmed",
            "phone": "03007776655",
            "address_line": "Street 9",
            "city": "Lahore",
            "billing_day": 1,
            "due_day": 10,
        }
        payload.update(overrides)
        return payload

    def test_activation_generates_credentials_and_provisions_router_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("customer-activate"),
                self.activation_payload(),
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        credentials = response.data["network_assignment"]
        service_number = response.data["service_account"]["service_number"]
        self.assertEqual(credentials["username"], service_number)
        self.assertEqual(len(credentials["password"]), 12)

        assignment = NetworkAssignment.objects.get(id=credentials["id"])
        self.assertNotIn(credentials["password"], assignment.network_password_encrypted)
        self.assertEqual(decrypt_secret(assignment.network_password_encrypted), credentials["password"])

        secret = self.router.secret(service_number)
        self.assertIsNotNone(secret)
        self.assertEqual(secret["password"], credentials["password"])
        request = ProvisioningRequest.objects.get(id=response.data["provisioning_request"]["id"])
        self.assertEqual(request.status, ProvisioningRequest.Status.SUCCEEDED, request.error_message)

    def test_activation_uses_staff_supplied_credentials(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("customer-activate"),
                self.activation_payload(network_username="sara-fiber", network_password="Chosen-Pass-9"),
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.router.secret("sara-fiber")["password"], "Chosen-Pass-9")

    def test_duplicate_username_on_same_node_is_rejected(self):
        service, _ = self.create_service()

        response = self.client.post(
            reverse("customer-activate"),
            self.activation_payload(network_username="ALI-001"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already assigned", response.data["detail"])
        self.assertEqual(NetworkAssignment.objects.filter(network_node=self.node).count(), 1)

    def test_node_router_password_is_write_only_and_kept_on_blank_update(self):
        detail_url = reverse("network-node-detail", kwargs={"node_id": self.node.id})

        response = self.client.get(detail_url)
        self.assertNotIn("router_api_password", response.data)
        self.assertNotIn("router_api_password_encrypted", response.data)
        self.assertTrue(response.data["router_api_password_set"])

        response = self.client.patch(detail_url, {"router_api_password": "", "router_api_port": 8729}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.node.refresh_from_db()
        self.assertEqual(decrypt_secret(self.node.router_api_password_encrypted), "router-secret")
        self.assertEqual(self.node.router_api_port, 8729)

    def test_mikrotik_node_requires_router_credentials(self):
        response = self.client.post(
            reverse("network-node-list"),
            {
                "name": "New BRAS",
                "code": "BRAS-NEW",
                "node_type": NetworkNode.NodeType.ROUTER,
                "management_ip": "10.70.0.1",
                "provisioning_backend": NetworkNode.ProvisioningBackend.MIKROTIK,
                "router_api_username": "api",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data["detail"])
        self.assertFalse(NetworkNode.objects.filter(code="BRAS-NEW").exists())

    def test_test_connection_reports_router_identity(self):
        response = self.client.post(
            reverse("network-node-test-connection", kwargs={"node_id": self.node.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["router"]["identity"], "NEXORA-CORE")
        self.assertEqual(response.data["router"]["version"], "7.16.1 (stable)")

    def test_test_connection_surfaces_router_errors(self):
        self.router.connect_error = ConnectionRefusedError("refused")

        response = self.client.post(
            reverse("network-node-test-connection", kwargs={"node_id": self.node.id})
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Could not reach router", response.data["detail"])

    def test_test_connection_rejects_manual_nodes(self):
        self.node.provisioning_backend = NetworkNode.ProvisioningBackend.MANUAL
        self.node.save()

        response = self.client.post(
            reverse("network-node-test-connection", kwargs={"node_id": self.node.id})
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class NetworkCredentialTests(TestCase):
    def test_round_trip_and_blank_values(self):
        token = encrypt_secret("s3cret")
        self.assertNotEqual(token, "s3cret")
        self.assertEqual(decrypt_secret(token), "s3cret")
        self.assertEqual(encrypt_secret(""), "")
        self.assertEqual(decrypt_secret(""), "")

    def test_wrong_key_raises_clear_error(self):
        token = encrypt_secret("s3cret")
        with override_settings(NETWORK_CREDENTIALS_KEY="ZmFrZS1rZXktZmFrZS1rZXktZmFrZS1rZXktZmFrZTE="):
            with self.assertRaises(NetworkCredentialError):
                decrypt_secret(token)
