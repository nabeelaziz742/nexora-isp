from django.db import transaction
from django.template import Context, Template
from django.utils import timezone

from .models import (
    CommunicationAutomation,
    CommunicationLog,
    CommunicationQueue,
)


class CommunicationAutomationService:
    """Execute event-based communication automations."""

    @classmethod
    def execute_trigger(
        cls,
        *,
        organization,
        trigger,
        customer=None,
        invoice=None,
        complaint=None,
        work_order=None,
        lifecycle_event=None,
        provisioning_request_id=None,
    ):
        automations = (
            CommunicationAutomation.objects.select_related(
                "template",
                "template__communication_provider",
            ).filter(
                organization=organization,
                trigger=trigger,
                is_enabled=True,
            ).order_by("execution_order")
        )

        queues = []
        for automation in automations:
            queue = cls.execute_automation(
                automation=automation,
                customer=customer,
                invoice=invoice,
                complaint=complaint,
                work_order=work_order,
                lifecycle_event=lifecycle_event or trigger,
                provisioning_request_id=provisioning_request_id,
            )
            if queue is not None:
                queues.append(queue)
        return queues

    @classmethod
    @transaction.atomic
    def execute_automation(
        cls,
        *,
        automation,
        customer=None,
        invoice=None,
        complaint=None,
        work_order=None,
        lifecycle_event=None,
        provisioning_request_id=None,
    ):
        provider = automation.template.communication_provider

        # Never enqueue from a stale, cross-tenant, inactive, or archived
        # communication configuration. This protects direct service callers
        # that bypass serializer validation.
        if (
            automation.organization_id != automation.template.organization_id
            or automation.organization_id != provider.organization_id
            or not provider.is_connected
            or provider.status != provider.Status.ACTIVE
            or automation.template.status != automation.template.Status.ACTIVE
        ):
            automation.last_execution_status = "SKIPPED"
            automation.last_executed_at = timezone.now()
            automation.save(
                update_fields=["last_executed_at", "last_execution_status"]
            )
            return None

        if customer is not None and customer.organization_id != automation.organization_id:
            automation.last_execution_status = "SKIPPED"
            automation.last_executed_at = timezone.now()
            automation.save(
                update_fields=["last_executed_at", "last_execution_status"]
            )
            return None

        context = cls.build_context(
            customer=customer,
            invoice=invoice,
            complaint=complaint,
            work_order=work_order,
        )

        if invoice:
            context["invoice_id"] = str(invoice.id)
        if lifecycle_event:
            context["lifecycle_event"] = str(lifecycle_event)
        if provisioning_request_id:
            context["provisioning_request_id"] = str(provisioning_request_id)

        recipient = cls.get_recipient(customer, provider.provider_type)
        if not recipient:
            automation.last_execution_status = "SKIPPED"
            automation.last_executed_at = timezone.now()
            automation.save(update_fields=["last_executed_at", "last_execution_status"])
            return None

        rendered_subject = cls.render_template(automation.template.subject, context)
        rendered_body = cls.render_template(automation.template.body, context)

        scheduled_at = timezone.now()
        if automation.delay_minutes:
            scheduled_at += timezone.timedelta(minutes=automation.delay_minutes)

        queue = CommunicationQueue.objects.create(
            organization=automation.organization,
            customer=customer,
            template=automation.template,
            provider=provider,
            recipient=recipient,
            payload=context,
            rendered_subject=rendered_subject,
            rendered_body=rendered_body,
            scheduled_at=scheduled_at,
            max_attempts=max(1, automation.max_retry_attempts),
        )

        CommunicationLog.objects.create(
            organization=automation.organization,
            queue=queue,
            recipient=queue.recipient,
            subject=rendered_subject,
            message=rendered_body,
        )

        automation.last_executed_at = timezone.now()
        automation.last_execution_status = "QUEUED"
        automation.save(update_fields=["last_executed_at", "last_execution_status"])
        return queue

    @staticmethod
    def render_template(template_text, context):
        if not template_text:
            return ""
        return Template(template_text).render(Context(context))

    @staticmethod
    def build_context(*, customer=None, invoice=None, complaint=None, work_order=None):
        context = {}
        if customer:
            context.update(
                {
                    "customer_name": customer.full_name,
                    "customer_email": getattr(customer, "email", ""),
                    "customer_phone": (
                        getattr(customer, "phone", "")
                        or getattr(customer, "phone_number", "")
                        or getattr(customer, "alternate_phone", "")
                    ),
                    "organization_name": customer.organization.name,
                }
            )
        if invoice:
            context.update(
                {
                    "invoice_number": invoice.invoice_number,
                    "due_date": invoice.due_date.isoformat() if invoice.due_date else "",
                }
            )
        if complaint:
            context.update(
                {
                    "ticket_number": complaint.ticket_number,
                    "ticket_subject": complaint.subject,
                }
            )
        if work_order:
            context["work_order_number"] = work_order.work_order_number
        return context

    @staticmethod
    def get_recipient(customer, provider_type):
        if customer is None:
            return ""
        if provider_type == "EMAIL":
            return getattr(customer, "email", "") or ""
        return (
            getattr(customer, "phone", "")
            or getattr(customer, "phone_number", "")
            or getattr(customer, "alternate_phone", "")
            or ""
        )
