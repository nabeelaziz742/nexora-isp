from django.urls import path

from field_operations.views import (
    WorkOrderAssignmentAPIView,
    WorkOrderCompletionAPIView,
    WorkOrderDetailAPIView,
    WorkOrderDispatchAPIView,
    WorkOrderListCreateAPIView,
    WorkOrderOnsiteAPIView,
)


urlpatterns = [
    path(
        "work-orders/",
        WorkOrderListCreateAPIView.as_view(),
        name="work-order-list-create",
    ),
    path(
        "work-orders/<uuid:work_order_id>/",
        WorkOrderDetailAPIView.as_view(),
        name="work-order-detail",
    ),
    path(
        "work-orders/<uuid:work_order_id>/assignments/",
        WorkOrderAssignmentAPIView.as_view(),
        name="work-order-assignment",
    ),
    path(
        "work-orders/<uuid:work_order_id>/dispatches/",
        WorkOrderDispatchAPIView.as_view(),
        name="work-order-dispatch",
    ),
    path(
        (
            "work-orders/<uuid:work_order_id>/"
            "onsite-transitions/"
        ),
        WorkOrderOnsiteAPIView.as_view(),
        name="work-order-onsite-transition",
    ),
    path(
        "work-orders/<uuid:work_order_id>/completions/",
        WorkOrderCompletionAPIView.as_view(),
        name="work-order-completion",
    ),
]