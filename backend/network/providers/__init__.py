from network.models import NetworkNode, ProvisioningRequest
from network.providers.mikrotik import MikroTikProvisioningProvider
from network.providers.stub import (
    BaseProvisioningProvider,
    ProvisioningProviderError,
    ProvisioningProviderResult,
    StubProvisioningProvider,
)


def get_provisioning_provider(
    *,
    provisioning_request: ProvisioningRequest,
) -> BaseProvisioningProvider:
    assignment = provisioning_request.network_assignment
    node = assignment.network_node if assignment else None

    if (
        node is not None
        and node.provisioning_backend
        == NetworkNode.ProvisioningBackend.MIKROTIK
    ):
        return MikroTikProvisioningProvider()

    return StubProvisioningProvider()


__all__ = [
    "BaseProvisioningProvider",
    "MikroTikProvisioningProvider",
    "ProvisioningProviderError",
    "ProvisioningProviderResult",
    "StubProvisioningProvider",
    "get_provisioning_provider",
]
