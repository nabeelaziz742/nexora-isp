from rest_framework.response import Response
from rest_framework.views import APIView

from reports.serializers import (
    PackageContributionSerializer,
    PackageRevenueContextSerializer,
    ServiceStatusDistributionSerializer,
    SubscriberOverviewSerializer,
)
from reports.services import (
    get_package_contribution,
    get_package_revenue_context,
    get_service_status_distribution,
    get_subscriber_overview,
)
from tenancy.permissions import (
    HasActiveTenantContext,
    IsOrganizationStaffOrOwner,
)


class ReportsBaseAPIView(APIView):
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationStaffOrOwner,
    ]


class SubscriberOverviewAPIView(ReportsBaseAPIView):
    def get(self, request):
        overview = get_subscriber_overview(
            organization=request.organization,
        )

        serializer = SubscriberOverviewSerializer(
            overview
        )

        return Response(serializer.data)


class ServiceStatusDistributionAPIView(
    ReportsBaseAPIView
):
    def get(self, request):
        distribution = get_service_status_distribution(
            organization=request.organization,
        )

        serializer = ServiceStatusDistributionSerializer(
            distribution,
            many=True,
        )

        return Response(serializer.data)


class PackageContributionAPIView(ReportsBaseAPIView):
    def get(self, request):
        contribution = get_package_contribution(
            organization=request.organization,
        )

        serializer = PackageContributionSerializer(
            contribution,
            many=True,
        )

        return Response(serializer.data)


class PackageRevenueContextAPIView(ReportsBaseAPIView):
    def get(self, request):
        revenue_context = get_package_revenue_context(
            organization=request.organization,
        )

        serializer = PackageRevenueContextSerializer(
            revenue_context,
            many=True,
        )

        return Response(serializer.data)