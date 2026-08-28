from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from field_operations.models import WorkOrder
from tenancy.models import Organization
from tenancy.services import record_audit_log


class MaintenanceDomainError(Exception):
    pass


@dataclass(frozen=True)
class MaintenanceResult:
    work_order: WorkOrder


def _get_maintenance(*, organization, work_order_id):
    try:
        work_order = (
            WorkOrder.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=work_order_id)
        )
    except WorkOrder.DoesNotExist as exc:
        raise MaintenanceDomainError(
            "Maintenance work order was not found for this organization."
        ) from exc

    if work_order.work_type != WorkOrder.WorkType.NETWORK_MAINTENANCE:
        raise MaintenanceDomainError(
            "Maintenance lifecycle is only available for network maintenance work orders."
        )
    return work_order


def _audit(*, organization, actor, action, work_order):
    record_audit_log(
        organization=organization,
        actor=actor,
        action=action,
        resource_type="WorkOrder",
        resource_id=work_order.id,
        metadata={
            "work_order_number": work_order.work_order_number,
            "work_type": work_order.work_type,
            "status": work_order.status,
            "network_node_id": str(work_order.network_node_id or ""),
            "scheduled_at": (
                work_order.scheduled_at.isoformat()
                if work_order.scheduled_at else ""
            ),
        },
    )


@transaction.atomic
def schedule_maintenance(
    *, organization: Organization, work_order_id, scheduled_at, maintenance_notes="", actor=None
) -> MaintenanceResult:
    if not organization.is_active:
        raise MaintenanceDomainError("Organization is not active.")
    if scheduled_at is None:
        raise MaintenanceDomainError("Scheduled time is required.")

    work_order = _get_maintenance(
        organization=organization,
        work_order_id=work_order_id,
    )

    if work_order.status != WorkOrder.Status.CREATED:
        raise MaintenanceDomainError("Only a created maintenance work order can be scheduled.")

    if scheduled_at <= timezone.now():
        raise MaintenanceDomainError("Maintenance must be scheduled for a future time.")

    work_order.scheduled_at = scheduled_at
    work_order.maintenance_notes = maintenance_notes.strip()
    work_order.status = WorkOrder.Status.SCHEDULED
    work_order.save(update_fields=["scheduled_at", "maintenance_notes", "status", "updated_at"])
    _audit(
        organization=organization,
        actor=actor,
        action="MAINTENANCE_SCHEDULED",
        work_order=work_order,
    )
    return MaintenanceResult(work_order=work_order)


@transaction.atomic
def start_maintenance(*, organization: Organization, work_order_id, actor=None) -> MaintenanceResult:
    work_order = _get_maintenance(organization=organization, work_order_id=work_order_id)
    if work_order.status != WorkOrder.Status.SCHEDULED:
        raise MaintenanceDomainError("Only scheduled maintenance can be started.")

    work_order.started_at = timezone.now()
    work_order.status = WorkOrder.Status.STARTED
    work_order.save(update_fields=["started_at", "status", "updated_at"])
    _audit(organization=organization, actor=actor, action="MAINTENANCE_STARTED", work_order=work_order)
    return MaintenanceResult(work_order=work_order)


@transaction.atomic
def complete_maintenance(*, organization: Organization, work_order_id, completion_notes, actor=None) -> MaintenanceResult:
    work_order = _get_maintenance(organization=organization, work_order_id=work_order_id)
    if work_order.status != WorkOrder.Status.STARTED:
        raise MaintenanceDomainError("Only started maintenance can be completed.")

    completion_notes = completion_notes.strip()
    if not completion_notes:
        raise MaintenanceDomainError("Completion notes are required to complete maintenance.")

    work_order.completion_notes = completion_notes
    work_order.completed_at = timezone.now()
    work_order.status = WorkOrder.Status.COMPLETED
    work_order.save(update_fields=["completion_notes", "completed_at", "status", "updated_at"])
    _audit(organization=organization, actor=actor, action="MAINTENANCE_COMPLETED", work_order=work_order)
    return MaintenanceResult(work_order=work_order)


@transaction.atomic
def restore_maintenance(*, organization: Organization, work_order_id, actor=None) -> MaintenanceResult:
    work_order = _get_maintenance(organization=organization, work_order_id=work_order_id)
    if work_order.status != WorkOrder.Status.COMPLETED:
        raise MaintenanceDomainError("Only completed maintenance can be restored.")

    work_order.restored_at = timezone.now()
    work_order.status = WorkOrder.Status.RESTORED
    work_order.save(update_fields=["restored_at", "status", "updated_at"])
    _audit(organization=organization, actor=actor, action="MAINTENANCE_RESTORED", work_order=work_order)
    return MaintenanceResult(work_order=work_order)
