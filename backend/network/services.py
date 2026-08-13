from dataclasses import dataclass
from typing import Any

from django.db import transaction

from customers.models import (
    InternetPackage,
    ServiceAccount,
)
from network.models import (
    NetworkAssignment,
    NetworkNode,
    ProvisioningRequest,
)
from tenancy.models import Organization
from tenancy.services import record_audit_log


class NetworkAssignmentError(Exception):
    pass


class ServiceLifecycleError(Exception):
    pass


@dataclass(frozen=True)
class NetworkActivationResult:
    network_assignment: NetworkAssignment
    provisioning_request: ProvisioningRequest


@dataclass(frozen=True)
class ServiceLifecycleResult:
    service_account: ServiceAccount
    provisioning_request: ProvisioningRequest


@transaction.atomic
def create_activation_network_request(
    *,
    organization: Organization,
    service_account: ServiceAccount,
    network_node_id,
    username: str = "",
    ip_address: str | None = None,
    provisioning_payload: dict[str, Any] | None = None,
) -> NetworkActivationResult:
    if service_account.organization_id != organization.id:
        raise NetworkAssignmentError(
            "Service account does not belong to this organization."
        )

    try:
        network_node = (
            NetworkNode.objects
            .for_organization(organization)
            .select_for_update()
            .get(
                id=network_node_id,
                is_active=True,
            )
        )
    except NetworkNode.DoesNotExist as exc:
        raise NetworkAssignmentError(
            "Active network node was not found "
            "for this organization."
        ) from exc

    if (
        NetworkAssignment.objects
        .for_organization(organization)
        .filter(service_account=service_account)
        .exists()
    ):
        raise NetworkAssignmentError(
            "Service account already has a network assignment."
        )

    network_assignment = NetworkAssignment.objects.create(
        organization=organization,
        service_account=service_account,
        network_node=network_node,
        username=username.strip(),
        ip_address=ip_address,
    )

    provisioning_request = ProvisioningRequest.objects.create(
        organization=organization,
        service_account=service_account,
        network_assignment=network_assignment,
        action=ProvisioningRequest.Action.ACTIVATE,
        status=ProvisioningRequest.Status.PENDING,
        requested_payload=provisioning_payload or {},
    )

    return NetworkActivationResult(
        network_assignment=network_assignment,
        provisioning_request=provisioning_request,
    )


def _get_locked_service_account(
    *,
    organization: Organization,
    service_account_id,
) -> ServiceAccount:
    try:
        return (
            ServiceAccount.objects
            .for_organization(organization)
            .select_for_update()
            .select_related(
                "customer",
                "internet_package",
            )
            .get(id=service_account_id)
        )
    except ServiceAccount.DoesNotExist as exc:
        raise ServiceLifecycleError(
            "Service account was not found "
            "for this organization."
        ) from exc


def _get_network_assignment(
    *,
    organization: Organization,
    service_account: ServiceAccount,
) -> NetworkAssignment:
    try:
        return (
            NetworkAssignment.objects
            .for_organization(organization)
            .select_for_update()
            .select_related("network_node")
            .get(
                service_account=service_account,
                is_active=True,
            )
        )
    except NetworkAssignment.DoesNotExist as exc:
        raise ServiceLifecycleError(
            "Active network assignment was not found "
            "for this service account."
        ) from exc


def _ensure_no_conflicting_provisioning_request(
    *,
    organization: Organization,
    service_account: ServiceAccount,
) -> None:
    has_conflicting_request = (
        ProvisioningRequest.objects
        .for_organization(organization)
        .filter(
            service_account=service_account,
            status__in=[
                ProvisioningRequest.Status.PENDING,
                ProvisioningRequest.Status.PROCESSING,
            ],
        )
        .exists()
    )

    if has_conflicting_request:
        raise ServiceLifecycleError(
            "Service account already has an active "
            "provisioning request."
        )


@transaction.atomic
def request_service_suspension(
    *,
    organization: Organization,
    service_account_id,
    requested_by=None,
) -> ServiceLifecycleResult:
    if not organization.is_active:
        raise ServiceLifecycleError(
            "Organization is not active."
        )

    service_account = _get_locked_service_account(
        organization=organization,
        service_account_id=service_account_id,
    )

    if service_account.status not in [
        ServiceAccount.Status.ACTIVE,
        ServiceAccount.Status.GRACE_PERIOD,
    ]:
        raise ServiceLifecycleError(
            "Service account cannot request suspension "
            "from its current status."
        )

    network_assignment = _get_network_assignment(
        organization=organization,
        service_account=service_account,
    )

    _ensure_no_conflicting_provisioning_request(
        organization=organization,
        service_account=service_account,
    )

    provisioning_request = ProvisioningRequest.objects.create(
        organization=organization,
        service_account=service_account,
        network_assignment=network_assignment,
        action=ProvisioningRequest.Action.SUSPEND,
        status=ProvisioningRequest.Status.PENDING,
        requested_payload={
            "reason": "NON_PAYMENT",
        },
    )

    service_account.status = (
        ServiceAccount.Status.SUSPENSION_PENDING
    )
    service_account.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    record_audit_log(
        organization=organization,
        actor=requested_by,
        action="SERVICE_SUSPENSION_REQUESTED",
        resource_type="ServiceAccount",
        resource_id=service_account.id,
        metadata={
            "service_number": service_account.service_number,
            "provisioning_request_id": str(
                provisioning_request.id
            ),
        },
    )

    return ServiceLifecycleResult(
        service_account=service_account,
        provisioning_request=provisioning_request,
    )


@transaction.atomic
def request_service_restore(
    *,
    organization: Organization,
    service_account_id,
    requested_by=None,
) -> ServiceLifecycleResult:
    if not organization.is_active:
        raise ServiceLifecycleError(
            "Organization is not active."
        )

    service_account = _get_locked_service_account(
        organization=organization,
        service_account_id=service_account_id,
    )

    if (
        service_account.status
        != ServiceAccount.Status.SUSPENDED_NON_PAYMENT
    ):
        raise ServiceLifecycleError(
            "Only a suspended non-payment service "
            "can request restore."
        )

    network_assignment = _get_network_assignment(
        organization=organization,
        service_account=service_account,
    )

    _ensure_no_conflicting_provisioning_request(
        organization=organization,
        service_account=service_account,
    )

    provisioning_request = ProvisioningRequest.objects.create(
        organization=organization,
        service_account=service_account,
        network_assignment=network_assignment,
        action=ProvisioningRequest.Action.RESTORE,
        status=ProvisioningRequest.Status.PENDING,
        requested_payload={
            "reason": "SERVICE_RESTORE",
        },
    )

    service_account.status = (
        ServiceAccount.Status.RESTORE_PENDING
    )
    service_account.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    record_audit_log(
        organization=organization,
        actor=requested_by,
        action="SERVICE_RESTORE_REQUESTED",
        resource_type="ServiceAccount",
        resource_id=service_account.id,
        metadata={
            "service_number": service_account.service_number,
            "provisioning_request_id": str(
                provisioning_request.id
            ),
        },
    )

    return ServiceLifecycleResult(
        service_account=service_account,
        provisioning_request=provisioning_request,
    )


@transaction.atomic
def request_package_change(
    *,
    organization: Organization,
    service_account_id,
    internet_package_id,
    requested_by=None,
) -> ServiceLifecycleResult:
    if not organization.is_active:
        raise ServiceLifecycleError(
            "Organization is not active."
        )

    service_account = _get_locked_service_account(
        organization=organization,
        service_account_id=service_account_id,
    )

    if service_account.status != ServiceAccount.Status.ACTIVE:
        raise ServiceLifecycleError(
            "Package change can only be requested "
            "for an active service account."
        )

    try:
        internet_package = (
            InternetPackage.objects
            .for_organization(organization)
            .get(
                id=internet_package_id,
                is_active=True,
            )
        )
    except InternetPackage.DoesNotExist as exc:
        raise ServiceLifecycleError(
            "Active internet package was not found "
            "for this organization."
        ) from exc

    if (
        service_account.internet_package_id
        == internet_package.id
    ):
        raise ServiceLifecycleError(
            "Service account already uses this package."
        )

    network_assignment = _get_network_assignment(
        organization=organization,
        service_account=service_account,
    )

    _ensure_no_conflicting_provisioning_request(
        organization=organization,
        service_account=service_account,
    )

    provisioning_request = ProvisioningRequest.objects.create(
        organization=organization,
        service_account=service_account,
        network_assignment=network_assignment,
        action=ProvisioningRequest.Action.CHANGE_PACKAGE,
        status=ProvisioningRequest.Status.PENDING,
        requested_payload={
            "current_package_id": str(
                service_account.internet_package_id
            ),
            "target_package_id": str(
                internet_package.id
            ),
            "target_package_code": internet_package.code,
            "target_package_name": internet_package.name,
        },
    )

    record_audit_log(
        organization=organization,
        actor=requested_by,
        action="SERVICE_PACKAGE_CHANGE_REQUESTED",
        resource_type="ServiceAccount",
        resource_id=service_account.id,
        metadata={
            "service_number": service_account.service_number,
            "current_package_id": str(
                service_account.internet_package_id
            ),
            "target_package_id": str(
                internet_package.id
            ),
            "provisioning_request_id": str(
                provisioning_request.id
            ),
        },
    )

    return ServiceLifecycleResult(
        service_account=service_account,
        provisioning_request=provisioning_request,
    )