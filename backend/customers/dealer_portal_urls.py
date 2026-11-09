from django.urls import path

from customers.dealer_portal import (
    DealerCollectionsView,
    DealerCollectPaymentView,
    DealerCustomerListView,
    DealerRechargeView,
    DealerSummaryView,
)

urlpatterns = [
    path("summary/", DealerSummaryView.as_view(), name="dealer-portal-summary"),
    path("customers/", DealerCustomerListView.as_view(), name="dealer-portal-customers"),
    path("services/<uuid:service_id>/payments/", DealerCollectPaymentView.as_view(), name="dealer-portal-payment"),
    path("services/<uuid:service_id>/recharge/", DealerRechargeView.as_view(), name="dealer-portal-recharge"),
    path("collections/", DealerCollectionsView.as_view(), name="dealer-portal-collections"),
]
