from abc import ABC, abstractmethod


class BaseCommunicationProvider(ABC):
    """Base class for communication providers."""

    @abstractmethod
    def send(
        self,
        *,
        recipient,
        subject="",
        message="",
        provider,
        template_message=None,
    ):
        """
        Send a communication.

        `template_message` is an optional pre-approved template
        ({"name", "language", "parameters"}) for channels that support it;
        other channels ignore it and send `message`.

        Must return a dictionary containing at least:
        success, provider_message_id, response, error, retryable.
        """
        raise NotImplementedError

    def is_configured(self, *, provider):
        """Return True when the provider has what it needs to send externally."""
        return True

    def health_check(self, *, provider):
        """Validate provider connectivity without sending a customer message."""
        return {
            "success": False,
            "message": "Provider health check is not implemented.",
        }
