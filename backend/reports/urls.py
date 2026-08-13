from django.urls import path

from reports.views import (
    PackageContributionAPIView,
    PackageRevenueContextAPIView,
    ServiceStatusDistributionAPIView,
    SubscriberOverviewAPIView,
)


app_name = "reports"


urlpatterns = [
    path(
        "subscriber-overview/",
        SubscriberOverviewAPIView.as_view(),
        name="subscriber-overview",
    ),
    path(
        "service-status-distribution/",
        ServiceStatusDistributionAPIView.as_view(),
        name="service-status-distribution",
    ),
    path(
        "package-contribution/",
        PackageContributionAPIView.as_view(),
        name="package-contribution",
    ),
    path(
        "package-revenue-context/",
        PackageRevenueContextAPIView.as_view(),
        name="package-revenue-context",
    ),
]