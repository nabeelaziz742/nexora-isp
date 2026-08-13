from django.contrib import admin

from .models import (
    NetworkAssignment,
    NetworkNode,
    ProvisioningRequest,
)


@admin.register(NetworkNode)
class NetworkNodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "organization",
        "node_type",
        "management_ip",
        "is_active",
    )
    list_filter = (
        "node_type",
        "is_active",
        "organization",
    )
    search_fields = (
        "code",
        "name",
        "management_ip",
    )


@admin.register(NetworkAssignment)
class NetworkAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "service_account",
        "network_node",
        "organization",
        "username",
        "ip_address",
        "is_active",
        "assigned_at",
    )
    list_filter = (
        "is_active",
        "organization",
    )
    search_fields = (
        "service_account__service_number",
        "network_node__code",
        "username",
        "ip_address",
    )


@admin.register(ProvisioningRequest)
class ProvisioningRequestAdmin(admin.ModelAdmin):
    list_display = (
        "service_account",
        "action",
        "status",
        "organization",
        "requested_at",
        "completed_at",
    )
    list_filter = (
        "action",
        "status",
        "organization",
    )
    search_fields = (
        "service_account__service_number",
        "provider_reference",
    )
    readonly_fields = (
        "idempotency_key",
        "requested_at",
        "updated_at",
    )