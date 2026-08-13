from dataclasses import dataclass

from customers.models import NotificationPreference
from notifications.models import NotificationJob
from notifications.services import (
    NotificationDomainError,
    queue_customer_notification,
)
from support.models import Incident
from tenancy.models import Organization


@dataclass(frozen=True)
class IncidentNotificationAutomationSummary:
    incident: Incident
    affected_services: int
    queued_notifications: int
    skipped_notifications: int
    failed_notifications: int


def _resolve_customer_notification_channel(
    *,
    organization: Organization,
    customer_id,
) -> str | None:
    try:
        preference = (
            NotificationPreference.objects
            .for_organization(organization)
            .get(customer_id=customer_id)
        )
    except NotificationPreference.DoesNotExist:
        return None

    if preference.whatsapp_enabled:
        return NotificationJob.Channel.WHATSAPP

    if preference.sms_enabled:
        return NotificationJob.Channel.SMS

    return None


def _incident_notification_exists(
    *,
    organization: Organization,
    incident: Incident,
    service_account_id,
) -> bool:
    return (
        NotificationJob.objects
        .for_organization(organization)
        .filter(
            service_account_id=service_account_id,
            event_type="INCIDENT_OPENED",
            context__incident_id=str(incident.id),
        )
        .exists()
    )


def queue_incident_opened_notifications(
    *,
    organization: Organization,
    incident: Incident,
    actor=None,
) -> IncidentNotificationAutomationSummary:
    if incident.organization_id != organization.id:
        return IncidentNotificationAutomationSummary(
            incident=incident,
            affected_services=0,
            queued_notifications=0,
            skipped_notifications=0,
            failed_notifications=1,
        )

    affected_service_rows = (
        incident.affected_services
        .for_organization(organization)
        .select_related(
            "service_account",
            "service_account__customer",
        )
        .order_by("service_account__service_number")
    )

    affected_services = 0
    queued_notifications = 0
    skipped_notifications = 0
    failed_notifications = 0

    for affected_service in affected_service_rows:
        affected_services += 1

        service_account = affected_service.service_account
        customer = service_account.customer

        channel = _resolve_customer_notification_channel(
            organization=organization,
            customer_id=customer.id,
        )

        if channel is None:
            skipped_notifications += 1
            continue

        if _incident_notification_exists(
            organization=organization,
            incident=incident,
            service_account_id=service_account.id,
        ):
            skipped_notifications += 1
            continue

        try:
            queue_customer_notification(
                organization=organization,
                customer_id=customer.id,
                service_account_id=service_account.id,
                channel=channel,
                event_type="INCIDENT_OPENED",
                subject=(
                    f"Service Incident "
                    f"{incident.incident_number}"
                ),
                message=(
                    f"We are investigating a service incident "
                    f"affecting your NEXORA internet service "
                    f"{service_account.service_number}. "
                    f"Incident reference: "
                    f"{incident.incident_number}. "
                    f"Our operations team is working on it."
                ),
                context={
                    "incident_id": str(incident.id),
                    "incident_number": (
                        incident.incident_number
                    ),
                    "incident_title": incident.title,
                    "severity": incident.severity,
                    "status": incident.status,
                    "service_account_id": str(
                        service_account.id
                    ),
                    "service_number": (
                        service_account.service_number
                    ),
                    "network_node_id": (
                        str(incident.network_node_id)
                        if incident.network_node_id
                        else ""
                    ),
                },
                actor=actor,
            )
        except NotificationDomainError:
            failed_notifications += 1
            continue

        queued_notifications += 1

    return IncidentNotificationAutomationSummary(
        incident=incident,
        affected_services=affected_services,
        queued_notifications=queued_notifications,
        skipped_notifications=skipped_notifications,
        failed_notifications=failed_notifications,
    )