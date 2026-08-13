from django.urls import path

from notifications.views import (
    NotificationJobDetailAPIView,
    NotificationJobListCreateAPIView,
    NotificationJobMarkFailedAPIView,
    NotificationJobMarkSentAPIView,
    NotificationJobStartProcessingAPIView,
    NotificationSummaryAPIView,
)


app_name = "notifications"


urlpatterns = [
    path(
        "jobs/",
        NotificationJobListCreateAPIView.as_view(),
        name="notification-job-list-create",
    ),
    path(
        "jobs/<uuid:notification_job_id>/",
        NotificationJobDetailAPIView.as_view(),
        name="notification-job-detail",
    ),
    path(
        "jobs/<uuid:notification_job_id>/start-processing/",
        NotificationJobStartProcessingAPIView.as_view(),
        name="notification-job-start-processing",
    ),
    path(
        "jobs/<uuid:notification_job_id>/mark-sent/",
        NotificationJobMarkSentAPIView.as_view(),
        name="notification-job-mark-sent",
    ),
    path(
        "jobs/<uuid:notification_job_id>/mark-failed/",
        NotificationJobMarkFailedAPIView.as_view(),
        name="notification-job-mark-failed",
    ),
    path(
        "summary/",
        NotificationSummaryAPIView.as_view(),
        name="notification-summary",
    ),
]