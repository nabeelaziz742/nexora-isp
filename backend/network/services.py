from dataclasses import dataclass
from typing import Any

from django.db import transaction

from customers.models import (
    Area,
    InternetPackage,
    ServiceAccount,
)
from network.models import (
    NetworkAssignment,
    NetworkNode,
    PointOfPresence,
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


# ==============================================================================
# POINT OF PRESENCE (POP) INFRASTRUCTURE SERVICES (BATCH 13)
# ==============================================================================

class PopDomainError(Exception):
    pass


@transaction.atomic
def create_pop_site(
    *,
    organization: Organization,
    actor,
    code: str,
    name: str,
    pop_type: str = PointOfPresence.PopType.DISTRIBUTION,
    area_id=None,
    address: str = "",
    latitude=None,
    longitude=None,
    rack_capacity_units: int = 42,
    power_backup_type: str = "UPS_GENERATOR",
    status: str = PointOfPresence.Status.ACTIVE,
    supervisor_id=None,
    notes: str = "",
) -> PointOfPresence:
    code_clean = str(code).strip().upper()
    name_clean = str(name).strip()

    if not code_clean:
        raise PopDomainError("POP code is required.")
    if not name_clean:
        raise PopDomainError("POP name is required.")
    if rack_capacity_units < 0:
        raise PopDomainError("Rack capacity units cannot be negative.")

    if PointOfPresence.objects.for_organization(organization).filter(code=code_clean).exists():
        raise PopDomainError(f"A POP site with code '{code_clean}' already exists in this organization.")

    area = None
    if area_id:
        try:
            area = Area.objects.for_organization(organization).get(id=area_id)
        except Area.DoesNotExist as exc:
            raise PopDomainError("The specified Area was not found in this organization.") from exc

    supervisor = None
    if supervisor_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            supervisor = User.objects.get(id=supervisor_id)
        except User.DoesNotExist as exc:
            raise PopDomainError("The specified supervisor was not found.") from exc

    pop = PointOfPresence.objects.create(
        organization=organization,
        code=code_clean,
        name=name_clean,
        pop_type=pop_type,
        area=area,
        address=address.strip(),
        latitude=latitude,
        longitude=longitude,
        rack_capacity_units=rack_capacity_units,
        power_backup_type=power_backup_type.strip(),
        status=status,
        supervisor=supervisor,
        notes=notes.strip(),
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="POP_SITE_CREATED",
        resource_type="PointOfPresence",
        resource_id=pop.id,
        metadata={
            "code": pop.code,
            "name": pop.name,
            "pop_type": pop.pop_type,
            "area_id": str(area.id) if area else None,
            "status": pop.status,
            "rack_capacity_units": pop.rack_capacity_units,
        },
    )

    return pop


@transaction.atomic
def update_pop_site(
    *,
    organization: Organization,
    actor,
    pop_id,
    **kwargs,
) -> PointOfPresence:
    try:
        pop = (
            PointOfPresence.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=pop_id)
        )
    except PointOfPresence.DoesNotExist as exc:
        raise PopDomainError("POP site was not found in this organization.") from exc

    old_status = pop.status

    if "code" in kwargs:
        new_code = str(kwargs["code"]).strip().upper()
        if not new_code:
            raise PopDomainError("POP code cannot be empty.")
        if (
            PointOfPresence.objects.for_organization(organization)
            .filter(code=new_code)
            .exclude(id=pop.id)
            .exists()
        ):
            raise PopDomainError(f"A POP site with code '{new_code}' already exists in this organization.")
        pop.code = new_code

    if "name" in kwargs:
        new_name = str(kwargs["name"]).strip()
        if not new_name:
            raise PopDomainError("POP name cannot be empty.")
        pop.name = new_name

    if "pop_type" in kwargs:
        pop.pop_type = kwargs["pop_type"]

    if "area_id" in kwargs:
        area_id = kwargs["area_id"]
        if area_id:
            try:
                pop.area = Area.objects.for_organization(organization).get(id=area_id)
            except Area.DoesNotExist as exc:
                raise PopDomainError("The specified Area was not found in this organization.") from exc
        else:
            pop.area = None

    if "address" in kwargs:
        pop.address = str(kwargs["address"]).strip()

    if "latitude" in kwargs:
        pop.latitude = kwargs["latitude"]

    if "longitude" in kwargs:
        pop.longitude = kwargs["longitude"]

    if "rack_capacity_units" in kwargs:
        cap = int(kwargs["rack_capacity_units"])
        if cap < 0:
            raise PopDomainError("Rack capacity units cannot be negative.")
        pop.rack_capacity_units = cap

    if "power_backup_type" in kwargs:
        pop.power_backup_type = str(kwargs["power_backup_type"]).strip()

    if "status" in kwargs:
        pop.status = kwargs["status"]

    if "supervisor_id" in kwargs:
        sup_id = kwargs["supervisor_id"]
        if sup_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                pop.supervisor = User.objects.get(id=sup_id)
            except User.DoesNotExist as exc:
                raise PopDomainError("The specified supervisor was not found.") from exc
        else:
            pop.supervisor = None

    if "notes" in kwargs:
        pop.notes = str(kwargs["notes"]).strip()

    if "is_active" in kwargs:
        pop.is_active = bool(kwargs["is_active"])

    pop.save()

    audit_action = "POP_SITE_STATUS_CHANGED" if old_status != pop.status else "POP_SITE_UPDATED"
    record_audit_log(
        organization=organization,
        actor=actor,
        action=audit_action,
        resource_type="PointOfPresence",
        resource_id=pop.id,
        metadata={
            "code": pop.code,
            "name": pop.name,
            "status": pop.status,
            "old_status": old_status,
        },
    )

    return pop


def get_pop_statistics(*, organization: Organization, pop: PointOfPresence) -> dict:
    """Aggregates real-time subscriber and hardware node counts for a POP site."""
    node_ids = list(pop.nodes.values_list("id", flat=True))
    active_assignments_count = (
        NetworkAssignment.objects
        .for_organization(organization)
        .filter(network_node_id__in=node_ids, is_active=True)
        .count()
    )
    total_assignments_count = (
        NetworkAssignment.objects
        .for_organization(organization)
        .filter(network_node_id__in=node_ids)
        .count()
    )

    return {
        "nodes_count": len(node_ids),
        "active_subscribers_count": active_assignments_count,
        "total_subscribers_count": total_assignments_count,
    }