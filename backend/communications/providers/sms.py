import logging

from .base import BaseCommunicationProvider

logger = logging.getLogger(__name__)


class SMSProvider(BaseCommunicationProvider):
    """
    Placeholder SMS Provider.

    Replace this class with your preferred
    SMS gateway implementation.
    """

    def send(
        self,
        *,
        recipient,
        subject="",
        message="",
        provider,
    ):
        logger.info(
            "SMS placeholder: %s",
            recipient,
        )

        return {
            "success": True,
            "provider_message_id": "",
            "response": {
                "status": "queued",
                "recipient": recipient,
                "message": message,
            },
            "error": "",
        }