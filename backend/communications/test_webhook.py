import hashlib
import hmac

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from .views import WhatsAppWebhookAPIView


class WhatsAppWebhookSecurityTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = WhatsAppWebhookAPIView.as_view()

    @override_settings(WHATSAPP_VERIFY_TOKEN="test-verify-token")
    def test_get_verification_accepts_configured_token(self):
        request = self.factory.get(
            "/api/v1/communications/webhook/whatsapp/",
            {
                "hub.mode": "subscribe",
                "hub.challenge": "challenge-123",
                "hub.verify_token": "test-verify-token",
            },
        )

        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"challenge-123")

    @override_settings(WHATSAPP_VERIFY_TOKEN="test-verify-token")
    def test_get_verification_rejects_wrong_token(self):
        request = self.factory.get(
            "/api/v1/communications/webhook/whatsapp/",
            {
                "hub.mode": "subscribe",
                "hub.challenge": "challenge-123",
                "hub.verify_token": "wrong-token",
            },
        )

        response = self.view(request)

        self.assertEqual(response.status_code, 403)

    @override_settings(WHATSAPP_APP_SECRET="test-app-secret")
    def test_post_rejects_invalid_signature(self):
        payload = b'{"entry": []}'
        request = self.factory.post(
            "/api/v1/communications/webhook/whatsapp/",
            data=payload,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=invalid",
        )

        response = self.view(request)

        self.assertEqual(response.status_code, 403)

    @override_settings(WHATSAPP_APP_SECRET="test-app-secret")
    def test_signature_helper_accepts_valid_signature(self):
        payload = b'{"entry": []}'
        signature = "sha256=" + hmac.new(
            b"test-app-secret",
            payload,
            hashlib.sha256,
        ).hexdigest()
        request = self.factory.post(
            "/api/v1/communications/webhook/whatsapp/",
            data=payload,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

        view = WhatsAppWebhookAPIView()

        self.assertTrue(view._valid_signature(request))
