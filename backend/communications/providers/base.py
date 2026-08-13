from abc import ABC, abstractmethod


class BaseCommunicationProvider(ABC):
    """
    Base class for all communication providers.
    """

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

        Must return:

        {
            "success": bool,
            "provider_message_id": str,
            "response": dict,
            "error": str,
        }
        """
        raise NotImplementedError