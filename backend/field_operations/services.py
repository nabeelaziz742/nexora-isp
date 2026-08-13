from dataclasses import dataclass
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from customers.models import Customer, ServiceAccount
from field_operations.models import WorkOrder
from network.models import NetworkNode
from support.models import Complaint, Incident
from tenancy.models import (
    Organization,
    OrganizationMembership,
)
from tenancy.services import record_audit_log


class FieldOperationsDomainError(Exception):
    pass


@dataclass(frozen=True)
class WorkOrderResult:
    work_order: WorkOrder


def _generate_work_order_number() -> str:
    return f"WO-{uuid4().hex[:12].upper()}"


@transaction.atomic
def create_work_order(
    *,
    organization: Organization,
    work_type: str,
    priority: str,
    title: str,
    description: str,
    customer_id=None,
    service_account_id=None,
    network_node_id=None,
    complaint_id=None,
    incident_id=None,
    created_by=None,
) -> WorkOrderResult:
    if not organization.is_active:
        raise FieldOperationsDomainError(
            "Organization is not active."
        )

    if work_type not in WorkOrder.WorkType.values:
        raise FieldOperationsDomainError(
            "Invalid work order type."
        )

    if priority not in WorkOrder.Priority.values:
        raise FieldOperationsDomainError(
            "Invalid work order priority."
        )

    title = title.strip()
    description = description.strip()

    if not title:
        raise FieldOperationsDomainError(
            "Work order title is required."
        )

    if not description:
        raise FieldOperationsDomainError(
            "Work order description is required."
        )

    customer = None

    if customer_id is not None:
        try:
            customer = (
                Customer.objects
                .for_organization(organization)
                .get(id=customer_id)
            )
        except Customer.DoesNotExist as exc:
            raise FieldOperationsDomainError(
                "Customer was not found "
                "for this organization."
            ) from exc

    service_account = None

    if service_account_id is not None:
        try:
            service_account = (
                ServiceAccount.objects
                .for_organization(organization)
                .select_related("customer")
                .get(id=service_account_id)
            )
        except ServiceAccount.DoesNotExist as exc:
            raise FieldOperationsDomainError(
                "Service account was not found "
                "for this organization."
            ) from exc

        if (
            customer is not None
            and service_account.customer_id != customer.id
        ):
            raise FieldOperationsDomainError(
                "Service account does not belong "
                "to the selected customer."
            )

        if customer is None:
            customer = service_account.customer

    network_node = None

    if network_node_id is not None:
        try:
            network_node = (
                NetworkNode.objects
                .for_organization(organization)
                .get(id=network_node_id)
            )
        except NetworkNode.DoesNotExist as exc:
            raise FieldOperationsDomainError(
                "Network node was not found "
                "for this organization."
            ) from exc

    complaint = None

    if complaint_id is not None:
        try:
            complaint = (
                Complaint.objects
                .for_organization(organization)
                .select_related(
                    "customer",
                    "service_account",
                )
                .get(id=complaint_id)
            )
        except Complaint.DoesNotExist as exc:
            raise FieldOperationsDomainError(
                "Complaint was not found "
                "for this organization."
            ) from exc

        if (
            customer is not None
            and complaint.customer_id != customer.id
        ):
            raise FieldOperationsDomainError(
                "Complaint does not belong "
                "to the selected customer."
            )

        if (
            service_account is not None
            and complaint.service_account_id is not None
            and complaint.service_account_id
            != service_account.id
        ):
            raise FieldOperationsDomainError(
                "Complaint service does not match "
                "the selected service account."
            )

        if customer is None:
            customer = complaint.customer

        if (
            service_account is None
            and complaint.service_account is not None
        ):
            service_account = complaint.service_account

    incident = None

    if incident_id is not None:
        try:
            incident = (
                Incident.objects
                .for_organization(organization)
                .get(id=incident_id)
            )
        except Incident.DoesNotExist as exc:
            raise FieldOperationsDomainError(
                "Incident was not found "
                "for this organization."
            ) from exc

    work_order = WorkOrder.objects.create(
        organization=organization,
        work_order_number=_generate_work_order_number(),
        customer=customer,
        service_account=service_account,
        network_node=network_node,
        complaint=complaint,
        incident=incident,
        work_type=work_type,
        priority=priority,
        status=WorkOrder.Status.CREATED,
        title=title,
        description=description,
        created_by=created_by,
    )

    record_audit_log(
        organization=organization,
        actor=created_by,
        action="FIELD_WORK_ORDER_CREATED",
        resource_type="WorkOrder",
        resource_id=work_order.id,
        metadata={
            "work_order_number": (
                work_order.work_order_number
            ),
            "work_type": work_order.work_type,
            "priority": work_order.priority,
            "customer_id": (
                str(customer.id)
                if customer
                else ""
            ),
            "service_account_id": (
                str(service_account.id)
                if service_account
                else ""
            ),
            "network_node_id": (
                str(network_node.id)
                if network_node
                else ""
            ),
            "complaint_id": (
                str(complaint.id)
                if complaint
                else ""
            ),
            "incident_id": (
                str(incident.id)
                if incident
                else ""
            ),
        },
    )

    return WorkOrderResult(
        work_order=work_order,
    )


@transaction.atomic
def assign_work_order_technician(
    *,
    organization: Organization,
    work_order_id,
    technician_id,
    actor=None,
) -> WorkOrderResult:
    try:
        work_order = (
            WorkOrder.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=work_order_id)
        )
    except WorkOrder.DoesNotExist as exc:
        raise FieldOperationsDomainError(
            "Work order was not found "
            "for this organization."
        ) from exc

    if work_order.status != WorkOrder.Status.CREATED:
        raise FieldOperationsDomainError(
            "Only a created work order "
            "can be assigned."
        )

    try:
        membership = (
            OrganizationMembership.objects
            .select_related("user")
            .get(
                organization=organization,
                user_id=technician_id,
                role=OrganizationMembership.Role.TECHNICIAN,
                is_active=True,
                user__is_active=True,
            )
        )
    except OrganizationMembership.DoesNotExist as exc:
        raise FieldOperationsDomainError(
            "Active technician membership was not found "
            "for this organization."
        ) from exc

    technician: User = membership.user

    work_order.assigned_technician = technician
    work_order.assigned_at = timezone.now()
    work_order.status = WorkOrder.Status.ASSIGNED

    work_order.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="FIELD_WORK_ORDER_ASSIGNED",
        resource_type="WorkOrder",
        resource_id=work_order.id,
        metadata={
            "work_order_number": (
                work_order.work_order_number
            ),
            "technician_id": str(technician.id),
            "technician_email": technician.email,
        },
    )

    return WorkOrderResult(
        work_order=work_order,
    )


@transaction.atomic
def dispatch_work_order(
    *,
    organization: Organization,
    work_order_id,
    dispatch_notes: str = "",
    actor=None,
) -> WorkOrderResult:
    try:
        work_order = (
            WorkOrder.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=work_order_id)
        )
    except WorkOrder.DoesNotExist as exc:
        raise FieldOperationsDomainError(
            "Work order was not found "
            "for this organization."
        ) from exc

    if work_order.status != WorkOrder.Status.ASSIGNED:
        raise FieldOperationsDomainError(
            "Only an assigned work order "
            "can be dispatched."
        )

    if work_order.assigned_technician_id is None:
        raise FieldOperationsDomainError(
            "Work order requires an assigned technician."
        )

    work_order.dispatch_notes = dispatch_notes.strip()
    work_order.dispatched_at = timezone.now()
    work_order.status = WorkOrder.Status.DISPATCHED

    work_order.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="FIELD_WORK_ORDER_DISPATCHED",
        resource_type="WorkOrder",
        resource_id=work_order.id,
        metadata={
            "work_order_number": (
                work_order.work_order_number
            ),
            "technician_id": str(
                work_order.assigned_technician_id
            ),
        },
    )

    return WorkOrderResult(
        work_order=work_order,
    )


@transaction.atomic
def mark_work_order_onsite(
    *,
    organization: Organization,
    work_order_id,
    onsite_notes: str = "",
    actor=None,
) -> WorkOrderResult:
    try:
        work_order = (
            WorkOrder.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=work_order_id)
        )
    except WorkOrder.DoesNotExist as exc:
        raise FieldOperationsDomainError(
            "Work order was not found "
            "for this organization."
        ) from exc

    if work_order.status != WorkOrder.Status.DISPATCHED:
        raise FieldOperationsDomainError(
            "Only a dispatched work order "
            "can move onsite."
        )

    actor_role = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            user=actor,
            is_active=True,
        )
        .values_list("role", flat=True)
        .first()
    )

    if (
        actor_role == OrganizationMembership.Role.TECHNICIAN
        and work_order.assigned_technician_id
        != getattr(actor, "id", None)
    ):
        raise FieldOperationsDomainError(
            "Technician can only update assigned work orders."
        )

    work_order.onsite_notes = onsite_notes.strip()
    work_order.onsite_at = timezone.now()
    work_order.status = WorkOrder.Status.ONSITE

    work_order.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="FIELD_WORK_ORDER_ONSITE",
        resource_type="WorkOrder",
        resource_id=work_order.id,
        metadata={
            "work_order_number": (
                work_order.work_order_number
            ),
            "technician_id": str(
                work_order.assigned_technician_id
            ),
        },
    )

    return WorkOrderResult(
        work_order=work_order,
    )


@transaction.atomic
def complete_work_order(
    *,
    organization: Organization,
    work_order_id,
    completion_notes: str,
    actor=None,
) -> WorkOrderResult:
    try:
        work_order = (
            WorkOrder.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=work_order_id)
        )
    except WorkOrder.DoesNotExist as exc:
        raise FieldOperationsDomainError(
            "Work order was not found "
            "for this organization."
        ) from exc

    if work_order.status != WorkOrder.Status.ONSITE:
        raise FieldOperationsDomainError(
            "Only an onsite work order "
            "can be completed."
        )

    actor_role = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            user=actor,
            is_active=True,
        )
        .values_list("role", flat=True)
        .first()
    )

    if (
        actor_role == OrganizationMembership.Role.TECHNICIAN
        and work_order.assigned_technician_id
        != getattr(actor, "id", None)
    ):
        raise FieldOperationsDomainError(
            "Technician can only complete assigned work orders."
        )

    completion_notes = completion_notes.strip()

    if not completion_notes:
        raise FieldOperationsDomainError(
            "Completion notes are required "
            "to complete a work order."
        )

    work_order.completion_notes = completion_notes
    work_order.completed_at = timezone.now()
    work_order.status = WorkOrder.Status.COMPLETED

    work_order.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="FIELD_WORK_ORDER_COMPLETED",
        resource_type="WorkOrder",
        resource_id=work_order.id,
        metadata={
            "work_order_number": (
                work_order.work_order_number
            ),
            "technician_id": str(
                work_order.assigned_technician_id
            ),
        },
    )

    return WorkOrderResult(
        work_order=work_order,
    )