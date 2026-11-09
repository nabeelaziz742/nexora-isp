"""Super admin APIs for the platform: dashboard, ISPs, subscriptions."""
from django.http import Http404, HttpResponse
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.api.password_views import ChangePasswordSerializer, check_new_password
from onboarding.models import ISPSubscriptionPayment
from onboarding.platform_services import (
    MAX_SUBSCRIPTION_MONTHS,
    activate_isp,
    get_isp_detail,
    get_platform_dashboard,
    list_isps,
    record_subscription_payment,
    reset_owner_password,
    subscription_status_for_owner,
    suspend_isp,
    update_subscription,
)
from onboarding.receipts import build_receipt_pdf, receipt_filename
from onboarding.views import IsSuperAdmin
from tenancy.models import Organization
from tenancy.permissions import IsOrganizationOwner
from tenancy.services import record_audit_log


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


class ISPOwnerPasswordResetAPIView(SuperAdminAPIView):
    """Fallback when the owner cannot get the reset email: returns a one-time temporary password."""

    def post(self, request, organization_id):
        email, password = reset_owner_password(organization_id=organization_id)
        detail = get_isp_detail(organization_id)
        record_audit_log(
            organization=Organization.objects.get(id=organization_id),
            actor=request.user,
            action="OWNER_PASSWORD_RESET_BY_PLATFORM",
            resource_type="User",
            resource_id=email,
            metadata={"email": email},
        )
        return Response({"email": email, "temporary_password": password, "organization_code": detail["code"]})


class SuperAdminChangePasswordAPIView(SuperAdminAPIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            raise serializers.ValidationError({"current_password": ["Current password is incorrect."]})
        check_new_password(serializer.validated_data["new_password"], user)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password changed."})


class OwnerSubscriptionStatusAPIView(APIView):
    """The signed-in ISP owner's own Nexora subscription (for the renewal banner)."""

    permission_classes = [IsOrganizationOwner]

    def get(self, request):
        return Response(subscription_status_for_owner(request.organization))


def _receipt_response(payment: ISPSubscriptionPayment) -> HttpResponse:
    response = HttpResponse(build_receipt_pdf(payment), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{receipt_filename(payment)}"'
    response["Cache-Control"] = "no-store"
    return response


class SubscriptionReceiptAPIView(SuperAdminAPIView):
    def get(self, request, payment_id):
        payment = ISPSubscriptionPayment.objects.select_related("organization", "recorded_by").filter(id=payment_id).first()
        if payment is None:
            raise Http404
        return _receipt_response(payment)


class OwnerSubscriptionReceiptAPIView(APIView):
    """The ISP owner downloads a receipt for one of their own subscription payments."""

    permission_classes = [IsOrganizationOwner]

    def get(self, request, payment_id):
        payment = (
            ISPSubscriptionPayment.objects.select_related("organization", "recorded_by")
            .filter(id=payment_id, organization=request.organization)
            .first()
        )
        if payment is None:
            raise Http404
        return _receipt_response(payment)
