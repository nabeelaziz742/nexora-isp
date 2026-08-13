from django.urls import path

from inventory.views import (
    AssignDeviceView,
    DeviceAssignmentListView,
    InventoryDeviceDetailView,
    InventoryDeviceListView,
    ReturnDeviceView,
)


urlpatterns = [
    path(
        "devices/",
        InventoryDeviceListView.as_view(),
        name="inventory-device-list",
    ),
    path(
        "devices/<uuid:device_id>/",
        InventoryDeviceDetailView.as_view(),
        name="inventory-device-detail",
    ),
    path(
        "assignments/",
        DeviceAssignmentListView.as_view(),
        name="device-assignment-list",
    ),
    path(
        "assignments/assign/",
        AssignDeviceView.as_view(),
        name="device-assignment-assign",
    ),
    path(
        "assignments/<uuid:assignment_id>/return/",
        ReturnDeviceView.as_view(),
        name="device-assignment-return",
    ),
]