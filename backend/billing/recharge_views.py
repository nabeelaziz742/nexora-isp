from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.recharge_serializers import (
    BillingModeSerializer,
    RechargeResultSerializer,
    ServiceRechargeSerializer,
)
from billing.recharge_services import (
    change_billing_mode,
    get_expiring_services,
    recharge_service,
)
from billing.services import BillingDomainError
from tenancy.permissions import CanManageBilling


class ServiceRechargeView(APIView):
    permission_classes = [CanManageBilling]

    def post(self, request, service_account_id):
        serializer = ServiceRechargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = recharge_service(
                organization=request.organization,
                actor=request.user,
                service_account_id=service_account_id,
                months=data["months"],
                payment_method=data["payment_method"],
                reference=data.get("reference", ""),
                notes=data.get("notes", ""),
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(RechargeResultSerializer(result).data, status=status.HTTP_201_CREATED)


class ServiceBillingModeView(APIView):
    permission_classes = [CanManageBilling]

    def put(self, request, service_account_id):
        serializer = BillingModeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            service_account = change_billing_mode(
                organization=request.organization,
                actor=request.user,
                service_account_id=service_account_id,
                billing_cycle=data["billing_cycle"],
                expiry_date=data.get("expiry_date"),
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "service_account_id": str(service_account.id),
            "billing_cycle": data["billing_cycle"],
            "expiry_date": service_account.expiry_date,
        })


class ExpiringServicesView(APIView):
    permission_classes = [CanManageBilling]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 3))
        except ValueError:
            days = 3
        days = max(0, min(days, 30))

        results = get_expiring_services(organization=request.organization, days=days)
        return Response({"days": days, "count": len(results), "results": results})
