from django.urls import path

from network.views import (
    NetworkAssignmentListView,
    NetworkNodeDetailView,
    NetworkNodeListView,
    ProvisioningRequestListView,
    ServicePackageChangeRequestView,
    ServiceRestoreRequestView,
    ServiceSuspensionRequestView,
)


urlpatterns = [
    path(
        "nodes/",
        NetworkNodeListView.as_view(),
        name="network-node-list",
    ),
    path(
        "nodes/<uuid:node_id>/",
        NetworkNodeDetailView.as_view(),
        name="network-node-detail",
    ),
    path(
        "assignments/",
        NetworkAssignmentListView.as_view(),
        name="network-assignment-list",
    ),
    path(
        "provisioning-requests/",
        ProvisioningRequestListView.as_view(),
        name="provisioning-request-list",
    ),
    path(
        (
            "services/<uuid:service_account_id>/"
            "suspension-requests/"
        ),
        ServiceSuspensionRequestView.as_view(),
        name="service-suspension-request",
    ),
    path(
        (
            "services/<uuid:service_account_id>/"
            "restore-requests/"
        ),
        ServiceRestoreRequestView.as_view(),
        name="service-restore-request",
    ),
    path(
        (
            "services/<uuid:service_account_id>/"
            "package-change-requests/"
        ),
        ServicePackageChangeRequestView.as_view(),
        name="service-package-change-request",
    ),
]