"""Super admin APIs for the platform: dashboard, ISPs, subscriptions."""
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from onboarding.models import ISPSubscriptionPayment
from onboarding.platform_services import (
    MAX_SUBSCRIPTION_MONTHS,
    activate_isp,
    get_isp_detail,
    get_platform_dashboard,
    list_isps,
    record_subscription_payment,
    suspend_isp,
    update_subscription,
)
from onboarding.views import IsSuperAdmin


class SuperAdminAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]


class SuspendISPSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class SubscriptionUpdateSerializer(serializers.Serializer):
    monthly_fee = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    paid_until = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class SubscriptionPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    months = serializers.IntegerField(min_value=1, max_value=MAX_SUBSCRIPTION_MONTHS)
    method = serializers.ChoiceField(choices=ISPSubscriptionPayment.Method.choices)
    reference = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class PlatformDashboardAPIView(SuperAdminAPIView):
    def get(self, request):
        return Response(get_platform_dashboard())


class ISPListAPIView(SuperAdminAPIView):
    def get(self, request):
        items = list_isps(
            search=request.query_params.get("search", "").strip(),
            status=request.query_params.get("status", "").strip().upper(),
            subscription_filter=request.query_params.get("subscription", "").strip().lower(),
        )
        return Response({"count": len(items), "results": items})


class ISPDetailAPIView(SuperAdminAPIView):
    def get(self, request, organization_id):
        return Response(get_isp_detail(organization_id))


class ISPSuspendAPIView(SuperAdminAPIView):
    def post(self, request, organization_id):
        serializer = SuspendISPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suspend_isp(organization_id=organization_id, actor=request.user, reason=serializer.validated_data["reason"])
        return Response(get_isp_detail(organization_id))


class ISPActivateAPIView(SuperAdminAPIView):
    def post(self, request, organization_id):
        activate_isp(organization_id=organization_id)
        return Response(get_isp_detail(organization_id))


class ISPSubscriptionAPIView(SuperAdminAPIView):
    def put(self, request, organization_id):
        serializer = SubscriptionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        update_subscription(
            organization_id=organization_id,
            monthly_fee=data.get("monthly_fee"),
            paid_until=data.get("paid_until"),
            notes=data.get("notes"),
            clear_paid_until="paid_until" in data and data["paid_until"] is None,
        )
        return Response(get_isp_detail(organization_id))


class ISPSubscriptionPaymentAPIView(SuperAdminAPIView):
    def post(self, request, organization_id):
        serializer = SubscriptionPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record_subscription_payment(organization_id=organization_id, actor=request.user, **serializer.validated_data)
        return Response(get_isp_detail(organization_id), status=status.HTTP_201_CREATED)
