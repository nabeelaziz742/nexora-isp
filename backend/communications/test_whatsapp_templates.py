from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase

from billing.automation import process_invoice_collection
from billing.models import Invoice, InvoiceLine
from communications.dispatcher import CommunicationDispatcher
from communications.models import (
    CommunicationProvider,
    CommunicationQueue,
    CommunicationTemplate,
)
from communications.notification_engine import NotificationEvent, dispatch_notification_event
from communications.providers.whatsapp import WhatsAppCloudProvider
from communications.serializers import CommunicationTemplateSerializer
from customers.models import (
    BillingProfile,
    Customer,
    InternetPackage,
    NotificationPreference,
    ServiceAccount,
)
from notifications.models import NotificationJob
from tenancy.models import Organization


def meta_ok(message_id="wamid.test"):
    return Mock(ok=True, status_code=200, json=Mock(return_value={"messages": [{"id": message_id}]}))


class WhatsAppTemplateFixtureMixin:
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name="Template ISP",
            code="TEMPLATE-ISP",
            city="Lahore",
            currency="PKR",
        )
        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="TPL-CUST-001",
            first_name="Hina",
            last_name="Raza",
            phone="03001112222",
            address_line="Street 7",
            city="Lahore",
        )
        NotificationPreference.objects.create(
            organization=self.organization,
            customer=self.customer,
            whatsapp_enabled=True,
            sms_enabled=False,
        )
        self.provider = CommunicationProvider.objects.create(
            organization=self.organization,
            name="WhatsApp",
            provider_type=CommunicationProvider.ProviderType.WHATSAPP,
            phone_number_id="123456",
            access_token="token",
            is_connected=True,
        )

    def sent_payload(self, mock_post):
        mock_post.assert_called_once()
        return mock_post.call_args.kwargs["json"]


class WhatsAppProviderTemplateTests(WhatsAppTemplateFixtureMixin, TestCase):
    @patch("communications.providers.whatsapp.requests.post")
    def test_template_message_uses_meta_template_payload(self, mock_post):
        mock_post.return_value = meta_ok()

        result = WhatsAppCloudProvider().send(
            recipient="0300-1112222",
            message="ignored body",
            provider=self.provider,
            template_message={
                "name": "nexora_bill_overdue",
                "language": "en",
                "parameters": ["Hina Raza", "2500.00", "", "2026-11-10"],
            },
        )

        self.assertTrue(result["success"])
        payload = self.sent_payload(mock_post)
        self.assertEqual(payload["to"], "923001112222")
        self.assertEqual(payload["type"], "template")
        self.assertEqual(payload["template"]["name"], "nexora_bill_overdue")
        self.assertEqual(payload["template"]["language"], {"code": "en"})
        texts = [p["text"] for p in payload["template"]["components"][0]["parameters"]]
        self.assertEqual(texts, ["Hina Raza", "2500.00", "-", "2026-11-10"])

    @patch("communications.providers.whatsapp.requests.post")
    def test_without_template_plain_text_is_sent(self, mock_post):
        mock_post.return_value = meta_ok()

        WhatsAppCloudProvider().send(recipient="03001112222", message="Hello", provider=self.provider)

        payload = self.sent_payload(mock_post)
        self.assertEqual(payload["type"], "text")
        self.assertEqual(payload["text"], {"body": "Hello"})

    @patch("communications.providers.whatsapp.requests.post")
    def test_template_without_parameters_has_no_components(self, mock_post):
        mock_post.return_value = meta_ok()

        WhatsAppCloudProvider().send(
            recipient="03001112222",
            provider=self.provider,
            template_message={"name": "hello_world", "language": "en_US", "parameters": []},
        )

        template = self.sent_payload(mock_post)["template"]
        self.assertNotIn("components", template)
        self.assertEqual(template["language"], {"code": "en_US"})


class DispatcherTemplateTests(WhatsAppTemplateFixtureMixin, TestCase):
    def test_parameters_follow_template_order_from_payload(self):
        template = CommunicationTemplate.objects.create(
            organization=self.organization,
            name="Overdue",
            body="Body",
            communication_provider=self.provider,
            whatsapp_template_name="nexora_bill_overdue",
            whatsapp_template_language="en",
            whatsapp_template_params=["customer_name", "outstanding_amount", "missing"],
        )
        queue = CommunicationQueue(
            template=template,
            payload={"outstanding_amount": "2500.00", "customer_name": "Hina Raza"},
        )

        message = CommunicationDispatcher.build_template_message(queue)

        self.assertEqual(message["name"], "nexora_bill_overdue")
        self.assertEqual(message["parameters"], ["Hina Raza", "2500.00", ""])

    def test_template_without_meta_name_sends_text(self):
        template = CommunicationTemplate.objects.create(
            organization=self.organization,
            name="Plain",
            body="Body",
            communication_provider=self.provider,
        )

        self.assertIsNone(CommunicationDispatcher.build_template_message(CommunicationQueue(template=template)))

    @patch("communications.providers.whatsapp.requests.post")
    def test_event_notification_uses_default_meta_template(self, mock_post):
        mock_post.return_value = meta_ok()

        result = dispatch_notification_event(
            organization=self.organization,
            customer=self.customer,
            event_type=NotificationEvent.SERVICE_SUSPENDED,
            context={"service_number": "TPL-SRV-1", "outstanding_amount": Decimal("1500.00")},
        )

        self.assertEqual(result["queued_items"][0]["status"], CommunicationQueue.Status.SENT)
        template = self.sent_payload(mock_post)["template"]
        self.assertEqual(template["name"], "nexora_service_suspended")
        texts = [p["text"] for p in template["components"][0]["parameters"]]
        self.assertEqual(texts, ["Hina Raza", "TPL-SRV-1", "1500.00"])


class TemplateSerializerTests(WhatsAppTemplateFixtureMixin, TestCase):
    def serializer(self, **data):
        request = Mock(organization=self.organization)
        return CommunicationTemplateSerializer(
            data={
                "name": "Overdue",
                "body": "Dear {{customer_name}}",
                "communication_provider": str(self.provider.id),
                **data,
            },
            context={"request": request},
        )

    def test_valid_meta_template_fields(self):
        serializer = self.serializer(
            whatsapp_template_name="nexora_bill_overdue",
            whatsapp_template_params=["customer_name", " outstanding_amount "],
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["whatsapp_template_params"], ["customer_name", "outstanding_amount"])

    def test_invalid_meta_template_name_is_rejected(self):
        serializer = self.serializer(whatsapp_template_name="Bill Overdue!")

        self.assertFalse(serializer.is_valid())
        self.assertIn("whatsapp_template_name", serializer.errors)


class CollectionReminderDeliveryTests(WhatsAppTemplateFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 25",
            code="TPL-25",
            download_speed_mbps=25,
            upload_speed_mbps=10,
            monthly_price="2500.00",
        )
        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="TPL-SRV-001",
            customer=self.customer,
            internet_package=package,
            status=ServiceAccount.Status.ACTIVE,
        )
        profile = BillingProfile.objects.create(
            organization=self.organization,
            service_account=self.service,
            billing_day=1,
            due_day=10,
        )
        self.invoice = Invoice.objects.create(
            organization=self.organization,
            invoice_number="TPL-INV-0001",
            service_account=self.service,
            billing_profile=profile,
            billing_period_start=date(2026, 10, 1),
            billing_period_end=date(2026, 10, 31),
            issue_date=date(2026, 10, 1),
            due_date=date(2026, 10, 10),
            status=Invoice.Status.UNPAID,
        )
        InvoiceLine.objects.create(
            organization=self.organization,
            invoice=self.invoice,
            description="Monthly internet service",
            amount=Decimal("2500.00"),
        )

    def collect(self):
        return process_invoice_collection(
            organization=self.organization,
            invoice=self.invoice,
            as_of_date=date(2026, 10, 11),
            overdue_reminder_days=1,
            final_warning_days=7,
            suspension_days=15,
        )

    @patch("communications.providers.whatsapp.requests.post")
    def test_overdue_reminder_is_sent_on_whatsapp_with_template(self, mock_post):
        mock_post.return_value = meta_ok("wamid.overdue")

        result = self.collect()

        self.assertEqual(result.action, "OVERDUE_REMINDER")
        template = self.sent_payload(mock_post)["template"]
        self.assertEqual(template["name"], "nexora_bill_overdue")
        texts = [p["text"] for p in template["components"][0]["parameters"]]
        self.assertEqual(texts, ["Hina Raza", "2500.00", "TPL-INV-0001", "2026-10-10"])
        job = NotificationJob.objects.get(event_type="OVERDUE_REMINDER")
        self.assertEqual(job.status, NotificationJob.Status.SENT)
        self.assertEqual(job.provider_message_id, "wamid.overdue")

    @patch("communications.providers.whatsapp.requests.post")
    def test_rejected_reminder_marks_job_failed(self, mock_post):
        mock_post.return_value = Mock(
            ok=False,
            status_code=400,
            json=Mock(return_value={"error": {"message": "Template name does not exist", "code": 132001}}),
        )

        self.collect()

        job = NotificationJob.objects.get(event_type="OVERDUE_REMINDER")
        self.assertEqual(job.status, NotificationJob.Status.FAILED)
        self.assertIn("Template name does not exist", job.failure_reason)

    @patch("communications.providers.whatsapp.requests.post")
    def test_unconfigured_provider_marks_job_failed_without_calling_meta(self, mock_post):
        self.provider.is_connected = False
        self.provider.save()

        self.collect()

        mock_post.assert_not_called()
        job = NotificationJob.objects.get(event_type="OVERDUE_REMINDER")
        self.assertEqual(job.status, NotificationJob.Status.FAILED)
