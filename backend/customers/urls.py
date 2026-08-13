from django.urls import path

from customers.views import (
    CustomerActivationView,
    CustomerDetailView,
    CustomerListView,
    InternetPackageListView,
)


urlpatterns = [
    path(
        "",
        CustomerListView.as_view(),
        name="customer-list",
    ),
    path(
        "activate/",
        CustomerActivationView.as_view(),
        name="customer-activate",
    ),
    path(
        "packages/",
        InternetPackageListView.as_view(),
        name="internet-package-list",
    ),
    path(
        "<uuid:customer_id>/",
        CustomerDetailView.as_view(),
        name="customer-detail",
    ),
]