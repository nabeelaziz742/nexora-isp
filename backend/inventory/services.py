from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from customers.models import ServiceAccount
from inventory.models import (
    DeviceAssignment,
    InventoryDevice,
)
from tenancy.models import Organization
from tenancy.services import record_audit_log


User = get_user_model()


class InventoryCustodyError(Exception):
    pass


@dataclass(frozen=True)
class DeviceAssignmentResult:
    device: InventoryDevice
    assignment: DeviceAssignment


@transaction.atomic
def assign_device_to_service(
    *,
    organization: Organization,
    actor: User,
    device_id,
    service_account_id,
    assignment_notes: str = "",
) -> DeviceAssignmentResult:
    try:
        device = (
            InventoryDevice.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=device_id)
        )
    except InventoryDevice.DoesNotExist as exc:
        raise InventoryCustodyError(
            "Device was not found for this organization."
        ) from exc

    try:
        service_account = (
            ServiceAccount.objects
            .for_organization(organization)
            .get(id=service_account_id)
        )
    except ServiceAccount.DoesNotExist as exc:
        raise InventoryCustodyError(
            "Service account was not found for this organization."
        ) from exc

    if device.status != InventoryDevice.Status.AVAILABLE:
        raise InventoryCustodyError(
            "Only an available device can be assigned."
        )

    active_assignment_exists = (
        DeviceAssignment.objects
        .for_organization(organization)
        .filter(
            device=device,
            returned_at__isnull=True,
        )
        .exists()
    )

    if active_assignment_exists:
        raise InventoryCustodyError(
            "Device already has an active assignment."
        )

    assignment = DeviceAssignment.objects.create(
        organization=organization,
        device=device,
        service_account=service_account,
        assigned_by=actor,
        assignment_notes=assignment_notes.strip(),
    )

    device.status = InventoryDevice.Status.ASSIGNED
    device.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="INVENTORY_DEVICE_ASSIGNED",
        resource_type="InventoryDevice",
        resource_id=device.id,
        metadata={
            "device_assignment_id": str(assignment.id),
            "asset_tag": device.asset_tag,
            "service_account_id": str(service_account.id),
            "service_number": service_account.service_number,
        },
    )

    return DeviceAssignmentResult(
        device=device,
        assignment=assignment,
    )


@transaction.atomic
def return_device_from_service(
    *,
    organization: Organization,
    actor: User,
    assignment_id,
    return_condition: str,
    return_notes: str = "",
) -> DeviceAssignmentResult:
    try:
        assignment = (
            DeviceAssignment.objects
            .select_for_update()
            .select_related(
                "device",
                "service_account",
            )
            .for_organization(organization)
            .get(
                id=assignment_id,
                returned_at__isnull=True,
            )
        )
    except DeviceAssignment.DoesNotExist as exc:
        raise InventoryCustodyError(
            "Active device assignment was not found "
            "for this organization."
        ) from exc

    valid_conditions = {
        choice
        for choice, _ in DeviceAssignment.ReturnCondition.choices
    }

    if return_condition not in valid_conditions:
        raise InventoryCustodyError(
            "Invalid device return condition."
        )

    device = InventoryDevice.objects.select_for_update().get(
        id=assignment.device_id,
        organization=organization,
    )

    assignment.returned_by = actor
    assignment.returned_at = timezone.now()
    assignment.return_condition = return_condition
    assignment.return_notes = return_notes.strip()
    assignment.save(
        update_fields=[
            "returned_by",
            "returned_at",
            "return_condition",
            "return_notes",
            "updated_at",
        ]
    )

    if return_condition == DeviceAssignment.ReturnCondition.GOOD:
        device.status = InventoryDevice.Status.AVAILABLE
    else:
        device.status = InventoryDevice.Status.FAULTY

    device.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="INVENTORY_DEVICE_RETURNED",
        resource_type="InventoryDevice",
        resource_id=device.id,
        metadata={
            "device_assignment_id": str(assignment.id),
            "asset_tag": device.asset_tag,
            "service_account_id": str(
                assignment.service_account_id
            ),
            "service_number": (
                assignment.service_account.service_number
            ),
            "return_condition": return_condition,
        },
    )

    return DeviceAssignmentResult(
        device=device,
        assignment=assignment,
    )