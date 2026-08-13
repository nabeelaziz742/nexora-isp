from django.urls import path

from revenue_intelligence.views import (
    CollectionsByPeriodAPIView,
    OutstandingReceivablesAPIView,
    PaymentMethodMixAPIView,
    RevenueOverviewAPIView,
)


app_name = "revenue_intelligence"


urlpatterns = [
    path(
        "overview/",
        RevenueOverviewAPIView.as_view(),
        name="revenue-overview",
    ),
    path(
        "collections-by-period/",
        CollectionsByPeriodAPIView.as_view(),
        name="collections-by-period",
    ),
    path(
        "payment-method-mix/",
        PaymentMethodMixAPIView.as_view(),
        name="payment-method-mix",
    ),
    path(
        "outstanding-receivables/",
        OutstandingReceivablesAPIView.as_view(),
        name="outstanding-receivables",
    ),
]