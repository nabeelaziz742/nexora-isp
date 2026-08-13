from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from customers.models import (
    Customer,
    NotificationPreference,
    ServiceAccount,
)
from notifications.models import NotificationJob
from tenancy.models import Organization
from tenancy.services import record_audit_log


class NotificationDomainError(Exception):
    pass


@dataclass(frozen=True)
class NotificationJobResult:
    notification_job: NotificationJob


def _is_channel_enabled(
    *,
    preference: NotificationPreference,
    channel: str,
) -> bool:
    if channel == NotificationJob.Channel.SMS:
        return preference.sms_enabled

    if channel == NotificationJob.Channel.WHATSAPP:
        return preference.whatsapp_enabled

    return False


def _resolve_recipient(
    *,
    customer: Customer,
    channel: str,
) -> str:
    if channel in (
        NotificationJob.Channel.SMS,
        NotificationJob.Channel.WHATSAPP,
    ):
        return customer.phone.strip()

    raise NotificationDomainError(
        "Unsupported notification channel."
    )


@transaction.atomic
def queue_customer_notification(
    *,
    organization: Organization,
    customer_id,
    channel: str,
    event_type: str,
    message: str,
    service_account_id=None,
    subject: str = "",
    context=None,
    actor=None,
) -> NotificationJobResult:
    if not organization.is_active:
        raise NotificationDomainError(
            "Organization is not active."
        )

    if channel not in NotificationJob.Channel.values:
        raise NotificationDomainError(
            "Invalid notification channel."
        )

    event_type = event_type.strip()
    message = message.strip()
    subject = subject.strip()

    if not event_type:
        raise NotificationDomainError(
            "Notification event type is required."
        )

    if not message:
        raise NotificationDomainError(
            "Notification message is required."
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
        raise NotificationDomainError(
            "Active customer was not found "
            "for this organization."
        ) from exc

    try:
        preference = (
            NotificationPreference.objects
            .for_organization(organization)
            .get(customer=customer)
        )
    except NotificationPreference.DoesNotExist as exc:
        raise NotificationDomainError(
            "Notification preference was not found "
            "for this customer."
        ) from exc

    if not _is_channel_enabled(
        preference=preference,
        channel=channel,
    ):
        raise NotificationDomainError(
            "Selected notification channel is disabled "
            "for this customer."
        )

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
            raise NotificationDomainError(
                "Service account was not found for this "
                "customer and organization."
            ) from exc

    recipient = _resolve_recipient(
        customer=customer,
        channel=channel,
    )

    if not recipient:
        raise NotificationDomainError(
            "Notification recipient is required."
        )

    notification_job = NotificationJob.objects.create(
        organization=organization,
        customer=customer,
        service_account=service_account,
        channel=channel,
        status=NotificationJob.Status.PENDING,
        event_type=event_type,
        recipient=recipient,
        subject=subject,
        message=message,
        context=context or {},
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="NOTIFICATION_JOB_QUEUED",
        resource_type="NotificationJob",
        resource_id=notification_job.id,
        metadata={
            "customer_id": str(customer.id),
            "service_account_id": (
                str(service_account.id)
                if service_account
                else ""
            ),
            "channel": notification_job.channel,
            "event_type": notification_job.event_type,
            "status": notification_job.status,
        },
    )

    return NotificationJobResult(
        notification_job=notification_job,
    )


@transaction.atomic
def start_notification_processing(
    *,
    organization: Organization,
    notification_job_id,
    provider_name: str,
    actor=None,
) -> NotificationJobResult:
    try:
        notification_job = (
            NotificationJob.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=notification_job_id)
        )
    except NotificationJob.DoesNotExist as exc:
        raise NotificationDomainError(
            "Notification job was not found "
            "for this organization."
        ) from exc

    if notification_job.status != NotificationJob.Status.PENDING:
        raise NotificationDomainError(
            "Only a pending notification job "
            "can start processing."
        )

    provider_name = provider_name.strip()

    if not provider_name:
        raise NotificationDomainError(
            "Notification provider name is required."
        )

    notification_job.status = NotificationJob.Status.PROCESSING
    notification_job.provider_name = provider_name
    notification_job.processing_started_at = timezone.now()
    notification_job.attempt_count += 1
    notification_job.failure_reason = ""
    notification_job.failed_at = None

    notification_job.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="NOTIFICATION_JOB_PROCESSING_STARTED",
        resource_type="NotificationJob",
        resource_id=notification_job.id,
        metadata={
            "channel": notification_job.channel,
            "event_type": notification_job.event_type,
            "provider_name": notification_job.provider_name,
            "attempt_count": notification_job.attempt_count,
        },
    )

    return NotificationJobResult(
        notification_job=notification_job,
    )


@transaction.atomic
def mark_notification_sent(
    *,
    organization: Organization,
    notification_job_id,
    provider_message_id: str,
    actor=None,
) -> NotificationJobResult:
    try:
        notification_job = (
            NotificationJob.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=notification_job_id)
        )
    except NotificationJob.DoesNotExist as exc:
        raise NotificationDomainError(
            "Notification job was not found "
            "for this organization."
        ) from exc

    if (
        notification_job.status
        != NotificationJob.Status.PROCESSING
    ):
        raise NotificationDomainError(
            "Only a processing notification job "
            "can be marked as sent."
        )

    provider_message_id = provider_message_id.strip()

    if not provider_message_id:
        raise NotificationDomainError(
            "Provider message ID is required "
            "to mark notification as sent."
        )

    notification_job.status = NotificationJob.Status.SENT
    notification_job.provider_message_id = provider_message_id
    notification_job.sent_at = timezone.now()
    notification_job.failure_reason = ""
    notification_job.failed_at = None

    notification_job.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="NOTIFICATION_JOB_SENT",
        resource_type="NotificationJob",
        resource_id=notification_job.id,
        metadata={
            "channel": notification_job.channel,
            "event_type": notification_job.event_type,
            "provider_name": notification_job.provider_name,
            "provider_message_id": (
                notification_job.provider_message_id
            ),
        },
    )

    return NotificationJobResult(
        notification_job=notification_job,
    )


@transaction.atomic
def mark_notification_failed(
    *,
    organization: Organization,
    notification_job_id,
    failure_reason: str,
    actor=None,
) -> NotificationJobResult:
    try:
        notification_job = (
            NotificationJob.objects
            .for_organization(organization)
            .select_for_update()
            .get(id=notification_job_id)
        )
    except NotificationJob.DoesNotExist as exc:
        raise NotificationDomainError(
            "Notification job was not found "
            "for this organization."
        ) from exc

    if (
        notification_job.status
        != NotificationJob.Status.PROCESSING
    ):
        raise NotificationDomainError(
            "Only a processing notification job "
            "can be marked as failed."
        )

    failure_reason = failure_reason.strip()

    if not failure_reason:
        raise NotificationDomainError(
            "Failure reason is required "
            "to mark notification as failed."
        )

    notification_job.status = NotificationJob.Status.FAILED
    notification_job.failure_reason = failure_reason
    notification_job.failed_at = timezone.now()
    notification_job.sent_at = None
    notification_job.provider_message_id = ""

    notification_job.save()

    record_audit_log(
        organization=organization,
        actor=actor,
        action="NOTIFICATION_JOB_FAILED",
        resource_type="NotificationJob",
        resource_id=notification_job.id,
        metadata={
            "channel": notification_job.channel,
            "event_type": notification_job.event_type,
            "provider_name": notification_job.provider_name,
            "failure_reason": notification_job.failure_reason,
        },
    )

    return NotificationJobResult(
        notification_job=notification_job,
    )