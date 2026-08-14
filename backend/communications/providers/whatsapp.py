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
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30,
            )

            try:
                data = response.json()
            except Exception:
                data = {
                    "raw": response.text,
                }

            if not response.ok:
                error_data = data.get("error", {})
                error_message = (
                    error_data.get("message")
                    if isinstance(error_data, dict)
                    else None
                ) or "WhatsApp provider request failed."

                logger.warning(
                    "WhatsApp provider request failed with status %s",
                    response.status_code,
                )

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
                    "error": error_message,
                }

            message_id = None

            if data.get("messages"):
                message_id = data["messages"][0].get("id")

            logger.info(
                "WhatsApp message sent successfully with provider status %s",
                response.status_code,
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
                "WhatsApp provider request failed unexpectedly: %s",
                exc,
            )

            return {
                "success": False,
                "provider_message_id": "",
                "status_code": None,
                "retryable": True,
                "response": {},
                "error": str(exc),
            }
