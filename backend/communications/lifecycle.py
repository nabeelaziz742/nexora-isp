from django.db import transaction
from django.template import Context, Template
from django.utils import timezone

from .models import (
    CommunicationAutomation,
    CommunicationLog,
    CommunicationQueue,
)


def queue_lifecycle_trigger(
    *,
    organization,
    trigger,
    customer,
    context=None,
):
    """Queue all enabled templates configured for a lifecycle trigger."""
    context = dict(context or {})
    context.setdefault("customer_name", customer.full_name)
    context.setdefault("customer_email", getattr(customer, "email", ""))
    context.setdefault(
        "customer_phone",
        getattr(customer, "phone", "")
        or getattr(customer, "phone_number", "")
        or getattr(customer, "alternate_phone", ""),
    )
    context.setdefault("organization_name", organization.name)

    queued = []
    automations = (
        CommunicationAutomation.objects
        .select_related("template", "template__communication_provider")
        .filter(
            organization=organization,
            trigger=trigger,
            is_enabled=True,
        )
        .order_by("execution_order")
    )

    for automation in automations:
        provider = automation.template.communication_provider
        if not provider.is_connected or provider.status != "ACTIVE":
            continue

        recipient = (
            customer.email
            if provider.provider_type == "EMAIL"
            else context["customer_phone"]
        )
        if not recipient:
            continue

        rendered_subject = Template(
            automation.template.subject or ""
        ).render(Context(context))
        rendered_body = Template(
            automation.template.body
        ).render(Context(context))

        scheduled_at = timezone.now()
        if automation.delay_minutes:
            scheduled_at += timezone.timedelta(
                minutes=automation.delay_minutes
            )

        with transaction.atomic():
            queue = CommunicationQueue.objects.create(
                organization=organization,
                customer=customer,
                template=automation.template,
                provider=provider,
                recipient=recipient,
                payload=context,
                rendered_subject=rendered_subject,
                rendered_body=rendered_body,
                scheduled_at=scheduled_at,
                max_attempts=automation.max_retry_attempts,
            )
            CommunicationLog.objects.create(
                organization=organization,
                queue=queue,
                recipient=recipient,
                subject=rendered_subject,
                message=rendered_body,
            )
            automation.last_executed_at = timezone.now()
            automation.last_execution_status = "SUCCESS"
            automation.save(
                update_fields=[
                    "last_executed_at",
                    "last_execution_status",
                ]
            )

        queued.append(queue)

    return queued
