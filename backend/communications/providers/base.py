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
    ):
        """
        Send a communication.

        Must return a dictionary containing at least:
        success, provider_message_id, response, error, retryable.
        """
        raise NotImplementedError

    def health_check(self, *, provider):
        """Validate provider connectivity without sending a customer message."""
        return {
            "success": False,
            "message": "Provider health check is not implemented.",
        }
