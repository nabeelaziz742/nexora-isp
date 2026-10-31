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
from network.credentials import encrypt_secret, generate_network_password
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
    # Plaintext PPPoE password, returned once so staff can configure the customer's router.
    network_password: str = ""


def _schedule_provisioning_execution(provisioning_request: ProvisioningRequest) -> None:
    """Execute the request once the surrounding transaction commits, so the router never
    sees a change the database later rolled back."""
    from network.tasks import execute_provisioning_request_task

    request_id = str(provisioning_request.id)
    # robust: the data is already committed, so a broker or router hiccup must not
    # turn the user's request into a 500; the periodic task retries pending requests.
    transaction.on_commit(
        lambda: execute_provisioning_request_task.delay(request_id),
        robust=True,
    )


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
    password: str = "",
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

    username = username.strip()
    password = password.strip()
    if network_node.provisioning_backend == NetworkNode.ProvisioningBackend.MIKROTIK:
        # A router-managed subscriber always needs PPPoE credentials.
        username = username or service_account.service_number
        password = password or generate_network_password()

    if (
        username
        and NetworkAssignment.objects
        .for_organization(organization)
        .filter(network_node=network_node, username__iexact=username, is_active=True)
        .exists()
    ):
        # Reusing a username would let one subscriber's provisioning overwrite another's secret.
        raise NetworkAssignmentError(
            f"Network username '{username}' is already assigned on node {network_node.code}."
        )

    network_assignment = NetworkAssignment.objects.create(
        organization=organization,
        service_account=service_account,
        network_node=network_node,
        username=username,
        network_password_encrypted=encrypt_secret(password),
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

    _schedule_provisioning_execution(provisioning_request)

    return NetworkActivationResult(
        network_assignment=network_assignment,
        provisioning_request=provisioning_request,
        network_password=password,
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

    _schedule_provisioning_execution(provisioning_request)

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

    _schedule_provisioning_execution(provisioning_request)

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

    _schedule_provisioning_execution(provisioning_request)

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

# ==============================================================================
# NETWORK NODE INFRASTRUCTURE SERVICES
# ==============================================================================

class NetworkNodeDomainError(Exception):
    pass


def _resolve_node_pop_site(*, organization: Organization, pop_site_id):
    if not pop_site_id:
        return None
    try:
        return PointOfPresence.objects.for_organization(organization).get(id=pop_site_id)
    except PointOfPresence.DoesNotExist as exc:
        raise NetworkNodeDomainError("The specified POP site was not found in this organization.") from exc


def _validate_router_integration(node: NetworkNode) -> None:
    if node.provisioning_backend != NetworkNode.ProvisioningBackend.MIKROTIK:
        return
    if not (node.router_api_host or node.management_ip):
        raise NetworkNodeDomainError("MikroTik integration needs a router API host or management IP.")
    if not node.router_api_username:
        raise NetworkNodeDomainError("MikroTik integration needs a router API username.")
    if not node.router_api_password_encrypted:
        raise NetworkNodeDomainError("MikroTik integration needs a router API password.")


@transaction.atomic
def create_network_node(
    *,
    organization: Organization,
    actor,
    code: str,
    name: str,
    node_type: str,
    pop_site_id=None,
    management_ip=None,
    location: str = "",
    is_active: bool = True,
    provisioning_backend: str = NetworkNode.ProvisioningBackend.MANUAL,
    router_api_host: str = "",
    router_api_port=None,
    router_api_username: str = "",
    router_api_password: str = "",
    router_api_use_tls: bool = False,
) -> NetworkNode:
    code_clean = str(code).strip().upper()
    name_clean = str(name).strip()

    if not code_clean:
        raise NetworkNodeDomainError("Node code is required.")
    if not name_clean:
        raise NetworkNodeDomainError("Node name is required.")

    if NetworkNode.objects.for_organization(organization).filter(code=code_clean).exists():
        raise NetworkNodeDomainError(f"A network node with code '{code_clean}' already exists in this organization.")

    pop_site = _resolve_node_pop_site(organization=organization, pop_site_id=pop_site_id)

    node = NetworkNode(
        organization=organization,
        code=code_clean,
        name=name_clean,
        node_type=node_type,
        pop_site=pop_site,
        management_ip=management_ip or None,
        location=location.strip(),
        is_active=is_active,
        provisioning_backend=provisioning_backend,
        router_api_host=router_api_host.strip(),
        router_api_port=router_api_port or None,
        router_api_username=router_api_username.strip(),
        router_api_password_encrypted=encrypt_secret(router_api_password),
        router_api_use_tls=router_api_use_tls,
    )
    _validate_router_integration(node)
    node.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="NETWORK_NODE_CREATED",
        resource_type="NetworkNode",
        resource_id=node.id,
        metadata={
            "code": node.code,
            "name": node.name,
            "node_type": node.node_type,
            "pop_site_id": str(pop_site.id) if pop_site else None,
            "management_ip": node.management_ip,
            "is_active": node.is_active,
            "provisioning_backend": node.provisioning_backend,
        },
    )

    return node


@transaction.atomic
def update_network_node(
    *,
    organization: Organization,
    actor,
    node_id,
    **kwargs,
) -> NetworkNode:
    try:
        node = (
            NetworkNode.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=node_id)
        )
    except NetworkNode.DoesNotExist as exc:
        raise NetworkNodeDomainError("Network node was not found in this organization.") from exc

    was_active = node.is_active

    if "code" in kwargs:
        new_code = str(kwargs["code"]).strip().upper()
        if not new_code:
            raise NetworkNodeDomainError("Node code cannot be empty.")
        if (
            NetworkNode.objects.for_organization(organization)
            .filter(code=new_code)
            .exclude(id=node.id)
            .exists()
        ):
            raise NetworkNodeDomainError(f"A network node with code '{new_code}' already exists in this organization.")
        node.code = new_code

    if "name" in kwargs:
        new_name = str(kwargs["name"]).strip()
        if not new_name:
            raise NetworkNodeDomainError("Node name cannot be empty.")
        node.name = new_name

    if "node_type" in kwargs:
        node.node_type = kwargs["node_type"]

    if "pop_site_id" in kwargs:
        node.pop_site = _resolve_node_pop_site(organization=organization, pop_site_id=kwargs["pop_site_id"])

    if "management_ip" in kwargs:
        node.management_ip = kwargs["management_ip"] or None

    if "location" in kwargs:
        node.location = str(kwargs["location"]).strip()

    if "is_active" in kwargs:
        node.is_active = bool(kwargs["is_active"])

    if "provisioning_backend" in kwargs:
        node.provisioning_backend = kwargs["provisioning_backend"]

    if "router_api_host" in kwargs:
        node.router_api_host = str(kwargs["router_api_host"]).strip()

    if "router_api_port" in kwargs:
        node.router_api_port = kwargs["router_api_port"] or None

    if "router_api_username" in kwargs:
        node.router_api_username = str(kwargs["router_api_username"]).strip()

    # A blank password on update means "keep the stored one".
    if kwargs.get("router_api_password"):
        node.router_api_password_encrypted = encrypt_secret(kwargs["router_api_password"])

    if "router_api_use_tls" in kwargs:
        node.router_api_use_tls = bool(kwargs["router_api_use_tls"])

    _validate_router_integration(node)

    # Deactivating a node that still carries subscribers would strand their services.
    if was_active and not node.is_active:
        active_assignments = node.service_assignments.filter(is_active=True).count()
        if active_assignments:
            raise NetworkNodeDomainError(
                f"This node has {active_assignments} active service assignment(s). "
                "Move those services to another node before deactivating it."
            )

    node.save()

    audit_action = "NETWORK_NODE_STATUS_CHANGED" if was_active != node.is_active else "NETWORK_NODE_UPDATED"
    record_audit_log(
        organization=organization,
        actor=actor,
        action=audit_action,
        resource_type="NetworkNode",
        resource_id=node.id,
        metadata={
            "code": node.code,
            "name": node.name,
            "node_type": node.node_type,
            "is_active": node.is_active,
            "was_active": was_active,
            "provisioning_backend": node.provisioning_backend,
        },
    )

    return node
