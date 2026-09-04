import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from communications.dispatcher import CommunicationDispatcher
from communications.models import (
    CommunicationLog,
    CommunicationProvider,
    CommunicationQueue,
    CommunicationTemplate,
)
from customers.models import (
    Customer,
    NotificationPreference,
)

logger = logging.getLogger(__name__)


class NotificationEvent:
    INVOICE_GENERATED = "INVOICE_GENERATED"
    BILL_DUE_REMINDER = "BILL_DUE_REMINDER"
    BILL_OVERDUE_REMINDER = "BILL_OVERDUE_REMINDER"
    SUSPENSION_WARNING = "SUSPENSION_WARNING"
    SERVICE_SUSPENDED = "SERVICE_SUSPENDED"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    PAYMENT_PARTIAL_RECEIVED = "PAYMENT_PARTIAL_RECEIVED"
    SERVICE_RESTORED = "SERVICE_RESTORED"
    PTP_CREATED = "PTP_CREATED"
    PTP_DEADLINE_APPROACHING = "PTP_DEADLINE_APPROACHING"
    PTP_BREACHED = "PTP_BREACHED"
    TICKET_CREATED = "TICKET_CREATED"
    COMPLAINT_CREATED = "COMPLAINT_CREATED"
    COMPLAINT_ACKNOWLEDGED = "COMPLAINT_ACKNOWLEDGED"
    COMPLAINT_ASSIGNED = "COMPLAINT_ASSIGNED"
    TECHNICIAN_DISPATCHED = "TECHNICIAN_DISPATCHED"
    TECHNICIAN_ONSITE = "TECHNICIAN_ONSITE"
    TICKET_RESOLVED = "TICKET_RESOLVED"
    COMPLAINT_RESOLVED = "COMPLAINT_RESOLVED"
    COMPLAINT_CLOSED = "COMPLAINT_CLOSED"
    SLA_BREACH_WARNING = "SLA_BREACH_WARNING"


DEFAULT_TEMPLATES = {
    NotificationEvent.INVOICE_GENERATED: {
        "subject": "New Invoice Generated - {{invoice_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Your invoice {{invoice_number}} for {{billing_month}} has been generated.\n"
            "Amount Due: PKR {{total_amount}}\n"
            "Due Date: {{due_date}}\n"
            "Service: {{service_number}} ({{package_name}})\n\n"
            "Thank you for choosing {{organization_name}}."
        ),
    },
    NotificationEvent.BILL_DUE_REMINDER: {
        "subject": "Payment Due Reminder - Invoice {{invoice_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "This is a gentle reminder that your bill of PKR {{outstanding_amount}} "
            "for invoice {{invoice_number}} is due on {{due_date}}.\n"
            "Please clear your dues to enjoy uninterrupted broadband service.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.BILL_OVERDUE_REMINDER: {
        "subject": "URGENT: Overdue Bill Notice - {{invoice_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Your broadband bill of PKR {{outstanding_amount}} for service {{service_number}} "
            "is now OVERDUE (Due date was {{due_date}}).\n"
            "Please pay immediately to prevent service disruption.\n\n"
            "{{organization_name}} Support: {{support_phone}}"
        ),
    },
    NotificationEvent.SUSPENSION_WARNING: {
        "subject": "FINAL NOTICE: Impending Service Suspension",
        "body": (
            "Dear {{customer_name}},\n"
            "Your internet service {{service_number}} is scheduled for SUSPENSION on {{suspension_date}} "
            "due to an outstanding balance of PKR {{outstanding_amount}}.\n"
            "Kindly pay today to avoid automatic disconnection and reconnection charges.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.SERVICE_SUSPENDED: {
        "subject": "Notice: Internet Service Suspended",
        "body": (
            "Dear {{customer_name}},\n"
            "Your internet service {{service_number}} has been SUSPENDED due to unpaid dues of PKR {{outstanding_amount}}.\n"
            "Reason: {{reason}}\n"
            "To restore your broadband service immediately, please clear your balance.\n\n"
            "{{organization_name}} - {{support_phone}}"
        ),
    },
    NotificationEvent.PAYMENT_RECEIVED: {
        "subject": "Payment Confirmation - Receipt {{payment_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Thank you! We have received your payment of PKR {{paid_amount}} (Receipt: {{payment_number}}).\n"
            "Service: {{service_number}}\n"
            "Remaining Balance: PKR {{outstanding_amount}}\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.PAYMENT_PARTIAL_RECEIVED: {
        "subject": "Partial Payment Received - Receipt {{payment_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "We received a partial payment of PKR {{paid_amount}} (Receipt: {{payment_number}}).\n"
            "Your remaining account balance is PKR {{outstanding_amount}}.\n"
            "Please pay the remaining amount to maintain full active service.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.SERVICE_RESTORED: {
        "subject": "Internet Service Restored",
        "body": (
            "Dear {{customer_name}},\n"
            "Great news! Your broadband service {{service_number}} ({{package_name}}) has been RESTORED.\n"
            "Thank you for your payment and continued partnership.\n\n"
            "{{organization_name}} Helpline: {{support_phone}}"
        ),
    },
    NotificationEvent.PTP_CREATED: {
        "subject": "Promise to Pay Registered - {{service_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Your Promise-to-Pay for PKR {{promised_amount}} with deadline {{deadline}} has been recorded.\n"
            "Your service will remain protected until {{deadline}}.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.PTP_DEADLINE_APPROACHING: {
        "subject": "Promise to Pay Deadline Approaching",
        "body": (
            "Dear {{customer_name}},\n"
            "Reminder: Your promised payment of PKR {{promised_amount}} is due by {{deadline}}.\n"
            "Please fulfill your promise to avoid automatic service suspension.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.PTP_BREACHED: {
        "subject": "Promise to Pay Expired / Breached",
        "body": (
            "Dear {{customer_name}},\n"
            "Your Promise-to-Pay deadline of {{deadline}} has expired without verified payment.\n"
            "Your account with outstanding PKR {{outstanding_amount}} is now subject to standard suspension rules.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.COMPLAINT_CREATED: {
        "subject": "Support Ticket Created - {{complaint_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Your support ticket {{complaint_number}} has been received.\n"
            "Subject: {{subject}}\n"
            "Category: {{category}} | Priority: {{priority}}\n"
            "Our support team is actively looking into your issue.\n\n"
            "{{organization_name}} Support Helpline: {{support_phone}}"
        ),
    },
    NotificationEvent.TICKET_CREATED: {
        "subject": "Support Ticket Created - {{complaint_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Your support ticket {{complaint_number}} has been received.\n"
            "Subject: {{subject}}\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.COMPLAINT_ASSIGNED: {
        "subject": "Support Ticket Assigned - {{complaint_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Your ticket {{complaint_number}} has been assigned to technician {{technician_name}}.\n"
            "We are working to resolve your connection issue promptly.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.TECHNICIAN_DISPATCHED: {
        "subject": "Field Technician Dispatched - {{complaint_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "A field technician ({{technician_name}}) has been dispatched for work order {{work_order_number}} regarding ticket {{complaint_number}}.\n"
            "Estimated arrival shortly at your registered service address.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.TECHNICIAN_ONSITE: {
        "subject": "Technician Arrived On-Site - {{complaint_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Technician {{technician_name}} is now on-site diagnosing your service issue for ticket {{complaint_number}}.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.COMPLAINT_RESOLVED: {
        "subject": "Support Ticket Resolved - {{complaint_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Your support ticket {{complaint_number}} has been marked RESOLVED.\n"
            "Resolution: {{resolution_summary}}\n"
            "Please test your connection. If your issue persists, reply to this message or contact support.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.TICKET_RESOLVED: {
        "subject": "Support Ticket Resolved - {{complaint_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Your support ticket {{complaint_number}} has been resolved.\n\n"
            "{{organization_name}}"
        ),
    },
    NotificationEvent.COMPLAINT_CLOSED: {
        "subject": "Support Ticket Closed - {{complaint_number}}",
        "body": (
            "Dear {{customer_name}},\n"
            "Your support ticket {{complaint_number}} is now officially CLOSED.\n"
            "Thank you for your feedback and cooperation.\n\n"
            "{{organization_name}}"
        ),
    },
}


def make_json_safe(obj):
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [make_json_safe(v) for v in obj]
    elif isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif hasattr(obj, "hex"):
        return str(obj)
    return obj


def render_template_string(template_str: str, context: dict) -> str:
    """
    Safely substitutes {{variable_name}} tokens with context values.
    Leaves no raw curly braces or uncaught KeyError exceptions.
    """
    if not template_str:
        return ""

    def replace_match(match):
        var_name = match.group(1).strip()
        val = context.get(var_name, "")
        if val is None:
            return ""
        if isinstance(val, Decimal):
            return f"{val:.2f}"
        return str(val)

    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", replace_match, template_str)


def get_or_create_default_template(organization, provider, event_type: str) -> CommunicationTemplate:
    """
    Retrieves an existing template for this event type or auto-provisions a default template.
    """
    template_name = f"Default - {event_type} - {provider.provider_type}"
    template = CommunicationTemplate.objects.filter(
        organization=organization,
        communication_provider=provider,
        name=template_name,
    ).first()

    if template:
        return template

    default_data = DEFAULT_TEMPLATES.get(event_type, {
        "subject": f"Notice: {event_type}",
        "body": f"Notification regarding your account with {organization.name}. Context: {{{{service_number}}}}",
    })

    return CommunicationTemplate.objects.create(
        organization=organization,
        communication_provider=provider,
        name=template_name,
        subject=default_data.get("subject", ""),
        body=default_data.get("body", ""),
        status=CommunicationTemplate.Status.ACTIVE,
    )


@transaction.atomic
def dispatch_notification_event(
    *,
    organization,
    customer: Customer,
    event_type: str,
    context: dict,
    preferred_channel: str | None = None,
) -> dict:
    """
    Dispatches notifications across enabled customer channels for any system event.
    Respects customer preferences (WhatsApp, SMS, Email).
    Uses real configured providers and executes immediate dispatch where available.
    """
    # Enrich context with organization metadata
    enriched_context = {
        "customer_name": customer.full_name,
        "customer_number": customer.customer_number,
        "organization_name": organization.name,
        "support_phone": organization.phone or "Support",
        **context,
    }
    json_safe_payload = make_json_safe(enriched_context)

    # Retrieve customer notification preference
    pref, _ = NotificationPreference.objects.get_or_create(
        organization=organization,
        customer=customer,
        defaults={
            "whatsapp_enabled": True,
            "sms_enabled": True,
            "email_enabled": True,
        },
    )

    channels_to_send = []
    if preferred_channel:
        channels_to_send = [preferred_channel.upper()]
    else:
        if pref.whatsapp_enabled and customer.phone:
            channels_to_send.append(CommunicationProvider.ProviderType.WHATSAPP)
        if pref.sms_enabled and customer.phone:
            channels_to_send.append(CommunicationProvider.ProviderType.SMS)
        if getattr(pref, "email_enabled", True) and customer.email:
            channels_to_send.append(CommunicationProvider.ProviderType.EMAIL)

    results = {
        "event_type": event_type,
        "customer_id": str(customer.id),
        "queued_items": [],
        "errors": [],
    }

    now = timezone.now()

    for channel in channels_to_send:
        # Find active provider for channel
        provider = CommunicationProvider.objects.filter(
            organization=organization,
            provider_type=channel,
            status=CommunicationProvider.Status.ACTIVE,
        ).first()

        recipient = customer.phone if channel in [
            CommunicationProvider.ProviderType.WHATSAPP,
            CommunicationProvider.ProviderType.SMS,
        ] else customer.email

        if not recipient:
            continue

        if not provider:
            # Create a placeholder provider record if none exists so queue item can be tracked
            provider, _ = CommunicationProvider.objects.get_or_create(
                organization=organization,
                provider_type=channel,
                name=f"{organization.name} - {channel} Provider",
                defaults={
                    "status": CommunicationProvider.Status.ACTIVE,
                    "is_connected": False,
                },
            )

        # Get or create template
        template = get_or_create_default_template(organization, provider, event_type)

        # Render subject and body
        rendered_subject = render_template_string(template.subject, enriched_context)
        rendered_body = render_template_string(template.body, enriched_context)

        # Create queue item
        queue_item = CommunicationQueue.objects.create(
            organization=organization,
            customer=customer,
            template=template,
            provider=provider,
            recipient=recipient,
            rendered_subject=rendered_subject,
            rendered_body=rendered_body,
            payload=json_safe_payload,
            status=CommunicationQueue.Status.PENDING,
            scheduled_at=now,
            priority=1 if event_type in [
                NotificationEvent.SERVICE_SUSPENDED,
                NotificationEvent.SERVICE_RESTORED,
            ] else 3,
        )

        # Dispatch immediately
        try:
            dispatch_result = CommunicationDispatcher.process(queue_item)
            results["queued_items"].append({
                "queue_id": str(queue_item.id),
                "channel": channel,
                "recipient": recipient,
                "status": queue_item.status,
                "dispatch_result": dispatch_result,
            })
        except Exception as exc:
            logger.exception("Error dispatching notification queue item %s", queue_item.id)
            results["errors"].append({
                "channel": channel,
                "error": str(exc),
            })

    return results
