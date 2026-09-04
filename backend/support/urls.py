from django.urls import path

from support.views import (
    ComplaintAssignAPIView,
    ComplaintCloseAPIView,
    ComplaintDetailAPIView,
    ComplaintEscalateAPIView,
    ComplaintInternalNoteAPIView,
    ComplaintListCreateAPIView,
    ComplaintReassignAPIView,
    ComplaintResolveAPIView,
    ComplaintSLAPolicyListUpdateAPIView,
    ComplaintStatusTransitionAPIView,
    ComplaintTimelineAPIView,
    IncidentDetailAPIView,
    IncidentListCreateAPIView,
    IncidentStatusTransitionAPIView,
    SupportDashboardMetricsAPIView,
)

urlpatterns = [
    # Complaint Endpoints
    path(
        "complaints/",
        ComplaintListCreateAPIView.as_view(),
        name="support-complaint-list-create",
    ),
    path(
        "complaints/<uuid:complaint_id>/",
        ComplaintDetailAPIView.as_view(),
        name="support-complaint-detail",
    ),
    path(
        "complaints/<uuid:complaint_id>/assign/",
        ComplaintAssignAPIView.as_view(),
        name="support-complaint-assign",
    ),
    path(
        "complaints/<uuid:complaint_id>/reassign/",
        ComplaintReassignAPIView.as_view(),
        name="support-complaint-reassign",
    ),
    path(
        "complaints/<uuid:complaint_id>/status-transitions/",
        ComplaintStatusTransitionAPIView.as_view(),
        name="support-complaint-status-transition-legacy",
    ),
    path(
        "complaints/<uuid:complaint_id>/transition/",
        ComplaintStatusTransitionAPIView.as_view(),
        name="support-complaint-transition",
    ),
    path(
        "complaints/<uuid:complaint_id>/escalate/",
        ComplaintEscalateAPIView.as_view(),
        name="support-complaint-escalate",
    ),
    path(
        "complaints/<uuid:complaint_id>/notes/",
        ComplaintInternalNoteAPIView.as_view(),
        name="support-complaint-notes",
    ),
    path(
        "complaints/<uuid:complaint_id>/resolve/",
        ComplaintResolveAPIView.as_view(),
        name="support-complaint-resolve",
    ),
    path(
        "complaints/<uuid:complaint_id>/close/",
        ComplaintCloseAPIView.as_view(),
        name="support-complaint-close",
    ),
    path(
        "complaints/<uuid:complaint_id>/timeline/",
        ComplaintTimelineAPIView.as_view(),
        name="support-complaint-timeline",
    ),

    # Dashboard & SLA Policies
    path(
        "dashboard/metrics/",
        SupportDashboardMetricsAPIView.as_view(),
        name="support-dashboard-metrics",
    ),
    path(
        "sla-policies/",
        ComplaintSLAPolicyListUpdateAPIView.as_view(),
        name="support-sla-policies",
    ),

    # Incident Endpoints (Preserved)
    path(
        "incidents/",
        IncidentListCreateAPIView.as_view(),
        name="support-incident-list-create",
    ),
    path(
        "incidents/<uuid:incident_id>/",
        IncidentDetailAPIView.as_view(),
        name="support-incident-detail",
    ),
    path(
        "incidents/<uuid:incident_id>/status-transitions/",
        IncidentStatusTransitionAPIView.as_view(),
        name="support-incident-status-transition",
    ),
]