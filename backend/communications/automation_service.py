from django.db import transaction
from django.template import Context, Template
from django.utils import timezone

from .models import (
    CommunicationAutomation,
    CommunicationLog,
    CommunicationQueue,
)


class CommunicationAutomationService:
    """
    Executes event-based communication automations.

    Flow:
        Business Event
            ↓
        Find Enabled Automations
            ↓
        Render Template
            ↓
        Create Queue Item
            ↓
        Update Automation Status
    """

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
    ):
        automations = (
            CommunicationAutomation.objects.select_related(
                "template",
                "template__communication_provider",
            )
            .filter(
                organization=organization,
                trigger=trigger,
                is_enabled=True,
            )
            .order_by("execution_order")
        )

        for automation in automations:
            cls.execute_automation(
                automation=automation,
                customer=customer,
                invoice=invoice,
                complaint=complaint,
                work_order=work_order,
            )

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
    ):
        context = cls.build_context(
            customer=customer,
            invoice=invoice,
            complaint=complaint,
            work_order=work_order,
        )

        rendered_subject = cls.render_template(
            automation.template.subject,
            context,
        )

        rendered_body = cls.render_template(
            automation.template.body,
            context,
        )

        scheduled_at = timezone.now()

        if automation.delay_minutes:
            scheduled_at += timezone.timedelta(
                minutes=automation.delay_minutes
            )

        queue = CommunicationQueue.objects.create(
            organization=automation.organization,
            customer=customer,
            template=automation.template,
            provider=automation.template.communication_provider,
            recipient=cls.get_recipient(
                customer,
                automation.template.communication_provider.provider_type,
            ),
            payload=context,
            rendered_subject=rendered_subject,
            rendered_body=rendered_body,
            scheduled_at=scheduled_at,
        )

        CommunicationLog.objects.create(
            organization=automation.organization,
            queue=queue,
            recipient=queue.recipient,
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

        return queue

    @staticmethod
    def render_template(template_text, context):
        if not template_text:
            return ""

        return Template(template_text).render(
            Context(context)
        )

    @staticmethod
    def build_context(
        *,
        customer=None,
        invoice=None,
        complaint=None,
        work_order=None,
    ):
        context = {}

        if customer:
            context.update(
                {
                    "customer_name": customer.full_name,
                    "customer_email": getattr(customer, "email", ""),
                    "customer_phone": getattr(customer, "phone_number", ""),
                    "organization_name": customer.organization.name,
                }
            )

        if invoice:
            context.update(
                {
                    "invoice_number": invoice.invoice_number,
                    "invoice_number": invoice.invoice_number,
                    "due_date": invoice.due_date.isoformat()
                    if invoice.due_date
                    else "",
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
            context.update(
                {
                    "work_order_number": work_order.work_order_number,
                }
            )

        return context

    @staticmethod
    def get_recipient(customer, provider_type):
        if customer is None:
            return ""

        if provider_type == "EMAIL":
            return customer.email or ""

        return customer.phone or customer.alternate_phone or ""