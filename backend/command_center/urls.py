from django.urls import path

from command_center.views import (
    CommandCenterOperationalAlertsAPIView,
    CommandCenterPriorityQueuesAPIView,
    CommandCenterRecentActivityAPIView,
    CommandCenterSummaryAPIView,
    OperationsCopilotAPIView,
)


app_name = "command_center"


urlpatterns = [
    path(
        "summary/",
        CommandCenterSummaryAPIView.as_view(),
        name="command-center-summary",
    ),
    path(
        "alerts/",
        CommandCenterOperationalAlertsAPIView.as_view(),
        name="command-center-alerts",
    ),
    path(
        "priority-queues/",
        CommandCenterPriorityQueuesAPIView.as_view(),
        name="command-center-priority-queues",
    ),
    path(
        "recent-activity/",
        CommandCenterRecentActivityAPIView.as_view(),
        name="command-center-recent-activity",
    ),
    path(
        "copilot/ask/",
        OperationsCopilotAPIView.as_view(),
        name="operations-copilot-ask",
    ),
]
