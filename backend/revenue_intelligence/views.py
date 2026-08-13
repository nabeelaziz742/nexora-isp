from rest_framework.response import Response
from rest_framework.views import APIView

from revenue_intelligence.serializers import (
    CollectionsByPeriodSerializer,
    OutstandingReceivableSerializer,
    PaymentMethodMixSerializer,
    RevenueOverviewSerializer,
)
from revenue_intelligence.services import (
    get_collections_by_period,
    get_outstanding_receivables,
    get_payment_method_mix,
    get_revenue_overview,
)
from tenancy.permissions import (
    HasActiveTenantContext,
    IsOrganizationStaffOrOwner,
)


class RevenueIntelligenceBaseAPIView(APIView):
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationStaffOrOwner,
    ]


class RevenueOverviewAPIView(
    RevenueIntelligenceBaseAPIView
):
    def get(self, request):
        overview = get_revenue_overview(
            organization=request.organization,
        )

        serializer = RevenueOverviewSerializer(overview)

        return Response(serializer.data)


class CollectionsByPeriodAPIView(
    RevenueIntelligenceBaseAPIView
):
    def get(self, request):
        collections = get_collections_by_period(
            organization=request.organization,
        )

        serializer = CollectionsByPeriodSerializer(
            collections,
            many=True,
        )

        return Response(serializer.data)


class PaymentMethodMixAPIView(
    RevenueIntelligenceBaseAPIView
):
    def get(self, request):
        payment_mix = get_payment_method_mix(
            organization=request.organization,
        )

        serializer = PaymentMethodMixSerializer(
            payment_mix,
            many=True,
        )

        return Response(serializer.data)


class OutstandingReceivablesAPIView(
    RevenueIntelligenceBaseAPIView
):
    def get(self, request):
        receivables = get_outstanding_receivables(
            organization=request.organization,
        )

        serializer = OutstandingReceivableSerializer(
            receivables,
            many=True,
        )

        return Response(serializer.data)