import logging

from django.core.mail import EmailMessage

from .base import BaseCommunicationProvider

logger = logging.getLogger(__name__)


class EmailProvider(BaseCommunicationProvider):
    """
    SMTP Email Provider.
    Uses Django EMAIL_BACKEND settings.
    """

    def send(
        self,
        *,
        recipient,
        subject="",
        message="",
        provider,
    ):
        try:

            email = EmailMessage(
                subject=subject,
                body=message,
                to=[recipient],
            )

            email.send(fail_silently=False)

            return {
                "success": True,
                "provider_message_id": "",
                "response": {
                    "status": "sent",
                },
                "error": "",
            }

        except Exception as exc:

            logger.exception(exc)

            return {
                "success": False,
                "provider_message_id": "",
                "response": {},
                "error": str(exc),
            }