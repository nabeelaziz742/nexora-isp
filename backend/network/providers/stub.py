from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from network.models import ProvisioningRequest


class ProvisioningProviderError(Exception):
    pass


@dataclass(frozen=True)
class ProvisioningProviderResult:
    provider_reference: str
    metadata: dict[str, Any]


class BaseProvisioningProvider(ABC):
    @abstractmethod
    def execute(
        self,
        *,
        provisioning_request: ProvisioningRequest,
    ) -> ProvisioningProviderResult:
        raise NotImplementedError


class StubProvisioningProvider(
    BaseProvisioningProvider
):
    """
    Safe development provisioning provider.

    No real router, OLT, RADIUS, BRAS, or external
    network infrastructure is contacted.
    """

    def execute(
        self,
        *,
        provisioning_request: ProvisioningRequest,
    ) -> ProvisioningProviderResult:
        action = provisioning_request.action

        supported_actions = {
            ProvisioningRequest.Action.ACTIVATE,
            ProvisioningRequest.Action.SUSPEND,
            ProvisioningRequest.Action.RESTORE,
            ProvisioningRequest.Action.CHANGE_PACKAGE,
        }

        if action not in supported_actions:
            raise ProvisioningProviderError(
                "Provisioning action is not supported "
                "by the stub provider."
            )

        provider_reference = (
            f"STUB-{action}-"
            f"{str(provisioning_request.id).upper()}"
        )

        return ProvisioningProviderResult(
            provider_reference=provider_reference,
            metadata={
                "provider": "STUB",
                "action": action,
                "service_number": (
                    provisioning_request
                    .service_account
                    .service_number
                ),
            },
        )


def get_provisioning_provider(
    *,
    provisioning_request: ProvisioningRequest,
) -> BaseProvisioningProvider:
    return StubProvisioningProvider()