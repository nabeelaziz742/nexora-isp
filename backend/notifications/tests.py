from django.contrib.auth import get_user_model
from django.test import TestCase

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from customers.models import (
    Customer,
    InternetPackage,
    NotificationPreference,
    ServiceAccount,
)
from notifications.models import NotificationJob
from notifications.services import (
    NotificationDomainError,
    mark_notification_failed,
    mark_notification_sent,
    queue_customer_notification,
    start_notification_processing,
)
from tenancy.models import (
    AuditLog,
    Organization,
    OrganizationMembership,
)

from customers.models import (
    Customer,
    InternetPackage,
    NotificationPreference,
    ServiceAccount,
)
from notifications.models import NotificationJob
from notifications.services import (
    NotificationDomainError,
    mark_notification_failed,
    mark_notification_sent,
    queue_customer_notification,
    start_notification_processing,
)
from tenancy.models import AuditLog, Organization


class NotificationDomainTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Notification ISP",
            code="NOTIF-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Notification ISP",
            code="OTHER-NOTIF",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        User = get_user_model()

        self.actor = User.objects.create_user(
            username="notification-owner",
            email="notification-owner@nexora.test",
            password="StrongPass123!",
            first_name="Notification",
            last_name="Owner",
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="NOTIF-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03009990001",
            address_line="Notification Street",
            city="Lahore",
        )

        self.other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-NOTIF-CUST",
            first_name="Other",
            last_name="Customer",
            phone="03009990002",
            address_line="Other Notification Street",
            city="Karachi",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Notification Fiber 50",
            code="NOTIF-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="NOTIF-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.preference = NotificationPreference.objects.create(
            organization=self.organization,
            customer=self.customer,
            sms_enabled=True,
            whatsapp_enabled=True,
        )

        NotificationPreference.objects.create(
            organization=self.other_organization,
            customer=self.other_customer,
            sms_enabled=True,
            whatsapp_enabled=True,
        )

    def queue_sms(self):
        return queue_customer_notification(
            organization=self.organization,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            channel=NotificationJob.Channel.SMS,
            event_type="SERVICE_STATUS_CHANGED",
            subject="Service Update",
            message="Your service status has changed.",
            context={
                "service_number": self.service.service_number,
            },
            actor=self.actor,
        ).notification_job

    def test_queue_customer_notification(self):
        notification_job = self.queue_sms()

        self.assertEqual(
            notification_job.status,
            NotificationJob.Status.PENDING,
        )
        self.assertEqual(
            notification_job.recipient,
            self.customer.phone,
        )
        self.assertEqual(
            notification_job.service_account,
            self.service,
        )
        self.assertEqual(
            notification_job.attempt_count,
            0,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="NOTIFICATION_JOB_QUEUED",
                resource_type="NotificationJob",
                resource_id=notification_job.id,
            ).exists()
        )

    def test_disabled_channel_is_blocked(self):
        self.preference.sms_enabled = False
        self.preference.save()

        with self.assertRaises(NotificationDomainError):
            self.queue_sms()

        self.assertEqual(
            NotificationJob.objects.count(),
            0,
        )

    def test_cross_tenant_customer_is_blocked(self):
        with self.assertRaises(NotificationDomainError):
            queue_customer_notification(
                organization=self.organization,
                customer_id=self.other_customer.id,
                channel=NotificationJob.Channel.SMS,
                event_type="TEST_EVENT",
                message="Cross tenant notification.",
            )

        self.assertEqual(
            NotificationJob.objects.count(),
            0,
        )

    def test_service_must_belong_to_customer(self):
        second_customer = Customer.objects.create(
            organization=self.organization,
            customer_number="NOTIF-CUST-002",
            first_name="Second",
            last_name="Customer",
            phone="03009990003",
            address_line="Second Street",
            city="Lahore",
        )

        second_package = InternetPackage.objects.create(
            organization=self.organization,
            name="Notification Fiber 100",
            code="NOTIF-100",
            download_speed_mbps=100,
            upload_speed_mbps=50,
            monthly_price="8000.00",
        )

        second_service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="NOTIF-SRV-002",
            customer=second_customer,
            internet_package=second_package,
            status=ServiceAccount.Status.ACTIVE,
        )

        with self.assertRaises(NotificationDomainError):
            queue_customer_notification(
                organization=self.organization,
                customer_id=self.customer.id,
                service_account_id=second_service.id,
                channel=NotificationJob.Channel.SMS,
                event_type="TEST_EVENT",
                message="Invalid service context.",
            )

    def test_notification_processing_to_sent_lifecycle(self):
        notification_job = self.queue_sms()

        start_notification_processing(
            organization=self.organization,
            notification_job_id=notification_job.id,
            provider_name="Test SMS Provider",
            actor=self.actor,
        )

        notification_job.refresh_from_db()

        self.assertEqual(
            notification_job.status,
            NotificationJob.Status.PROCESSING,
        )
        self.assertEqual(
            notification_job.attempt_count,
            1,
        )
        self.assertIsNotNone(
            notification_job.processing_started_at,
        )

        mark_notification_sent(
            organization=self.organization,
            notification_job_id=notification_job.id,
            provider_message_id="provider-message-001",
            actor=self.actor,
        )

        notification_job.refresh_from_db()

        self.assertEqual(
            notification_job.status,
            NotificationJob.Status.SENT,
        )
        self.assertEqual(
            notification_job.provider_message_id,
            "provider-message-001",
        )
        self.assertIsNotNone(
            notification_job.sent_at,
        )

        self.assertEqual(
            AuditLog.objects.filter(
                organization=self.organization,
                resource_type="NotificationJob",
                resource_id=notification_job.id,
            ).count(),
            3,
        )

    def test_notification_processing_to_failed_lifecycle(self):
        notification_job = self.queue_sms()

        start_notification_processing(
            organization=self.organization,
            notification_job_id=notification_job.id,
            provider_name="Test WhatsApp Provider",
            actor=self.actor,
        )

        mark_notification_failed(
            organization=self.organization,
            notification_job_id=notification_job.id,
            failure_reason="Provider rejected message.",
            actor=self.actor,
        )

        notification_job.refresh_from_db()

        self.assertEqual(
            notification_job.status,
            NotificationJob.Status.FAILED,
        )
        self.assertEqual(
            notification_job.failure_reason,
            "Provider rejected message.",
        )
        self.assertIsNotNone(
            notification_job.failed_at,
        )
        self.assertIsNone(
            notification_job.sent_at,
        )

        self.assertEqual(
            AuditLog.objects.filter(
                organization=self.organization,
                resource_type="NotificationJob",
                resource_id=notification_job.id,
            ).count(),
            3,
        )

    def test_pending_job_cannot_be_marked_sent(self):
        notification_job = self.queue_sms()

        with self.assertRaises(NotificationDomainError):
            mark_notification_sent(
                organization=self.organization,
                notification_job_id=notification_job.id,
                provider_message_id="fake-success",
            )

        notification_job.refresh_from_db()

        self.assertEqual(
            notification_job.status,
            NotificationJob.Status.PENDING,
        )

    def test_pending_job_cannot_be_marked_failed(self):
        notification_job = self.queue_sms()

        with self.assertRaises(NotificationDomainError):
            mark_notification_failed(
                organization=self.organization,
                notification_job_id=notification_job.id,
                failure_reason="Fake failure.",
            )

        notification_job.refresh_from_db()

        self.assertEqual(
            notification_job.status,
            NotificationJob.Status.PENDING,
        )

    def test_cross_tenant_processing_is_blocked(self):
        notification_job = self.queue_sms()

        with self.assertRaises(NotificationDomainError):
            start_notification_processing(
                organization=self.other_organization,
                notification_job_id=notification_job.id,
                provider_name="Invalid Provider",
            )

        notification_job.refresh_from_db()

        self.assertEqual(
            notification_job.status,
            NotificationJob.Status.PENDING,
        )

class NotificationOperationalAPITests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Notification API ISP",
            code="NOTIF-API",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Notification API ISP",
            code="OTHER-NOTIF-API",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        User = get_user_model()

        self.owner = User.objects.create_user(
            username="notification-api-owner",
            email="notification-api-owner@nexora.test",
            password="StrongPass123!",
            first_name="Notification",
            last_name="API Owner",
        )

        self.other_owner = User.objects.create_user(
            username="other-notification-api-owner",
            email="other-notification-api-owner@nexora.test",
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
            customer_number="NOTIF-API-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03008880001",
            address_line="Notification API Street",
            city="Lahore",
        )

        self.other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-NOTIF-API-CUST",
            first_name="Other",
            last_name="Customer",
            phone="03008880002",
            address_line="Other Notification API Street",
            city="Karachi",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Notification API Fiber 50",
            code="NOTIF-API-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="NOTIF-API-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        NotificationPreference.objects.create(
            organization=self.organization,
            customer=self.customer,
            sms_enabled=True,
            whatsapp_enabled=True,
        )

        NotificationPreference.objects.create(
            organization=self.other_organization,
            customer=self.other_customer,
            sms_enabled=True,
            whatsapp_enabled=True,
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

    def queue_notification(self, *, channel=None):
        return queue_customer_notification(
            organization=self.organization,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            channel=(
                channel
                or NotificationJob.Channel.SMS
            ),
            event_type="SERVICE_STATUS_CHANGED",
            subject="Service Update",
            message="Your service status has changed.",
            context={
                "service_number": self.service.service_number,
            },
            actor=self.owner,
        ).notification_job

    def test_queue_notification_api(self):
        self.authenticate()

        response = self.client.post(
            "/api/v1/notifications/jobs/",
            {
                "customer_id": str(self.customer.id),
                "service_account_id": str(self.service.id),
                "channel": NotificationJob.Channel.SMS,
                "event_type": "MANUAL_SERVICE_UPDATE",
                "subject": "Service Update",
                "message": "Your service has been updated.",
                "context": {
                    "source": "operations",
                },
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        notification_job = NotificationJob.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            notification_job.organization,
            self.organization,
        )
        self.assertEqual(
            notification_job.status,
            NotificationJob.Status.PENDING,
        )
        self.assertEqual(
            notification_job.customer,
            self.customer,
        )

    def test_notification_list_and_search_api(self):
        notification_job = self.queue_notification()

        self.authenticate()

        response = self.client.get(
            "/api/v1/notifications/jobs/",
            {
                "search": self.customer.customer_number,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            str(notification_job.id),
        )

    def test_notification_status_filter_api(self):
        self.queue_notification()

        whatsapp_job = self.queue_notification(
            channel=NotificationJob.Channel.WHATSAPP,
        )

        start_notification_processing(
            organization=self.organization,
            notification_job_id=whatsapp_job.id,
            provider_name="Test Provider",
            actor=self.owner,
        )

        self.authenticate()

        response = self.client.get(
            "/api/v1/notifications/jobs/",
            {
                "status": NotificationJob.Status.PROCESSING,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            str(whatsapp_job.id),
        )

    def test_notification_detail_api(self):
        notification_job = self.queue_notification()

        self.authenticate()

        response = self.client.get(
            (
                "/api/v1/notifications/jobs/"
                f"{notification_job.id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["customer_number"],
            self.customer.customer_number,
        )
        self.assertEqual(
            response.data["service_number"],
            self.service.service_number,
        )

    def test_cross_tenant_detail_returns_404(self):
        notification_job = self.queue_notification()

        self.authenticate(
            user=self.other_owner,
            organization=self.other_organization,
        )

        response = self.client.get(
            (
                "/api/v1/notifications/jobs/"
                f"{notification_job.id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_cross_tenant_queue_customer_is_blocked(self):
        self.authenticate()

        response = self.client.post(
            "/api/v1/notifications/jobs/",
            {
                "customer_id": str(self.other_customer.id),
                "channel": NotificationJob.Channel.SMS,
                "event_type": "INVALID_CROSS_TENANT",
                "message": "Cross tenant message.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_notification_summary_api(self):
        pending_job = self.queue_notification()

        processing_job = self.queue_notification(
            channel=NotificationJob.Channel.WHATSAPP,
        )

        sent_job = self.queue_notification()

        failed_job = self.queue_notification(
            channel=NotificationJob.Channel.WHATSAPP,
        )

        start_notification_processing(
            organization=self.organization,
            notification_job_id=processing_job.id,
            provider_name="Processing Provider",
            actor=self.owner,
        )

        start_notification_processing(
            organization=self.organization,
            notification_job_id=sent_job.id,
            provider_name="Sent Provider",
            actor=self.owner,
        )

        mark_notification_sent(
            organization=self.organization,
            notification_job_id=sent_job.id,
            provider_message_id="sent-message-001",
            actor=self.owner,
        )

        start_notification_processing(
            organization=self.organization,
            notification_job_id=failed_job.id,
            provider_name="Failed Provider",
            actor=self.owner,
        )

        mark_notification_failed(
            organization=self.organization,
            notification_job_id=failed_job.id,
            failure_reason="Provider rejected message.",
            actor=self.owner,
        )

        self.authenticate()

        response = self.client.get(
            "/api/v1/notifications/summary/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["total"], 4)
        self.assertEqual(response.data["pending"], 1)
        self.assertEqual(response.data["processing"], 1)
        self.assertEqual(response.data["sent"], 1)
        self.assertEqual(response.data["failed"], 1)
        self.assertEqual(response.data["cancelled"], 0)
        self.assertEqual(response.data["sms"], 2)
        self.assertEqual(response.data["whatsapp"], 2)

        self.assertEqual(
            pending_job.status,
            NotificationJob.Status.PENDING,
        )

    def test_unauthenticated_notification_api_is_blocked(self):
        response = self.client.get(
            "/api/v1/notifications/jobs/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )