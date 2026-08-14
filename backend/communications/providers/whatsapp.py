import logging

import requests
from django.conf import settings

from .base import BaseCommunicationProvider

logger = logging.getLogger(__name__)


class WhatsAppCloudProvider(BaseCommunicationProvider):
    """Meta WhatsApp Cloud API Provider."""

    @staticmethod
    def _safe_response(data):
        """Keep only non-sensitive provider metadata for persistence."""
        if not isinstance(data, dict):
            return {}

        safe = {}

        messages = data.get("messages")
        if isinstance(messages, list) and messages:
            message_id = messages[0].get("id") if isinstance(messages[0], dict) else None
            if message_id:
                safe["message_id"] = message_id

        error = data.get("error")
        if isinstance(error, dict):
            for key in ("type", "code", "error_subcode"):
                value = error.get(key)
                if value is not None:
                    safe[key] = value

        return safe

    def send(
        self,
        *,
        recipient,
        subject="",
        message="",
        provider,
    ):
        recipient = (
            str(recipient)
            .replace("+", "")
            .replace("-", "")
            .replace(" ", "")
        )

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
            "text": {"body": message},
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
            except ValueError:
                data = {}

            safe_response = self._safe_response(data)

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
                    "retryable": response.status_code in {429, 500, 502, 503, 504},
                    "response": safe_response,
                    "error": error_message,
                }

            message_id = None
            messages = data.get("messages")
            if isinstance(messages, list) and messages:
                first_message = messages[0]
                if isinstance(first_message, dict):
                    message_id = first_message.get("id")

            logger.info(
                "WhatsApp message accepted by provider with status %s",
                response.status_code,
            )

            return {
                "success": True,
                "provider_message_id": message_id,
                "status_code": response.status_code,
                "retryable": False,
                "response": safe_response,
                "error": "",
            }

        except requests.RequestException:
            logger.exception("WhatsApp provider request failed unexpectedly.")
            return {
                "success": False,
                "provider_message_id": "",
                "status_code": None,
                "retryable": True,
                "response": {},
                "error": "WhatsApp provider request failed.",
            }
