from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError

from communications.models import CommunicationProvider, CommunicationTemplate
from communications.providers.sms import SMSProvider
from communications.providers.whatsapp import WhatsAppCloudProvider
from communications.serializers import CommunicationProviderSerializer
from tenancy.models import Organization


class CommunicationProviderSecurityTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test ISP",
            code="COMM-SEC",
        )
        self.other_organization = Organization.objects.create(
            name="Other ISP",
            code="COMM-OTHER",
        )

    def serializer_context(self):
        request = SimpleNamespace(organization=self.organization)
        return {"request": request}

    def test_provider_credentials_are_not_serialized(self):
        provider = CommunicationProvider.objects.create(
            organization=self.organization,
            name="WhatsApp",
            provider_type=CommunicationProvider.ProviderType.WHATSAPP,
            access_token="secret-token",
            webhook_verify_token="verify-secret",
        )

        data = CommunicationProviderSerializer(provider).data

        self.assertNotIn("access_token", data)
        self.assertNotIn("webhook_verify_token", data)

    def test_template_cannot_reference_provider_from_another_tenant(self):
        provider = CommunicationProvider.objects.create(
            organization=self.other_organization,
            name="Other WhatsApp",
            provider_type=CommunicationProvider.ProviderType.WHATSAPP,
        )

        serializer = CommunicationProviderSerializer(
            provider,
            context=self.serializer_context(),
        )

        self.assertEqual(serializer.data["name"], "Other WhatsApp")


class CommunicationProviderBehaviorTests(SimpleTestCase):
    def test_sms_provider_fails_closed_when_not_configured(self):
        result = SMSProvider().send(
            recipient="03000000000",
            message="Test",
            provider=SimpleNamespace(),
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["retryable"])
        self.assertEqual(result["error"], "SMS provider is not configured.")

    @patch("communications.providers.whatsapp.requests.post")
    def test_whatsapp_persisted_response_is_redacted(self, mock_post):
        mock_post.return_value = SimpleNamespace(
            ok=True,
            status_code=200,
            json=lambda: {
                "messages": [{"id": "wamid.test"}],
                "contacts": [{"wa_id": "03000000000"}],
            },
        )

        provider = SimpleNamespace(
            phone_number_id="phone-123",
            access_token="secret-token",
        )

        result = WhatsAppCloudProvider().send(
            recipient="03000000000",
            message="Sensitive message",
            provider=provider,
        )

        self.assertEqual(result["response"], {"message_id": "wamid.test"})
        self.assertNotIn("03000000000", str(result["response"]))
        self.assertNotIn("Sensitive message", str(result["response"]))
