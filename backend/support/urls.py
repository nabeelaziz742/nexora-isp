from django.urls import path

from support.views import (
    ComplaintDetailAPIView,
    ComplaintListCreateAPIView,
    ComplaintStatusTransitionAPIView,
    IncidentDetailAPIView,
    IncidentListCreateAPIView,
    IncidentStatusTransitionAPIView,
)


urlpatterns = [
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
        (
            "complaints/<uuid:complaint_id>/"
            "status-transitions/"
        ),
        ComplaintStatusTransitionAPIView.as_view(),
        name="support-complaint-status-transition",
    ),
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
        (
            "incidents/<uuid:incident_id>/"
            "status-transitions/"
        ),
        IncidentStatusTransitionAPIView.as_view(),
        name="support-incident-status-transition",
    ),
]