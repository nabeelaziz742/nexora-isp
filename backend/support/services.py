from dataclasses import dataclass
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from customers.models import Customer, ServiceAccount
from network.models import NetworkNode
from support.automation import (
    queue_incident_opened_notifications,
)
from support.models import (
    Complaint,
    Incident,
    IncidentAffectedService,
)
from tenancy.models import Organization
from tenancy.services import record_audit_log


class SupportDomainError(Exception):
    pass


@dataclass(frozen=True)
class ComplaintResult:
    complaint: Complaint


@dataclass(frozen=True)
class IncidentResult:
    incident: Incident


def _generate_complaint_number() -> str:
    return f"CMP-{uuid4().hex[:12].upper()}"


def _generate_incident_number() -> str:
    return f"INC-{uuid4().hex[:12].upper()}"


@transaction.atomic
def create_complaint(
    *,
    organization: Organization,
    customer_id,
    category: str,
    priority: str,
    subject: str,
    description: str,
    service_account_id=None,
    created_by=None,
) -> ComplaintResult:
    if not organization.is_active:
        raise SupportDomainError(
            "Organization is not active."
        )

    if category not in Complaint.Category.values:
        raise SupportDomainError(
            "Invalid complaint category."
        )

    if priority not in Complaint.Priority.values:
        raise SupportDomainError(
            "Invalid complaint priority."
        )

    subject = subject.strip()
    description = description.strip()

    if not subject:
        raise SupportDomainError(
            "Complaint subject is required."
        )

    if not description:
        raise SupportDomainError(
            "Complaint description is required."
        )

    try:
        customer = (
            Customer.objects
            .for_organization(organization)
            .get(
                id=customer_id,
                is_active=True,
            )
        )
    except Customer.DoesNotExist as exc:
        raise SupportDomainError(
            "Active customer was not found "
            "for this organization."
        ) from exc

    service_account = None

    if service_account_id is not None:
        try:
            service_account = (
                ServiceAccount.objects
                .for_organization(organization)
                .get(
                    id=service_account_id,
                    customer=customer,
                )
            )
        except ServiceAccount.DoesNotExist as exc:
            raise SupportDomainError(
                "Service account was not found for "
                "this customer and organization."
            ) from exc

    complaint = Complaint.objects.create(
        organization=organization,
        complaint_number=_generate_complaint_number(),
        customer=customer,
        service_account=service_account,
        category=category,
        priority=priority,
        status=Complaint.Status.OPEN,
        subject=subject,
        description=description,
        created_by=created_by,
    )

    record_audit_log(
        organization=organization,
        actor=created_by,
        action="SUPPORT_COMPLAINT_CREATED",
        resource_type="Complaint",
        resource_id=complaint.id,
        metadata={
            "complaint_number": complaint.complaint_number,
            "customer_id": str(customer.id),
            "service_account_id": (
                str(service_account.id)
                if service_account
                else ""
            ),
            "priority": complaint.priority,
            "category": complaint.category,
        },
    )

    return ComplaintResult(
        complaint=complaint,
    )


@transaction.atomic
def transition_complaint_status(
    *,
    organization: Organization,
    complaint_id,
    target_status: str,
    resolution_notes: str = "",
    actor=None,
) -> ComplaintResult:
    try:
        complaint = (
            Complaint.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=complaint_id)
        )
    except Complaint.DoesNotExist as exc:
        raise SupportDomainError(
            "Complaint was not found "
            "for this organization."
        ) from exc

    allowed_transitions = {
        Complaint.Status.OPEN: {
            Complaint.Status.IN_PROGRESS,
        },
        Complaint.Status.IN_PROGRESS: {
            Complaint.Status.RESOLVED,
        },
        Complaint.Status.RESOLVED: {
            Complaint.Status.CLOSED,
        },
        Complaint.Status.CLOSED: set(),
    }

    if target_status not in Complaint.Status.values:
        raise SupportDomainError(
            "Invalid complaint status."
        )

    if target_status not in allowed_transitions[
        complaint.status
    ]:
        raise SupportDomainError(
            "Complaint status transition is not allowed."
        )

    if target_status == Complaint.Status.RESOLVED:
        resolution_notes = resolution_notes.strip()

        if not resolution_notes:
            raise SupportDomainError(
                "Resolution notes are required "
                "to resolve a complaint."
            )

        complaint.resolution_notes = resolution_notes
        complaint.resolved_by = actor
        complaint.resolved_at = timezone.now()

    if target_status == Complaint.Status.CLOSED:
        complaint.closed_at = timezone.now()

    previous_status = complaint.status
    complaint.status = target_status

    complaint.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="SUPPORT_COMPLAINT_STATUS_CHANGED",
        resource_type="Complaint",
        resource_id=complaint.id,
        metadata={
            "complaint_number": complaint.complaint_number,
            "previous_status": previous_status,
            "target_status": target_status,
        },
    )

    return ComplaintResult(
        complaint=complaint,
    )


@transaction.atomic
def create_incident(
    *,
    organization: Organization,
    title: str,
    description: str,
    severity: str,
    started_at,
    network_node_id=None,
    affected_service_ids=None,
    created_by=None,
) -> IncidentResult:
    if not organization.is_active:
        raise SupportDomainError(
            "Organization is not active."
        )

    if severity not in Incident.Severity.values:
        raise SupportDomainError(
            "Invalid incident severity."
        )

    title = title.strip()
    description = description.strip()

    if not title:
        raise SupportDomainError(
            "Incident title is required."
        )

    if not description:
        raise SupportDomainError(
            "Incident description is required."
        )

    if started_at is None:
        raise SupportDomainError(
            "Incident start time is required."
        )

    network_node = None

    if network_node_id is not None:
        try:
            network_node = (
                NetworkNode.objects
                .for_organization(organization)
                .get(id=network_node_id)
            )
        except NetworkNode.DoesNotExist as exc:
            raise SupportDomainError(
                "Network node was not found "
                "for this organization."
            ) from exc

    service_ids = list(
        dict.fromkeys(affected_service_ids or [])
    )

    services = []

    if service_ids:
        services = list(
            ServiceAccount.objects
            .for_organization(organization)
            .filter(id__in=service_ids)
        )

        if len(services) != len(service_ids):
            raise SupportDomainError(
                "One or more affected services were not "
                "found for this organization."
            )

    incident = Incident.objects.create(
        organization=organization,
        incident_number=_generate_incident_number(),
        network_node=network_node,
        title=title,
        description=description,
        severity=severity,
        status=Incident.Status.OPEN,
        started_at=started_at,
        created_by=created_by,
    )

    IncidentAffectedService.objects.bulk_create(
        [
            IncidentAffectedService(
                organization=organization,
                incident=incident,
                service_account=service_account,
            )
            for service_account in services
        ]
    )

    record_audit_log(
        organization=organization,
        actor=created_by,
        action="SUPPORT_INCIDENT_CREATED",
        resource_type="Incident",
        resource_id=incident.id,
        metadata={
            "incident_number": incident.incident_number,
            "severity": incident.severity,
            "network_node_id": (
                str(network_node.id)
                if network_node
                else ""
            ),
            "affected_service_count": len(services),
        },
    )

    queue_incident_opened_notifications(
        organization=organization,
        incident=incident,
        actor=created_by,
    )

    return IncidentResult(
        incident=incident,
    )


@transaction.atomic
def transition_incident_status(
    *,
    organization: Organization,
    incident_id,
    target_status: str,
    root_cause: str = "",
    resolution_notes: str = "",
    actor=None,
) -> IncidentResult:
    try:
        incident = (
            Incident.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=incident_id)
        )
    except Incident.DoesNotExist as exc:
        raise SupportDomainError(
            "Incident was not found "
            "for this organization."
        ) from exc

    allowed_transitions = {
        Incident.Status.OPEN: {
            Incident.Status.INVESTIGATING,
        },
        Incident.Status.INVESTIGATING: {
            Incident.Status.IDENTIFIED,
        },
        Incident.Status.IDENTIFIED: {
            Incident.Status.MONITORING,
        },
        Incident.Status.MONITORING: {
            Incident.Status.RESOLVED,
        },
        Incident.Status.RESOLVED: set(),
    }

    if target_status not in Incident.Status.values:
        raise SupportDomainError(
            "Invalid incident status."
        )

    if target_status not in allowed_transitions[
        incident.status
    ]:
        raise SupportDomainError(
            "Incident status transition is not allowed."
        )

    if target_status == Incident.Status.IDENTIFIED:
        root_cause = root_cause.strip()

        if not root_cause:
            raise SupportDomainError(
                "Root cause is required when "
                "an incident is identified."
            )

        incident.root_cause = root_cause

    if target_status == Incident.Status.RESOLVED:
        resolution_notes = resolution_notes.strip()

        if not resolution_notes:
            raise SupportDomainError(
                "Resolution notes are required "
                "to resolve an incident."
            )

        incident.resolution_notes = resolution_notes
        incident.resolved_by = actor
        incident.resolved_at = timezone.now()

    previous_status = incident.status
    incident.status = target_status

    incident.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="SUPPORT_INCIDENT_STATUS_CHANGED",
        resource_type="Incident",
        resource_id=incident.id,
        metadata={
            "incident_number": incident.incident_number,
            "previous_status": previous_status,
            "target_status": target_status,
        },
    )

    return IncidentResult(
        incident=incident,
    )