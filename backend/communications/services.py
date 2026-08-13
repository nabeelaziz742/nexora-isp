from django.db.models import Count
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

    queue = CommunicationQueue.objects.filter(
        organization=organization,
    )

    logs = CommunicationLog.objects.filter(
        organization=organization,
    )

    providers = CommunicationProvider.objects.filter(
        organization=organization,
    )

    delivered = logs.filter(
        status=CommunicationLog.Status.DELIVERED,
    ).count()

    failed = logs.filter(
        status=CommunicationLog.Status.FAILED,
    ).count()

    total = delivered + failed

    return {
        "messages_today": queue.filter(
            created_at__date=today,
        ).count(),

        "delivered": delivered,

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
            round((delivered / total) * 100, 2)
            if total
            else 0
        ),

        "providers": {
            "whatsapp": providers.filter(
                provider_type=CommunicationProvider.ProviderType.WHATSAPP,
                is_connected=True,
            ).exists(),

            "sms": providers.filter(
                provider_type=CommunicationProvider.ProviderType.SMS,
                is_connected=True,
            ).exists(),

            "email": providers.filter(
                provider_type=CommunicationProvider.ProviderType.EMAIL,
                is_connected=True,
            ).exists(),
        },
    }


def get_templates(organization):
    return CommunicationTemplate.objects.filter(
        organization=organization,
    )


def get_logs(organization):
    return CommunicationLog.objects.filter(
        organization=organization,
    ).select_related(
        "queue",
    )


def get_provider_status(organization):
    return CommunicationProvider.objects.filter(
        organization=organization,
    )


def get_schedules(organization):
    return CommunicationSchedule.objects.filter(
        organization=organization,
    )