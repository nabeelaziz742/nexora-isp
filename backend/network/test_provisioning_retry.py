from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import BillingProfile, Customer, InternetPackage, ServiceAccount
from network.models import NetworkAssignment, NetworkNode, ProvisioningRequest
from network.provisioning import execute_provisioning_request
from network.services import ServiceLifecycleError, retry_provisioning_request
from tenancy.models import AuditLog, Organization, OrganizationMembership


User = get_user_model()


class RetryFixtureMixin:
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name="Retry ISP",
            code="RETRY-ISP",
            city="Lahore",
            currency="PKR",
        )
        self.owner = User.objects.create_user(
            username="retry-owner",
            email="retry-owner@nexora.local",
            password="StrongTestPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )
        customer = Customer.objects.create(
            organization=self.organization,
            customer_number="RTY-CUST-001",
            first_name="Bilal",
            phone="03008887771",
            address_line="Street 4",
            city="Lahore",
        )
        package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 30",
            code="RTY-30",
            download_speed_mbps=30,
            upload_speed_mbps=10,
            monthly_price="3000.00",
        )
        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="RTY-SRV-001",
            customer=customer,
            internet_package=package,
            status=ServiceAccount.Status.ACTIVE,
        )
        BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service,
            billing_day=1,
            due_day=10,
        )
        node = NetworkNode.objects.create(
            organization=self.organization,
            name="Retry Router",
            code="RTY-NODE",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.40.0.1",
        )
        self.assignment = NetworkAssignment.objects.create(
            organization=self.organization,
            service_account=self.service,
            network_node=node,
            username="bilal-rty",
            ip_address="10.40.0.10",
        )

    def failed_request(self, action=ProvisioningRequest.Action.ACTIVATE, **extra):
        return ProvisioningRequest.objects.create(
            organization=self.organization,
            service_account=self.service,
            network_assignment=self.assignment,
            action=action,
            status=ProvisioningRequest.Status.FAILED,
            error_message="Router unreachable",
            requested_payload={"source": "activation"},
            **extra,
        )


class RetryServiceTests(RetryFixtureMixin, TestCase):
    def test_failed_activation_is_requeued_and_completes(self):
        failed = self.failed_request()

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            result = retry_provisioning_request(
                organization=self.organization,
                provisioning_request_id=failed.id,
                requested_by=self.owner,
            )

        retry = result.provisioning_request
        self.assertNotEqual(retry.id, failed.id)
        self.assertEqual(retry.action, ProvisioningRequest.Action.ACTIVATE)
        self.assertEqual(retry.status, ProvisioningRequest.Status.PENDING)
        self.assertEqual(retry.network_assignment, self.assignment)
        self.assertEqual(retry.requested_payload["retry_of"], str(failed.id))
        self.assertEqual(retry.requested_payload["source"], "activation")
        self.assertEqual(len(callbacks), 1)
        self.assertTrue(AuditLog.objects.filter(action="PROVISIONING_REQUEST_RETRIED").exists())

        execute_provisioning_request(provisioning_request_id=retry.id)

        retry.refresh_from_db()
        failed.refresh_from_db()
        self.assertEqual(retry.status, ProvisioningRequest.Status.SUCCEEDED)
        self.assertEqual(failed.status, ProvisioningRequest.Status.FAILED)

    def test_only_failed_requests_can_be_retried(self):
        succeeded = self.failed_request()
        succeeded.status = ProvisioningRequest.Status.SUCCEEDED
        succeeded.save()

        with self.assertRaisesMessage(ServiceLifecycleError, "Only a failed"):
            retry_provisioning_request(
                organization=self.organization,
                provisioning_request_id=succeeded.id,
            )

    def test_older_failure_cannot_be_retried_after_a_newer_request(self):
        old = self.failed_request()
        ProvisioningRequest.objects.filter(id=old.id).update(
            requested_at=timezone.now() - timedelta(hours=1)
        )
        self.failed_request()

        with self.assertRaisesMessage(ServiceLifecycleError, "newer provisioning request"):
            retry_provisioning_request(
                organization=self.organization,
                provisioning_request_id=old.id,
            )

    def test_retry_is_blocked_while_another_request_is_in_flight(self):
        failed = self.failed_request()
        in_flight = ProvisioningRequest.objects.create(
            organization=self.organization,
            service_account=self.service,
            network_assignment=self.assignment,
            action=ProvisioningRequest.Action.SUSPEND,
            status=ProvisioningRequest.Status.PROCESSING,
        )
        # requested_at is auto-set; make the in-flight request the older one.
        ProvisioningRequest.objects.filter(id=in_flight.id).update(
            requested_at=timezone.now() - timedelta(hours=1)
        )

        with self.assertRaisesMessage(ServiceLifecycleError, "active provisioning request"):
            retry_provisioning_request(
                organization=self.organization,
                provisioning_request_id=failed.id,
            )

    def test_failed_suspension_retry_marks_service_pending(self):
        failed = self.failed_request(action=ProvisioningRequest.Action.SUSPEND)

        retry_provisioning_request(
            organization=self.organization,
            provisioning_request_id=failed.id,
        )

        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.SUSPENSION_PENDING)

    def test_failed_restore_retry_marks_service_restore_pending(self):
        self.service.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.service.save()
        failed = self.failed_request(action=ProvisioningRequest.Action.RESTORE)

        retry_provisioning_request(
            organization=self.organization,
            provisioning_request_id=failed.id,
        )

        self.service.refresh_from_db()
        self.assertEqual(self.service.status, ServiceAccount.Status.RESTORE_PENDING)

    def test_request_from_another_tenant_is_not_found(self):
        other = Organization.objects.create(name="Other", code="OTHER-RTY", city="Lahore")
        failed = self.failed_request()

        with self.assertRaisesMessage(ServiceLifecycleError, "not found"):
            retry_provisioning_request(organization=other, provisioning_request_id=failed.id)


class RetryAPITests(RetryFixtureMixin, APITestCase):
    def setUp(self):
        super().setUp()
        response = self.client.post(
            reverse("tenant-login"),
            {
                "email": self.owner.email,
                "password": "StrongTestPassword123!",
                "organization_code": self.organization.code,
            },
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_retry_endpoint_creates_new_request(self):
        failed = self.failed_request()

        response = self.client.post(
            reverse("provisioning-request-retry", kwargs={"provisioning_request_id": failed.id})
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["action"], ProvisioningRequest.Action.ACTIVATE)
        self.assertEqual(
            ProvisioningRequest.objects.filter(service_account=self.service).count(),
            2,
        )

    def test_retry_endpoint_rejects_non_failed_request(self):
        failed = self.failed_request()
        failed.status = ProvisioningRequest.Status.SUCCEEDED
        failed.save()

        response = self.client.post(
            reverse("provisioning-request-retry", kwargs={"provisioning_request_id": failed.id})
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
