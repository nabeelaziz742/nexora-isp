from django.urls import path

from field_operations.maintenance_views import (
    MaintenanceCompletionAPIView,
    MaintenanceRestoreAPIView,
    MaintenanceScheduleAPIView,
    MaintenanceStartAPIView,
)
from field_operations.views import (
    WorkOrderAssignmentAPIView,
    WorkOrderCompletionAPIView,
    WorkOrderDetailAPIView,
    WorkOrderDispatchAPIView,
    WorkOrderListCreateAPIView,
    WorkOrderOnsiteAPIView,
)


urlpatterns = [
    path("work-orders/", WorkOrderListCreateAPIView.as_view(), name="work-order-list-create"),
    path("work-orders/<uuid:work_order_id>/", WorkOrderDetailAPIView.as_view(), name="work-order-detail"),
    path("work-orders/<uuid:work_order_id>/assignments/", WorkOrderAssignmentAPIView.as_view(), name="work-order-assignment"),
    path("work-orders/<uuid:work_order_id>/dispatches/", WorkOrderDispatchAPIView.as_view(), name="work-order-dispatch"),
    path("work-orders/<uuid:work_order_id>/onsite-transitions/", WorkOrderOnsiteAPIView.as_view(), name="work-order-onsite-transition"),
    path("work-orders/<uuid:work_order_id>/completions/", WorkOrderCompletionAPIView.as_view(), name="work-order-completion"),
    path("work-orders/<uuid:work_order_id>/maintenance/schedule/", MaintenanceScheduleAPIView.as_view(), name="maintenance-schedule"),
    path("work-orders/<uuid:work_order_id>/maintenance/start/", MaintenanceStartAPIView.as_view(), name="maintenance-start"),
    path("work-orders/<uuid:work_order_id>/maintenance/complete/", MaintenanceCompletionAPIView.as_view(), name="maintenance-complete"),
    path("work-orders/<uuid:work_order_id>/maintenance/restore/", MaintenanceRestoreAPIView.as_view(), name="maintenance-restore"),
]
