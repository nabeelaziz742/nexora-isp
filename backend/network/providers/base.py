from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class NetworkProviderError(Exception):
    pass


@dataclass(frozen=True)
class ProvisioningResult:
    success: bool
    provider_reference: str = ""
    metadata: dict[str, Any] | None = None
    error_message: str = ""


class NetworkProvider(ABC):
    @abstractmethod
    def activate_service(
        self,
        *,
        service_account,
        network_assignment,
        payload: dict[str, Any],
    ) -> ProvisioningResult:
        raise NotImplementedError

    @abstractmethod
    def suspend_service(
        self,
        *,
        service_account,
        network_assignment,
        payload: dict[str, Any],
    ) -> ProvisioningResult:
        raise NotImplementedError

    @abstractmethod
    def restore_service(
        self,
        *,
        service_account,
        network_assignment,
        payload: dict[str, Any],
    ) -> ProvisioningResult:
        raise NotImplementedError

    @abstractmethod
    def change_package(
        self,
        *,
        service_account,
        network_assignment,
        payload: dict[str, Any],
    ) -> ProvisioningResult:
        raise NotImplementedError