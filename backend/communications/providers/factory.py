from communications.models import CommunicationProvider

from .email import EmailProvider
from .sms import SMSProvider
from .whatsapp import WhatsAppCloudProvider


class ProviderFactory:
    """
    Returns the correct provider implementation.
    """

    PROVIDERS = {
        CommunicationProvider.ProviderType.WHATSAPP: WhatsAppCloudProvider,
        CommunicationProvider.ProviderType.EMAIL: EmailProvider,
        CommunicationProvider.ProviderType.SMS: SMSProvider,
    }

    @classmethod
    def get(cls, provider):
        provider_class = cls.PROVIDERS.get(
            provider.provider_type,
        )

        if provider_class is None:
            raise ValueError(
                f"Unsupported provider type: "
                f"{provider.provider_type}"
            )

        return provider_class()