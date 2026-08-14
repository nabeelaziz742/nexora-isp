from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from communications.dispatcher import CommunicationDispatcher
from communications.models import (
    CommunicationLog,
    CommunicationProvider,
    CommunicationQueue,
    CommunicationTemplate,
)
from customers.models import Customer
from tenancy.models import Organization


class CommunicationDispatcherTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test ISP",
            code="TEST-ISP",
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="CUST-001",
            first_name="Test",
            last_name="Customer",
            phone="03000000000",
            address_line="Test Address",
            city="Lahore",
        )

        self.provider = CommunicationProvider.objects.create(
            organization=self.organization,
            name="Test SMS",
            provider_type=CommunicationProvider.ProviderType.SMS,
        )

        self.template = CommunicationTemplate.objects.create(
            organization=self.organization,
            name="Test Template",
            body="Test message",
            communication_provider=self.provider,
        )

    def create_queue(self, **overrides):
        values = {
            "organization": self.organization,
            "customer": self.customer,
            "template": self.template,
            "provider": self.provider,
            "recipient": self.customer.phone,
            "rendered_subject": "",
            "rendered_body": "Test message",
            "scheduled_at": timezone.now() - timedelta(minutes=1),
        }
        values.update(overrides)
        return CommunicationQueue.objects.create(**values)

    def create_log(self, queue):
        return CommunicationLog.objects.create(
            organization=self.organization,
            queue=queue,
            recipient=queue.recipient,
            subject=queue.rendered_subject,
            message=queue.rendered_body,
        )

    @patch("communications.dispatcher.ProviderFactory.get")
    def test_provider_acceptance_marks_log_sent_not_delivered(self, get_provider):
        provider = Mock()
        provider.send.return_value = {
            "success": True,
            "provider_message_id": "provider-message-1",
            "response": {"status": "accepted"},
        }
        get_provider.return_value = provider

        queue = self.create_queue()
        self.create_log(queue)

        result = CommunicationDispatcher.dispatch_next()

        queue.refresh_from_db()
        log = CommunicationLog.objects.get(queue=queue)

        self.assertTrue(result)
        self.assertEqual(queue.status, CommunicationQueue.Status.SENT)
        self.assertIsNotNone(queue.sent_at)
        self.assertIsNone(queue.next_retry_at)
        self.assertEqual(log.status, CommunicationLog.Status.SENT)
        self.assertEqual(log.provider_message_id, "provider-message-1")

    def test_future_retry_is_not_dispatched(self):
        queue = self.create_queue(
            next_retry_at=timezone.now() + timedelta(minutes=10),
            attempts=1,
        )

        result = CommunicationDispatcher.dispatch_next()

        queue.refresh_from_db()

        self.assertIsNone(result)
        self.assertEqual(queue.status, CommunicationQueue.Status.PENDING)
        self.assertEqual(queue.attempts, 1)

    @patch("communications.dispatcher.ProviderFactory.get")
    def test_retryable_failure_is_scheduled_for_retry(self, get_provider):
        provider = Mock()
        provider.send.return_value = {
            "success": False,
            "retryable": True,
            "provider_message_id": "",
            "response": {"status": "unavailable"},
            "error": "Provider unavailable",
        }
        get_provider.return_value = provider

        queue = self.create_queue()
        before = timezone.now()

        result = CommunicationDispatcher.process(queue)

        queue.refresh_from_db()

        self.assertFalse(result)
        self.assertEqual(queue.status, CommunicationQueue.Status.PENDING)
        self.assertEqual(queue.attempts, 1)
        self.assertEqual(queue.retry_count, 1)
        self.assertEqual(queue.last_error, "Provider unavailable")
        self.assertIsNotNone(queue.next_retry_at)
        self.assertGreater(queue.next_retry_at, before)

    @patch("communications.dispatcher.ProviderFactory.get")
    def test_non_retryable_failure_is_failed_immediately(self, get_provider):
        provider = Mock()
        provider.send.return_value = {
            "success": False,
            "retryable": False,
            "provider_message_id": "",
            "response": {"status": "invalid_request"},
            "error": "Invalid recipient",
        }
        get_provider.return_value = provider

        queue = self.create_queue()

        result = CommunicationDispatcher.process(queue)

        queue.refresh_from_db()

        self.assertFalse(result)
        self.assertEqual(queue.status, CommunicationQueue.Status.FAILED)
        self.assertEqual(queue.attempts, 1)
        self.assertIsNone(queue.next_retry_at)
        self.assertEqual(queue.last_error, "Invalid recipient")

    @patch("communications.dispatcher.ProviderFactory.get")
    def test_max_attempts_marks_queue_failed(self, get_provider):
        provider = Mock()
        provider.send.return_value = {
            "success": False,
            "retryable": True,
            "provider_message_id": "",
            "response": {"status": "failed"},
            "error": "Provider unavailable",
        }
        get_provider.return_value = provider

        queue = self.create_queue(
            attempts=2,
            max_attempts=3,
        )

        result = CommunicationDispatcher.process(queue)

        queue.refresh_from_db()

        self.assertFalse(result)
        self.assertEqual(queue.status, CommunicationQueue.Status.FAILED)
        self.assertEqual(queue.attempts, 3)
        self.assertIsNone(queue.next_retry_at)

    def test_stale_processing_item_is_recovered(self):
        stale_time = timezone.now() - timedelta(minutes=30)

        queue = self.create_queue(
            status=CommunicationQueue.Status.PROCESSING,
            processing_started_at=stale_time,
        )

        CommunicationDispatcher.recover_stale_processing(timezone.now())

        queue.refresh_from_db()

        self.assertEqual(queue.status, CommunicationQueue.Status.PENDING)
        self.assertIsNone(queue.processing_started_at)
        self.assertIsNotNone(queue.next_retry_at)
        self.assertIn("Recovered stale processing", queue.last_error)

    def test_future_scheduled_item_is_not_dispatched(self):
        queue = self.create_queue(
            scheduled_at=timezone.now() + timedelta(minutes=10),
        )

        result = CommunicationDispatcher.dispatch_next()

        queue.refresh_from_db()

        self.assertIsNone(result)
        self.assertEqual(queue.status, CommunicationQueue.Status.PENDING)
