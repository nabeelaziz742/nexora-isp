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

    def is_configured(self, *, provider):
        return bool(
            provider.is_connected
            and provider.phone_number_id
            and provider.access_token
        )

    def health_check(self, *, provider):
        if not provider.phone_number_id or not provider.access_token:
            return {
                "success": False,
                "message": "WhatsApp phone number ID and access token are required.",
            }

        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{provider.phone_number_id}"
        )

        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {provider.access_token}"},
                params={"fields": "id,display_phone_number,verified_name"},
                timeout=15,
            )
            if not response.ok:
                return {
                    "success": False,
                    "message": "WhatsApp provider authentication failed.",
                }
            return {"success": True, "message": "WhatsApp provider is reachable."}
        except requests.RequestException:
            logger.exception("WhatsApp provider health check failed.")
            return {
                "success": False,
                "message": "WhatsApp provider is unreachable.",
            }

    @staticmethod
    def _template_payload(template_message):
        """Build the Cloud API `template` object for an approved Meta template."""
        template = {
            "name": template_message["name"],
            "language": {"code": template_message.get("language") or "en"},
        }
        parameters = template_message.get("parameters") or []
        if parameters:
            template["components"] = [
                {
                    "type": "body",
                    # Meta rejects empty text parameters.
                    "parameters": [
                        {"type": "text", "text": str(value) if str(value).strip() else "-"}
                        for value in parameters
                    ],
                }
            ]
        return template

    def send(self, *, recipient, subject="", message="", provider, template_message=None):
        recipient = (
            str(recipient)
            .replace("+", "")
            .replace("-", "")
            .replace(" ", "")
        )
        if recipient.startswith("0"):
            recipient = "92" + recipient[1:]

        use_template = bool(template_message and template_message.get("name"))

        if not use_template and not message:
            return {
                "success": False,
                "provider_message_id": "",
                "status_code": None,
                "retryable": False,
                "response": {},
                "error": "Message cannot be empty.",
            }

        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{provider.phone_number_id}/messages"
        )
        headers = {
            "Authorization": f"Bearer {provider.access_token}",
            "Content-Type": "application/json",
        }
        if use_template:
            # Approved templates may be sent at any time; plain text only
            # reaches customers who messaged the business in the last 24 hours.
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "template",
                "template": self._template_payload(template_message),
            }
        else:
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
