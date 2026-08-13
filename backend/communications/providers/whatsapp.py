import logging

import requests
from django.conf import settings

from .base import BaseCommunicationProvider

logger = logging.getLogger(__name__)


class WhatsAppCloudProvider(BaseCommunicationProvider):
    """
    Meta WhatsApp Cloud API Provider
    """

    def send(
        self,
        *,
        recipient,
        subject="",
        message="",
        provider,
    ):
        """
        Send WhatsApp message through Meta Cloud API.
        """

        recipient = (
            str(recipient)
            .replace("+", "")
            .replace("-", "")
            .replace(" ", "")
        )

        # Convert Pakistani local number to E.164
        if recipient.startswith("0"):
            recipient = "92" + recipient[1:]

        if not message:
            return {
                "success": False,
                "provider_message_id": "",
                "status_code": None,
                "retryable": False,
                "response": {},
                "error": "Message cannot be empty.",
            }

        url = (
            f"https://graph.facebook.com/"
            f"{settings.WHATSAPP_API_VERSION}/"
            f"{provider.phone_number_id}/messages"
        )

        headers = {
            "Authorization": f"Bearer {provider.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {
                "body": message,
            },
        }

        try:
            print("\n========== META REQUEST ==========")
            print("URL:", url)
            print("Recipient:", recipient)
            print("Payload:", payload)
            print("==================================")

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30,
            )

            print("\n========== META RESPONSE =========")
            print("Status:", response.status_code)
            print("Body:", response.text)
            print("==================================\n")

            try:
                data = response.json()
            except Exception:
                data = {
                    "raw": response.text,
                }

            if not response.ok:
                return {
                    "success": False,
                    "provider_message_id": "",
                    "status_code": response.status_code,
                    "retryable": response.status_code in {
                        429,
                        500,
                        502,
                        503,
                        504,
                    },
                    "response": data,
                    "error": data.get("error", {}).get("message", response.text),
                }

            message_id = None

            if data.get("messages"):
                message_id = data["messages"][0].get("id")

            logger.info(
                "WhatsApp message sent successfully to %s",
                recipient,
            )

            return {
                "success": True,
                "provider_message_id": message_id,
                "status_code": response.status_code,
                "retryable": False,
                "response": data,
                "error": "",
            }

        except Exception as exc:
            logger.exception(
                "WhatsApp send failed for recipient %s",
                recipient,
            )

            return {
                "success": False,
                "provider_message_id": "",
                "status_code": None,
                "retryable": True,
                "response": {},
                "error": str(exc),
            }