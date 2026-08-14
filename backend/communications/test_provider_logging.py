from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from .providers.whatsapp import WhatsAppCloudProvider


class WhatsAppProviderLoggingTests(SimpleTestCase):
    @patch("communications.providers.whatsapp.requests.post")
    def test_send_does_not_print_message_payload(self, mock_post):
        mock_post.return_value = SimpleNamespace(
            ok=True,
            status_code=200,
            json=lambda: {"messages": [{"id": "wamid.test"}]},
            text='{"messages":[{"id":"wamid.test"}]}',
        )
        provider = SimpleNamespace(
            phone_number_id="phone-123",
            access_token="secret-token",
        )

        with self.assertLogs(
            "communications.providers.whatsapp",
            level="INFO",
        ) as logs:
            result = WhatsAppCloudProvider().send(
                recipient="03001234567",
                message="Sensitive customer message",
                provider=provider,
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["provider_message_id"], "wamid.test")
        output = "\n".join(logs.output)
        self.assertNotIn("Sensitive customer message", output)
        self.assertNotIn("03001234567", output)
        self.assertNotIn("secret-token", output)
        self.assertNotIn("Sensitive customer message", output)
