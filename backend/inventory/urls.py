from django.urls import path

from inventory.views import (
    AssignDeviceView,
    DeviceAssignmentListView,
    InventoryDeviceDetailView,
    InventoryDeviceListView,
    InventoryItemAdjustmentView,
    InventoryItemDamageView,
    InventoryItemDetailView,
    InventoryItemDisposeView,
    InventoryItemListView,
    InventoryItemRestockView,
    ReturnDeviceView,
    StockMovementListView,
)


urlpatterns = [
    # Serialized CPE Devices
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

    # Quantity-based Inventory Items
    path(
        "items/",
        InventoryItemListView.as_view(),
        name="inventory-item-list",
    ),
    path(
        "items/<uuid:item_id>/",
        InventoryItemDetailView.as_view(),
        name="inventory-item-detail",
    ),
    path(
        "items/<uuid:item_id>/restock/",
        InventoryItemRestockView.as_view(),
        name="inventory-item-restock",
    ),
    path(
        "items/<uuid:item_id>/adjust/",
        InventoryItemAdjustmentView.as_view(),
        name="inventory-item-adjust",
    ),
    path(
        "items/<uuid:item_id>/damage/",
        InventoryItemDamageView.as_view(),
        name="inventory-item-damage",
    ),
    path(
        "items/<uuid:item_id>/dispose/",
        InventoryItemDisposeView.as_view(),
        name="inventory-item-dispose",
    ),

    # Stock Movement Ledger
    path(
        "movements/",
        StockMovementListView.as_view(),
        name="inventory-movement-list",
    ),
]