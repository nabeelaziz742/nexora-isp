from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),
    path(
        "api/v1/auth/",
        include("accounts.api.urls"),
    ),
    path(
        "api/v1/onboarding/",
        include("onboarding.urls"),
    ),
    path(
        "api/v1/tenant/",
        include("tenancy.urls"),
    ),
    path(
        "api/v1/customers/",
        include("customers.urls"),
    ),
    path(
        "api/v1/network/",
        include("network.urls"),
    ),
    path(
        "api/v1/inventory/",
        include("inventory.urls"),
    ),
    path(
        "api/v1/pos/",
        include("inventory.pos_urls"),
    ),
    path(
        "api/v1/billing/",
        include("billing.urls"),
    ),
    path(
        "api/v1/accounting/",
        include("accounting.urls"),
    ),
    path(
        "api/v1/support/",
        include("support.urls"),
    ),
    path(
        "api/v1/field-operations/",
        include("field_operations.urls"),
    ),
    path(
        "api/v1/notifications/",
        include("notifications.urls"),
    ),
    path(
        "api/v1/command-center/",
        include("command_center.urls"),
    ),
    path(
        "api/v1/revenue-intelligence/",
        include("revenue_intelligence.urls"),
    ),
    path(
        "api/v1/reports/",
        include("reports.urls"),
    ),
    path(
        "api/v1/communications/",
        include("communications.urls"),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
