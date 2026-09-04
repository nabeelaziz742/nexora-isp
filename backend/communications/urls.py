from rest_framework.routers import DefaultRouter
from .dashboard import CommunicationDashboardAPIView
from .views import (
    CustomerCommunicationHistoryView,
    WhatsAppWebhookAPIView,
)

from django.urls import path
from .views import (
    BroadcastAPIView,
    RetryCommunicationAPIView,
    broadcast_options,
)

from .views import (
    CommunicationAutomationViewSet,
    CommunicationLogViewSet,
    CommunicationProviderViewSet,
    CommunicationQueueViewSet,
    CommunicationScheduleViewSet,
    CommunicationTemplateViewSet,
)

router = DefaultRouter()

router.register(
    "providers",
    CommunicationProviderViewSet,
)

router.register(
    "templates",
    CommunicationTemplateViewSet,
)

router.register(
    "automations",
    CommunicationAutomationViewSet,
)

router.register(
    "schedules",
    CommunicationScheduleViewSet,
)

router.register(
    "queue",
    CommunicationQueueViewSet,
)

router.register(
    "logs",
    CommunicationLogViewSet,
)

urlpatterns = [
    path(
        "dashboard/",
        CommunicationDashboardAPIView.as_view(),
        name="communication-dashboard",
    ),

    path(
    "broadcast/",
    BroadcastAPIView.as_view(),
    name="broadcast",
    ),

    path(
    "broadcast/options/",
    broadcast_options,
    name="broadcast-options",
    ),

    path(
    "logs/<uuid:pk>/retry/",
    RetryCommunicationAPIView.as_view(),
    name="communication-log-retry",
    ),

    path(
        "customer/<uuid:customer_id>/history/",
        CustomerCommunicationHistoryView.as_view(),
        name="customer-communication-history",
    ),

    path(
        "webhook/whatsapp/",
        WhatsAppWebhookAPIView.as_view(),
        name="whatsapp-webhook",
    ),
]


urlpatterns += router.urls