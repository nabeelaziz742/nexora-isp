import logging
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.models import Customer, ServiceAccount, ServiceSuspensionLog
from customers.suspension_serializers import (
    ManualRestorationRequestSerializer,
    ManualSuspensionRequestSerializer,
    ServiceSuspensionLogSerializer,
    SuspensionPolicySerializer,
    SuspensionPolicyUpdateSerializer,
)
from customers.suspension_services import (
    evaluate_suspension_eligibility,
    execute_service_restoration,
    execute_service_suspension,
    get_or_create_suspension_policy,
    get_suspension_dashboard_metrics,
    run_automated_suspension_engine,
    update_suspension_policy,
)
from tenancy.models import OrganizationMembership
from tenancy.permissions import HasActiveTenantContext

logger = logging.getLogger(__name__)


class SuspensionDashboardView(APIView):
    permission_classes = [HasActiveTenantContext]

    def get(self, request):
        metrics = get_suspension_dashboard_metrics(request.organization)
        return Response(metrics, status=status.HTTP_200_OK)


class SuspensionEligibilityListView(APIView):
    permission_classes = [HasActiveTenantContext]

    def get(self, request):
        items = evaluate_suspension_eligibility(request.organization)

        # Filters
        search = request.query_params.get("search", "").strip().lower()
        if search:
            items = [
                item for item in items
                if search in item["customer_name"].lower()
                or search in item["service_number"].lower()
                or search in item["customer_phone"].lower()
            ]

        eligible_only = request.query_params.get("eligible_only")
        if eligible_only and eligible_only.lower() in ["true", "1"]:
            items = [item for item in items if item["is_eligible_for_suspension"]]

        warning_only = request.query_params.get("warning_only")
        if warning_only and warning_only.lower() in ["true", "1"]:
            items = [item for item in items if item["is_warning_eligible"]]

        ptp_exempt_only = request.query_params.get("ptp_exempt_only")
        if ptp_exempt_only and ptp_exempt_only.lower() in ["true", "1"]:
            items = [item for item in items if item["is_ptp_exempt"]]

        return Response({
            "count": len(items),
            "results": items,
        }, status=status.HTTP_200_OK)


class SuspensionHistoryListView(APIView):
    permission_classes = [HasActiveTenantContext]

    def get(self, request):
        logs = ServiceSuspensionLog.objects.filter(
            organization=request.organization,
        ).select_related("customer", "service_account", "actor")

        customer_id = request.query_params.get("customer_id")
        if customer_id:
            logs = logs.filter(customer_id=customer_id)

        service_account_id = request.query_params.get("service_account_id")
        if service_account_id:
            logs = logs.filter(service_account_id=service_account_id)

        event_type = request.query_params.get("event_type")
        if event_type:
            logs = logs.filter(event_type=event_type)

        trigger_type = request.query_params.get("trigger_type")
        if trigger_type:
            logs = logs.filter(trigger_type=trigger_type)

        serializer = ServiceSuspensionLogSerializer(logs[:100], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SuspensionPolicyView(APIView):
    permission_classes = [HasActiveTenantContext]

    def get(self, request):
        policy = get_or_create_suspension_policy(request.organization)
        serializer = SuspensionPolicySerializer(policy)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        if request.organization_role not in [
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.STAFF,
        ]:
            raise PermissionDenied("Only administrative staff can modify suspension policy.")

        serializer = SuspensionPolicyUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        policy = update_suspension_policy(
            organization=request.organization,
            data=serializer.validated_data,
            actor=request.user,
        )

        return Response(SuspensionPolicySerializer(policy).data, status=status.HTTP_200_OK)


class AutomatedSuspensionRunView(APIView):
    permission_classes = [HasActiveTenantContext]

    def post(self, request):
        if request.organization_role not in [
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.STAFF,
        ]:
            raise PermissionDenied("Only administrative staff can trigger automated suspension runs.")

        run_result = run_automated_suspension_engine(request.organization)
        return Response(run_result, status=status.HTTP_200_OK)


class ManualServiceSuspendView(APIView):
    permission_classes = [HasActiveTenantContext]

    def post(self, request, pk):
        try:
            service_account = ServiceAccount.objects.select_related(
                "customer", "internet_package"
            ).get(id=pk, organization=request.organization)
        except ServiceAccount.DoesNotExist as exc:
            raise NotFound("Service account not found.") from exc

        serializer = ManualSuspensionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            suspension_log = execute_service_suspension(
                service_account=service_account,
                trigger_type=ServiceSuspensionLog.TriggerType.MANUAL_STAFF,
                reason=serializer.validated_data["reason"],
                actor=request.user,
                force=serializer.validated_data.get("force", False),
            )
        except Exception as exc:
            raise ValidationError(str(exc)) from exc

        return Response(
            ServiceSuspensionLogSerializer(suspension_log).data,
            status=status.HTTP_200_OK,
        )


class ManualServiceRestoreView(APIView):
    permission_classes = [HasActiveTenantContext]

    def post(self, request, pk):
        try:
            service_account = ServiceAccount.objects.select_related(
                "customer", "internet_package"
            ).get(id=pk, organization=request.organization)
        except ServiceAccount.DoesNotExist as exc:
            raise NotFound("Service account not found.") from exc

        serializer = ManualRestorationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            restoration_log = execute_service_restoration(
                service_account=service_account,
                trigger_type=ServiceSuspensionLog.TriggerType.MANUAL_STAFF,
                reason=serializer.validated_data["reason"],
                actor=request.user,
                force=serializer.validated_data.get("force", False),
            )
        except Exception as exc:
            raise ValidationError(str(exc)) from exc

        return Response(
            ServiceSuspensionLogSerializer(restoration_log).data,
            status=status.HTTP_200_OK,
        )
