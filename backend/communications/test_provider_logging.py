from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from .providers.whatsapp import WhatsAppCloudProvider


class WhatsAppProviderLoggingTests(SimpleTestCase):
    @patch("communications.providers.whatsapp.requests.post")
    def test_send_does_not_print_or_persist_message_payload(self, mock_post):
        mock_post.return_value = SimpleNamespace(
            ok=True,
            status_code=200,
            json=lambda: {
                "messages": [{"id": "wamid.test"}],
                "contacts": [{"wa_id": "03001234567"}],
            },
            text='{"messages":[{"id":"wamid.test"}]}',
        )
        provider = SimpleNamespace(
            phone_number_id="phone-123",
            access_token="secret-token",
        )
        stdout = StringIO()

        with self.assertLogs(
            "communications.providers.whatsapp",
            level="INFO",
        ) as logs, redirect_stdout(stdout):
            result = WhatsAppCloudProvider().send(
                recipient="03001234567",
                message="Sensitive customer message",
                provider=provider,
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["provider_message_id"], "wamid.test")
        self.assertEqual(result["response"], {"message_id": "wamid.test"})
        self.assertEqual(stdout.getvalue(), "")

        output = "\n".join(logs.output)
        self.assertNotIn("Sensitive customer message", output)
        self.assertNotIn("03001234567", output)
        self.assertNotIn("secret-token", output)
        self.assertNotIn("Sensitive customer message", str(result["response"]))
        self.assertNotIn("03001234567", str(result["response"]))
