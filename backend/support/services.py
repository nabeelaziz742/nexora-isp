import logging
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from django.db import models, transaction
from django.db.models import Avg, Count, F, Q
from django.utils import timezone

from accounts.models import User
from communications.notification_engine import (
    NotificationEvent,
    dispatch_notification_event,
)
from customers.models import Customer, ServiceAccount
from network.models import NetworkNode
from support.models import (
    Complaint,
    ComplaintAttachment,
    ComplaintInternalNote,
    ComplaintSLAPolicy,
    ComplaintTimeline,
    Incident,
    IncidentAffectedService,
)
from tenancy.models import Organization, OrganizationMembership
from tenancy.services import record_audit_log

logger = logging.getLogger(__name__)


class SupportDomainError(Exception):
    pass


@dataclass(frozen=True)
class ComplaintResult:
    complaint: Complaint


@dataclass(frozen=True)
class IncidentResult:
    incident: Incident


def _generate_complaint_number() -> str:
    return f"CMP-{uuid4().hex[:10].upper()}"


def _generate_incident_number() -> str:
    return f"INC-{uuid4().hex[:10].upper()}"


def calculate_complaint_sla(organization: Organization, priority: str):
    """
    Calculates SLA response and resolution due timestamps based on tenant policy or defaults.
    """
    now = timezone.now()
    policy = ComplaintSLAPolicy.objects.filter(
        organization=organization,
        priority=priority,
        is_active=True,
    ).first()

    if policy:
        response_minutes = policy.response_target_minutes
        resolution_hours = policy.resolution_target_hours
    else:
        # Default industry standards
        defaults = {
            Complaint.Priority.CRITICAL: (15, 4),    # 15 mins response, 4 hours resolution
            Complaint.Priority.HIGH: (30, 8),        # 30 mins response, 8 hours resolution
            Complaint.Priority.MEDIUM: (60, 24),     # 60 mins response, 24 hours resolution
            Complaint.Priority.LOW: (120, 48),       # 120 mins response, 48 hours resolution
        }
        response_minutes, resolution_hours = defaults.get(priority, (60, 24))

    response_due_at = now + timedelta(minutes=response_minutes)
    resolution_due_at = now + timedelta(hours=resolution_hours)
    return response_due_at, resolution_due_at


@transaction.atomic
def create_complaint(
    *,
    organization: Organization,
    customer_id,
    category: str,
    priority: str,
    subject: str,
    description: str,
    source: str = Complaint.Source.STAFF,
    service_account_id=None,
    assigned_to_id=None,
    linked_incident_id=None,
    created_by=None,
) -> ComplaintResult:
    if not organization.is_active:
        raise SupportDomainError("Organization is not active.")

    if category not in Complaint.Category.values:
        raise SupportDomainError(f"Invalid complaint category: {category}")

    if priority not in Complaint.Priority.values:
        raise SupportDomainError(f"Invalid complaint priority: {priority}")

    if source not in Complaint.Source.values:
        raise SupportDomainError(f"Invalid complaint source: {source}")

    subject = subject.strip()
    description = description.strip()

    if not subject:
        raise SupportDomainError("Complaint subject is required.")

    if not description:
        raise SupportDomainError("Complaint description is required.")

    try:
        customer = (
            Customer.objects
            .for_organization(organization)
            .get(id=customer_id, is_active=True)
        )
    except Customer.DoesNotExist as exc:
        raise SupportDomainError("Active customer was not found for this organization.") from exc

    service_account = None
    if service_account_id is not None:
        try:
            service_account = (
                ServiceAccount.objects
                .for_organization(organization)
                .get(id=service_account_id, customer=customer)
            )
        except ServiceAccount.DoesNotExist as exc:
            raise SupportDomainError("Service account was not found for this customer.") from exc

    assigned_to = None
    assigned_by = None
    assigned_at = None
    initial_status = Complaint.Status.OPEN

    if assigned_to_id is not None:
        try:
            membership = OrganizationMembership.objects.get(
                organization=organization,
                user_id=assigned_to_id,
                is_active=True,
                user__is_active=True,
            )
            assigned_to = membership.user
            assigned_by = created_by
            assigned_at = timezone.now()
            initial_status = Complaint.Status.ASSIGNED
        except OrganizationMembership.DoesNotExist as exc:
            raise SupportDomainError("Active staff member was not found for assignment.") from exc

    linked_incident = None
    if linked_incident_id is not None:
        try:
            linked_incident = Incident.objects.for_organization(organization).get(id=linked_incident_id)
        except Incident.DoesNotExist as exc:
            raise SupportDomainError("Linked incident was not found for this organization.") from exc

    response_due_at, resolution_due_at = calculate_complaint_sla(organization, priority)

    complaint = Complaint.objects.create(
        organization=organization,
        complaint_number=_generate_complaint_number(),
        customer=customer,
        service_account=service_account,
        category=category,
        priority=priority,
        source=source,
        status=initial_status,
        subject=subject,
        description=description,
        assigned_to=assigned_to,
        assigned_by=assigned_by,
        assigned_at=assigned_at,
        response_due_at=response_due_at,
        resolution_due_at=resolution_due_at,
        sla_status=Complaint.SLAStatus.ON_TRACK,
        linked_incident=linked_incident,
        created_by=created_by,
    )

    # Initial timeline entry
    ComplaintTimeline.objects.create(
        organization=organization,
        complaint=complaint,
        event_type="CREATED",
        actor=created_by,
        new_value=initial_status,
        summary=f"Complaint {complaint.complaint_number} registered via {source}",
        notes=description,
        metadata={
            "category": category,
            "priority": priority,
            "source": source,
            "assigned_to": str(assigned_to.id) if assigned_to else None,
        },
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
            "service_account_id": str(service_account.id) if service_account else "",
            "priority": complaint.priority,
            "category": complaint.category,
            "source": complaint.source,
            "status": complaint.status,
        },
    )

    # Dispatch notification event
    try:
        dispatch_notification_event(
            organization=organization,
            customer=customer,
            event_type=NotificationEvent.COMPLAINT_CREATED,
            context={
                "customer_name": f"{customer.first_name} {customer.last_name}".strip(),
                "complaint_number": complaint.complaint_number,
                "subject": complaint.subject,
                "category": complaint.category,
                "priority": complaint.priority,
                "service_number": service_account.service_number if service_account else "",
            },
        )
    except Exception as notify_err:
        logger.warning("Failed to dispatch complaint created notification: %s", notify_err)

    return ComplaintResult(complaint=complaint)


@transaction.atomic
def assign_complaint(
    *,
    organization: Organization,
    complaint_id,
    technician_id,
    notes: str = "",
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
        raise SupportDomainError("Complaint was not found for this organization.") from exc

    if complaint.status in {Complaint.Status.CLOSED, Complaint.Status.CANCELLED}:
        raise SupportDomainError("Cannot assign a closed or cancelled complaint.")

    try:
        membership = OrganizationMembership.objects.get(
            organization=organization,
            user_id=technician_id,
            is_active=True,
            user__is_active=True,
        )
    except OrganizationMembership.DoesNotExist as exc:
        raise SupportDomainError("Active technician or staff member was not found for this organization.") from exc

    technician = membership.user
    previous_assignee = complaint.assigned_to
    complaint.assigned_to = technician
    complaint.assigned_by = actor
    complaint.assigned_at = timezone.now()

    if complaint.status in {Complaint.Status.NEW, Complaint.Status.OPEN, Complaint.Status.ACKNOWLEDGED}:
        complaint.status = Complaint.Status.ASSIGNED

    complaint.save(update_fields=["assigned_to", "assigned_by", "assigned_at", "status", "updated_at"])

    # Timeline entry
    ComplaintTimeline.objects.create(
        organization=organization,
        complaint=complaint,
        event_type="ASSIGNED",
        actor=actor,
        previous_value=previous_assignee.email if previous_assignee else "Unassigned",
        new_value=technician.email,
        summary=f"Assigned to {technician.email}",
        notes=notes.strip(),
        metadata={
            "technician_id": str(technician.id),
            "technician_email": technician.email,
        },
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="SUPPORT_COMPLAINT_ASSIGNED",
        resource_type="Complaint",
        resource_id=complaint.id,
        metadata={
            "complaint_number": complaint.complaint_number,
            "assigned_to": str(technician.id),
            "assigned_to_email": technician.email,
            "status": complaint.status,
        },
    )

    # Dispatch notification to customer
    try:
        dispatch_notification_event(
            organization=organization,
            customer=complaint.customer,
            event_type=NotificationEvent.COMPLAINT_ASSIGNED,
            context={
                "customer_name": f"{complaint.customer.first_name} {complaint.customer.last_name}".strip(),
                "complaint_number": complaint.complaint_number,
                "technician_name": technician.email.split("@")[0],
                "subject": complaint.subject,
            },
        )
    except Exception as notify_err:
        logger.warning("Failed to dispatch complaint assigned notification: %s", notify_err)

    return ComplaintResult(complaint=complaint)


@transaction.atomic
def reassign_complaint(
    *,
    organization: Organization,
    complaint_id,
    technician_id,
    reason: str,
    notes: str = "",
    actor=None,
) -> ComplaintResult:
    reason = reason.strip()
    if not reason:
        raise SupportDomainError("Reassignment reason is required.")

    try:
        complaint = (
            Complaint.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=complaint_id)
        )
    except Complaint.DoesNotExist as exc:
        raise SupportDomainError("Complaint was not found for this organization.") from exc

    if complaint.status in {Complaint.Status.CLOSED, Complaint.Status.CANCELLED}:
        raise SupportDomainError("Cannot reassign a closed or cancelled complaint.")

    try:
        membership = OrganizationMembership.objects.get(
            organization=organization,
            user_id=technician_id,
            is_active=True,
            user__is_active=True,
        )
    except OrganizationMembership.DoesNotExist as exc:
        raise SupportDomainError("Active staff member was not found.") from exc

    new_technician = membership.user
    old_technician = complaint.assigned_to

    complaint.assigned_to = new_technician
    complaint.assigned_by = actor
    complaint.assigned_at = timezone.now()
    complaint.reassignment_reason = reason
    complaint.save(update_fields=["assigned_to", "assigned_by", "assigned_at", "reassignment_reason", "updated_at"])

    ComplaintTimeline.objects.create(
        organization=organization,
        complaint=complaint,
        event_type="REASSIGNED",
        actor=actor,
        previous_value=old_technician.email if old_technician else "Unassigned",
        new_value=new_technician.email,
        summary=f"Reassigned to {new_technician.email}. Reason: {reason}",
        notes=notes.strip(),
        metadata={
            "reason": reason,
            "old_technician_id": str(old_technician.id) if old_technician else None,
            "new_technician_id": str(new_technician.id),
        },
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="SUPPORT_COMPLAINT_REASSIGNED",
        resource_type="Complaint",
        resource_id=complaint.id,
        metadata={
            "complaint_number": complaint.complaint_number,
            "new_technician_id": str(new_technician.id),
            "reason": reason,
        },
    )

    return ComplaintResult(complaint=complaint)


@transaction.atomic
def transition_complaint_status(
    *,
    organization: Organization,
    complaint_id,
    target_status: str,
    notes: str = "",
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
        raise SupportDomainError("Complaint was not found for this organization.") from exc

    if target_status not in Complaint.Status.values:
        raise SupportDomainError(f"Invalid target status: {target_status}")

    # Terminal state safeguards
    if complaint.status in {Complaint.Status.CLOSED, Complaint.Status.CANCELLED}:
        raise SupportDomainError("Cannot transition a closed or cancelled complaint.")

    allowed_transitions = {
        Complaint.Status.NEW: {
            Complaint.Status.ACKNOWLEDGED,
            Complaint.Status.ASSIGNED,
            Complaint.Status.IN_PROGRESS,
            Complaint.Status.CANCELLED,
        },
        Complaint.Status.OPEN: {
            Complaint.Status.ACKNOWLEDGED,
            Complaint.Status.ASSIGNED,
            Complaint.Status.IN_PROGRESS,
            Complaint.Status.RESOLVED,
            Complaint.Status.CANCELLED,
        },
        Complaint.Status.ACKNOWLEDGED: {
            Complaint.Status.ASSIGNED,
            Complaint.Status.IN_PROGRESS,
            Complaint.Status.WAITING_CUSTOMER,
            Complaint.Status.WAITING_PARTS,
            Complaint.Status.CANCELLED,
        },
        Complaint.Status.ASSIGNED: {
            Complaint.Status.IN_PROGRESS,
            Complaint.Status.WAITING_CUSTOMER,
            Complaint.Status.WAITING_PARTS,
            Complaint.Status.ESCALATED,
            Complaint.Status.CANCELLED,
        },
        Complaint.Status.IN_PROGRESS: {
            Complaint.Status.WAITING_CUSTOMER,
            Complaint.Status.WAITING_PARTS,
            Complaint.Status.ESCALATED,
            Complaint.Status.RESOLVED,
            Complaint.Status.CANCELLED,
        },
        Complaint.Status.WAITING_CUSTOMER: {
            Complaint.Status.IN_PROGRESS,
            Complaint.Status.RESOLVED,
            Complaint.Status.CANCELLED,
        },
        Complaint.Status.WAITING_PARTS: {
            Complaint.Status.IN_PROGRESS,
            Complaint.Status.RESOLVED,
            Complaint.Status.CANCELLED,
        },
        Complaint.Status.ESCALATED: {
            Complaint.Status.IN_PROGRESS,
            Complaint.Status.RESOLVED,
            Complaint.Status.CANCELLED,
        },
        Complaint.Status.RESOLVED: {
            Complaint.Status.CUSTOMER_CONFIRMED,
            Complaint.Status.CLOSED,
            Complaint.Status.IN_PROGRESS,  # In case customer reopens
        },
        Complaint.Status.CUSTOMER_CONFIRMED: {
            Complaint.Status.CLOSED,
        },
    }

    if target_status not in allowed_transitions.get(complaint.status, set()):
        raise SupportDomainError(
            f"Cannot transition complaint from {complaint.status} to {target_status}."
        )

    # First response tracking
    if complaint.first_response_at is None and target_status in {
        Complaint.Status.ACKNOWLEDGED,
        Complaint.Status.IN_PROGRESS,
        Complaint.Status.ASSIGNED,
    }:
        complaint.first_response_at = timezone.now()

    if target_status == Complaint.Status.RESOLVED:
        complaint.resolved_at = timezone.now()
        complaint.resolved_by = actor
        if resolution_notes:
            complaint.resolution_notes = resolution_notes.strip()

    if target_status == Complaint.Status.CLOSED:
        complaint.closed_at = timezone.now()

    previous_status = complaint.status
    complaint.status = target_status
    complaint.save()

    ComplaintTimeline.objects.create(
        organization=organization,
        complaint=complaint,
        event_type="STATUS_CHANGED",
        actor=actor,
        previous_value=previous_status,
        new_value=target_status,
        summary=f"Status changed from {previous_status} to {target_status}",
        notes=notes.strip(),
    )

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

    return ComplaintResult(complaint=complaint)


@transaction.atomic
def escalate_complaint(
    *,
    organization: Organization,
    complaint_id,
    reason: str,
    escalated_to_id=None,
    actor=None,
) -> ComplaintResult:
    reason = reason.strip()
    if not reason:
        raise SupportDomainError("Escalation reason is required.")

    try:
        complaint = (
            Complaint.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=complaint_id)
        )
    except Complaint.DoesNotExist as exc:
        raise SupportDomainError("Complaint was not found for this organization.") from exc

    if complaint.status in {Complaint.Status.CLOSED, Complaint.Status.CANCELLED}:
        raise SupportDomainError("Cannot escalate a closed or cancelled complaint.")

    escalated_to = None
    if escalated_to_id is not None:
        try:
            membership = OrganizationMembership.objects.get(
                organization=organization,
                user_id=escalated_to_id,
                is_active=True,
            )
            escalated_to = membership.user
        except OrganizationMembership.DoesNotExist as exc:
            raise SupportDomainError("Escalation target user was not found.") from exc

    previous_status = complaint.status
    complaint.is_escalated = True
    complaint.escalation_level += 1
    complaint.escalation_reason = reason
    complaint.escalated_by = actor
    complaint.escalated_at = timezone.now()
    complaint.escalated_to = escalated_to
    complaint.status = Complaint.Status.ESCALATED
    complaint.priority = Complaint.Priority.HIGH if complaint.priority == Complaint.Priority.LOW else complaint.priority

    complaint.save()

    ComplaintTimeline.objects.create(
        organization=organization,
        complaint=complaint,
        event_type="ESCALATED",
        actor=actor,
        previous_value=previous_status,
        new_value=Complaint.Status.ESCALATED,
        summary=f"Ticket escalated to level {complaint.escalation_level}. Reason: {reason}",
        notes=reason,
        metadata={
            "escalation_level": complaint.escalation_level,
            "escalated_to_id": str(escalated_to.id) if escalated_to else None,
        },
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="SUPPORT_COMPLAINT_ESCALATED",
        resource_type="Complaint",
        resource_id=complaint.id,
        metadata={
            "complaint_number": complaint.complaint_number,
            "escalation_level": complaint.escalation_level,
            "reason": reason,
        },
    )

    return ComplaintResult(complaint=complaint)


@transaction.atomic
def add_internal_note(
    *,
    organization: Organization,
    complaint_id,
    note: str,
    actor=None,
) -> ComplaintInternalNote:
    note = note.strip()
    if not note:
        raise SupportDomainError("Internal note content cannot be empty.")

    try:
        complaint = (
            Complaint.objects
            .for_organization(organization)
            .get(id=complaint_id)
        )
    except Complaint.DoesNotExist as exc:
        raise SupportDomainError("Complaint was not found for this organization.") from exc

    internal_note = ComplaintInternalNote.objects.create(
        organization=organization,
        complaint=complaint,
        author=actor,
        note=note,
        is_internal=True,
    )

    ComplaintTimeline.objects.create(
        organization=organization,
        complaint=complaint,
        event_type="NOTE_ADDED",
        actor=actor,
        summary=f"Internal staff note added by {actor.email if actor else 'Staff'}",
        notes=note,
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="SUPPORT_INTERNAL_NOTE_ADDED",
        resource_type="Complaint",
        resource_id=complaint.id,
        metadata={
            "complaint_number": complaint.complaint_number,
            "note_id": str(internal_note.id),
        },
    )

    return internal_note


@transaction.atomic
def resolve_complaint(
    *,
    organization: Organization,
    complaint_id,
    diagnosis_category: str,
    resolution_summary: str,
    resolution_notes: str = "",
    actor=None,
) -> ComplaintResult:
    diagnosis_category = diagnosis_category.strip()
    resolution_summary = resolution_summary.strip()

    if not diagnosis_category:
        raise SupportDomainError("Technical diagnosis category is required to resolve complaint.")

    if not resolution_summary:
        raise SupportDomainError("Resolution summary is required to resolve complaint.")

    try:
        complaint = (
            Complaint.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=complaint_id)
        )
    except Complaint.DoesNotExist as exc:
        raise SupportDomainError("Complaint was not found for this organization.") from exc

    if complaint.status in {Complaint.Status.CLOSED, Complaint.Status.CANCELLED}:
        raise SupportDomainError("Cannot resolve a closed or cancelled complaint.")

    previous_status = complaint.status
    complaint.diagnosis_category = diagnosis_category
    complaint.resolution_summary = resolution_summary
    complaint.resolution_notes = resolution_notes.strip()
    complaint.resolved_by = actor
    complaint.resolved_at = timezone.now()
    complaint.status = Complaint.Status.RESOLVED
    complaint.customer_confirmation = Complaint.CustomerConfirmation.PENDING

    if not complaint.is_resolution_sla_breached:
        complaint.sla_status = Complaint.SLAStatus.RESOLVED

    complaint.save()

    ComplaintTimeline.objects.create(
        organization=organization,
        complaint=complaint,
        event_type="RESOLVED",
        actor=actor,
        previous_value=previous_status,
        new_value=Complaint.Status.RESOLVED,
        summary=f"Complaint resolved: {resolution_summary}",
        notes=resolution_notes.strip(),
        metadata={
            "diagnosis_category": diagnosis_category,
            "resolution_summary": resolution_summary,
        },
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="SUPPORT_COMPLAINT_RESOLVED",
        resource_type="Complaint",
        resource_id=complaint.id,
        metadata={
            "complaint_number": complaint.complaint_number,
            "diagnosis_category": diagnosis_category,
            "resolution_summary": resolution_summary,
        },
    )

    # Dispatch resolution notification to customer
    try:
        dispatch_notification_event(
            organization=organization,
            customer=complaint.customer,
            event_type=NotificationEvent.COMPLAINT_RESOLVED,
            context={
                "customer_name": f"{complaint.customer.first_name} {complaint.customer.last_name}".strip(),
                "complaint_number": complaint.complaint_number,
                "resolution_summary": resolution_summary,
                "service_number": complaint.service_account.service_number if complaint.service_account else "",
            },
        )
    except Exception as notify_err:
        logger.warning("Failed to dispatch complaint resolved notification: %s", notify_err)

    return ComplaintResult(complaint=complaint)


@transaction.atomic
def confirm_and_close_complaint(
    *,
    organization: Organization,
    complaint_id,
    confirmation: str,
    feedback_rating: int | None = None,
    feedback_notes: str = "",
    actor=None,
) -> ComplaintResult:
    if confirmation not in Complaint.CustomerConfirmation.values:
        raise SupportDomainError(f"Invalid confirmation status: {confirmation}")

    try:
        complaint = (
            Complaint.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=complaint_id)
        )
    except Complaint.DoesNotExist as exc:
        raise SupportDomainError("Complaint was not found for this organization.") from exc

    if complaint.status != Complaint.Status.RESOLVED:
        raise SupportDomainError("Only a resolved complaint can be confirmed or closed.")

    complaint.customer_confirmation = confirmation
    complaint.customer_confirmed_at = timezone.now()
    if feedback_rating:
        complaint.customer_feedback_rating = max(1, min(5, feedback_rating))
    complaint.customer_feedback_notes = feedback_notes.strip()

    if confirmation == Complaint.CustomerConfirmation.CONFIRMED:
        complaint.status = Complaint.Status.CLOSED
        complaint.closed_at = timezone.now()
        event_summary = f"Customer confirmed resolution. Ticket closed with {complaint.customer_feedback_rating or 5}-star rating."
    elif confirmation == Complaint.CustomerConfirmation.REJECTED:
        complaint.status = Complaint.Status.IN_PROGRESS
        event_summary = f"Customer rejected resolution. Ticket reopened to In Progress. Notes: {feedback_notes}"
    else:
        complaint.status = Complaint.Status.CLOSED
        complaint.closed_at = timezone.now()
        event_summary = "Ticket closed by staff."

    complaint.save()

    ComplaintTimeline.objects.create(
        organization=organization,
        complaint=complaint,
        event_type="CONFIRMED" if confirmation == Complaint.CustomerConfirmation.CONFIRMED else "STATUS_CHANGED",
        actor=actor,
        new_value=complaint.status,
        summary=event_summary,
        notes=feedback_notes.strip(),
        metadata={
            "confirmation": confirmation,
            "rating": complaint.customer_feedback_rating,
        },
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="SUPPORT_COMPLAINT_CLOSED" if complaint.status == Complaint.Status.CLOSED else "SUPPORT_COMPLAINT_REOPENED",
        resource_type="Complaint",
        resource_id=complaint.id,
        metadata={
            "complaint_number": complaint.complaint_number,
            "confirmation": confirmation,
            "status": complaint.status,
        },
    )

    if complaint.status == Complaint.Status.CLOSED:
        try:
            dispatch_notification_event(
                organization=organization,
                customer=complaint.customer,
                event_type=NotificationEvent.COMPLAINT_CLOSED,
                context={
                    "customer_name": f"{complaint.customer.first_name} {complaint.customer.last_name}".strip(),
                    "complaint_number": complaint.complaint_number,
                },
            )
        except Exception as notify_err:
            logger.warning("Failed to dispatch complaint closed notification: %s", notify_err)

    return ComplaintResult(complaint=complaint)


def get_support_dashboard_metrics(organization: Organization) -> dict:
    """
    Real-time support operations KPI metrics and technician workload calculation.
    """
    now = timezone.now()
    qs = Complaint.objects.for_organization(organization)

    total_complaints = qs.count()

    open_statuses = [
        Complaint.Status.NEW,
        Complaint.Status.OPEN,
        Complaint.Status.ACKNOWLEDGED,
        Complaint.Status.ASSIGNED,
        Complaint.Status.IN_PROGRESS,
        Complaint.Status.WAITING_CUSTOMER,
        Complaint.Status.WAITING_PARTS,
        Complaint.Status.ESCALATED,
    ]

    open_complaints = qs.filter(status__in=open_statuses).count()
    critical_complaints = qs.filter(status__in=open_statuses, priority=Complaint.Priority.CRITICAL).count()
    unassigned_complaints = qs.filter(status__in=open_statuses, assigned_to__isnull=True).count()
    in_progress_complaints = qs.filter(status=Complaint.Status.IN_PROGRESS).count()
    waiting_complaints = qs.filter(status__in=[Complaint.Status.WAITING_CUSTOMER, Complaint.Status.WAITING_PARTS]).count()
    escalated_complaints = qs.filter(status=Complaint.Status.ESCALATED).count()
    resolved_complaints = qs.filter(status=Complaint.Status.RESOLVED).count()
    closed_complaints = qs.filter(status=Complaint.Status.CLOSED).count()

    # SLA breaches
    sla_breached_complaints = qs.filter(
        Q(is_resolution_sla_breached=True) |
        (Q(status__in=open_statuses) & Q(resolution_due_at__lt=now))
    ).count()

    # Category breakdown
    category_counts = (
        qs.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Priority breakdown
    priority_counts = (
        qs.values("priority")
        .annotate(count=Count("id"))
        .order_by("priority")
    )

    # Technician workload
    technicians = (
        OrganizationMembership.objects
        .filter(organization=organization, is_active=True)
        .select_related("user")
    )

    tech_workloads = []
    for membership in technicians:
        assigned_count = qs.filter(
            status__in=open_statuses,
            assigned_to=membership.user,
        ).count()
        tech_workloads.append({
            "technician_id": str(membership.user.id),
            "technician_name": f"{membership.user.first_name} {membership.user.last_name}".strip() or membership.user.email,
            "email": membership.user.email,
            "role": membership.role,
            "open_tickets": assigned_count,
        })

    # Average resolution time in hours for resolved/closed tickets
    resolved_qs = qs.filter(resolved_at__isnull=False)
    total_hours = 0.0
    count_resolved = 0
    for c in resolved_qs:
        if c.resolved_at and c.created_at:
            total_hours += (c.resolved_at - c.created_at).total_seconds() / 3600.0
            count_resolved += 1

    avg_resolution_hours = round(total_hours / count_resolved, 1) if count_resolved > 0 else 0.0

    return {
        "total_complaints": total_complaints,
        "open_complaints": open_complaints,
        "critical_complaints": critical_complaints,
        "unassigned_complaints": unassigned_complaints,
        "in_progress_complaints": in_progress_complaints,
        "waiting_complaints": waiting_complaints,
        "escalated_complaints": escalated_complaints,
        "resolved_complaints": resolved_complaints,
        "closed_complaints": closed_complaints,
        "sla_breached_complaints": sla_breached_complaints,
        "avg_resolution_hours": avg_resolution_hours,
        "category_breakdown": list(category_counts),
        "priority_breakdown": list(priority_counts),
        "technician_workloads": tech_workloads,
    }


# ==================== INCIDENT SERVICES (PRESERVED) ====================

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
        raise SupportDomainError("Organization is not active.")

    if severity not in Incident.Severity.values:
        raise SupportDomainError("Invalid incident severity.")

    title = title.strip()
    description = description.strip()

    if not title:
        raise SupportDomainError("Incident title is required.")

    if not description:
        raise SupportDomainError("Incident description is required.")

    if started_at is None:
        raise SupportDomainError("Incident start time is required.")

    network_node = None
    if network_node_id is not None:
        try:
            network_node = NetworkNode.objects.for_organization(organization).get(id=network_node_id)
        except NetworkNode.DoesNotExist as exc:
            raise SupportDomainError("Network node was not found for this organization.") from exc

    service_ids = list(dict.fromkeys(affected_service_ids or []))
    services = []
    if service_ids:
        services = list(ServiceAccount.objects.for_organization(organization).filter(id__in=service_ids))
        if len(services) != len(service_ids):
            raise SupportDomainError("One or more affected services were not found for this organization.")

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
            "network_node_id": str(network_node.id) if network_node else "",
            "affected_service_count": len(services),
        },
    )

    from support.automation import queue_incident_opened_notifications
    queue_incident_opened_notifications(
        organization=organization,
        incident=incident,
        actor=created_by,
    )

    return IncidentResult(incident=incident)


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
        raise SupportDomainError("Incident was not found for this organization.") from exc

    allowed_transitions = {
        Incident.Status.OPEN: {Incident.Status.INVESTIGATING},
        Incident.Status.INVESTIGATING: {Incident.Status.IDENTIFIED},
        Incident.Status.IDENTIFIED: {Incident.Status.MONITORING},
        Incident.Status.MONITORING: {Incident.Status.RESOLVED},
        Incident.Status.RESOLVED: set(),
    }

    if target_status not in Incident.Status.values:
        raise SupportDomainError("Invalid incident status.")

    if target_status not in allowed_transitions.get(incident.status, set()):
        raise SupportDomainError("Incident status transition is not allowed.")

    if target_status == Incident.Status.IDENTIFIED:
        root_cause = root_cause.strip()
        if not root_cause:
            raise SupportDomainError("Root cause is required when an incident is identified.")
        incident.root_cause = root_cause

    if target_status == Incident.Status.RESOLVED:
        resolution_notes = resolution_notes.strip()
        if not resolution_notes:
            raise SupportDomainError("Resolution notes are required to resolve an incident.")
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

    return IncidentResult(incident=incident)