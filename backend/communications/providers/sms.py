from .base import BaseCommunicationProvider


class SMSProvider(BaseCommunicationProvider):
    """
    SMS provider contract.

    A real gateway implementation must replace this class before SMS is
    enabled for a tenant. We intentionally fail closed instead of reporting
    a message as sent when no gateway is configured.
    """

    def send(
        self,
        *,
        recipient,
        subject="",
        message="",
        provider,
    ):
        return {
            "success": False,
            "provider_message_id": "",
            "status_code": None,
            "retryable": False,
            "response": {"status": "not_configured"},
            "error": "SMS provider is not configured.",
        }
