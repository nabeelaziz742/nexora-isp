from django.contrib import admin

from .models import (
    CommunicationAutomation,
    CommunicationLog,
    CommunicationProvider,
    CommunicationQueue,
    CommunicationSchedule,
    CommunicationTemplate,
)


@admin.register(CommunicationProvider)
class CommunicationProviderAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "provider_type",
        "status",
        "is_default",
        "organization",
    )
    list_filter = (
        "provider_type",
        "status",
        "organization",
    )
    search_fields = (
        "name",
        "business_id",
    )


@admin.register(CommunicationTemplate)
class CommunicationTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "communication_provider",
        "status",
        "organization",
    )
    list_filter = (
        "status",
        "communication_provider",
    )
    search_fields = (
        "name",
        "subject",
    )


@admin.register(CommunicationAutomation)
class CommunicationAutomationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "trigger",
        "template",
        "is_enabled",
        "organization",
    )
    list_filter = (
        "trigger",
        "is_enabled",
    )
    search_fields = (
        "name",
    )


@admin.register(CommunicationSchedule)
class CommunicationScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "automation",
        "frequency",
        "next_run",
        "is_enabled",
    )
    list_filter = (
        "frequency",
        "is_enabled",
    )


@admin.register(CommunicationQueue)
class CommunicationQueueAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "template",
        "status",
        "scheduled_at",
        "sent_at",
    )
    list_filter = (
        "status",
    )
    search_fields = (
        "customer__customer_number",
        "customer__first_name",
        "customer__phone",
    )


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = (
        "queue",
        "status",
        "recipient",
        "delivered_at",
        "created_at",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "recipient",
        "provider_response",
        "provider_response_code",
    )