from django.utils import timezone

from .models import (
    CommunicationAutomation,
    CommunicationLog,
    CommunicationProvider,
    CommunicationQueue,
    CommunicationSchedule,
    CommunicationTemplate,
)


def get_communication_dashboard_summary(organization):
    today = timezone.now().date()

    queue = CommunicationQueue.objects.filter(organization=organization)
    logs = CommunicationLog.objects.filter(organization=organization)
    providers = CommunicationProvider.objects.filter(organization=organization)

    delivered = logs.filter(
        status__in=[
            CommunicationLog.Status.DELIVERED,
            CommunicationLog.Status.READ,
        ],
    ).count()

    accepted = logs.filter(
        status__in=[
            CommunicationLog.Status.SENT,
            CommunicationLog.Status.DELIVERED,
            CommunicationLog.Status.READ,
        ],
    ).count()

    failed = logs.filter(status=CommunicationLog.Status.FAILED).count()
    completed = accepted + failed

    return {
        "messages_today": queue.filter(created_at__date=today).count(),
        "delivered": delivered,
        "accepted": accepted,
        "failed": failed,
        "pending": queue.filter(
            status=CommunicationQueue.Status.PENDING,
        ).count(),
        "scheduled_jobs": CommunicationSchedule.objects.filter(
            organization=organization,
            is_enabled=True,
        ).count(),
        "templates": CommunicationTemplate.objects.filter(
            organization=organization,
        ).count(),
        "success_rate": (
            round((accepted / completed) * 100, 2)
            if completed
            else 0
        ),
        "providers": {
            "whatsapp": providers.filter(
                provider_type=CommunicationProvider.ProviderType.WHATSAPP,
                status=CommunicationProvider.Status.ACTIVE,
                is_connected=True,
            ).exists(),
            "sms": providers.filter(
                provider_type=CommunicationProvider.ProviderType.SMS,
                status=CommunicationProvider.Status.ACTIVE,
                is_connected=True,
            ).exists(),
            "email": providers.filter(
                provider_type=CommunicationProvider.ProviderType.EMAIL,
                status=CommunicationProvider.Status.ACTIVE,
                is_connected=True,
            ).exists(),
        },
    }


def get_templates(organization):
    return CommunicationTemplate.objects.filter(organization=organization)


def get_logs(organization):
    return CommunicationLog.objects.filter(
        organization=organization,
    ).select_related("queue")


def get_provider_status(organization):
    return CommunicationProvider.objects.filter(organization=organization)


def get_schedules(organization):
    return CommunicationSchedule.objects.filter(organization=organization)
