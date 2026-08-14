from django.core.mail import EmailMessage

from .base import BaseCommunicationProvider


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
                "status_code": None,
                "retryable": False,
                "response": {"status": "accepted"},
                "error": "",
            }
        except Exception:
            return {
                "success": False,
                "provider_message_id": "",
                "status_code": None,
                "retryable": True,
                "response": {},
                "error": "Email provider request failed.",
            }
