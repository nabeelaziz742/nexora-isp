from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from command_center.copilot import (
    CopilotDomainError,
    CopilotProviderError,
    ask_operations_copilot,
)
from command_center.serializers import (
    CommandCenterSummarySerializer,
    OperationalActivitySerializer,
    OperationalAlertSerializer,
    OperationsCopilotRequestSerializer,
    OperationsCopilotResponseSerializer,
    PriorityQueuesSerializer,
)
from command_center.services import (
    get_command_center_summary,
    get_operational_alerts,
    get_priority_queues,
    get_recent_operational_activity,
)
from command_center.throttles import CopilotRateThrottle
from tenancy.permissions import (
    HasActiveTenantContext,
    IsOrganizationStaffOrOwner,
)


class CommandCenterBaseAPIView(APIView):
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationStaffOrOwner,
    ]


class CommandCenterSummaryAPIView(CommandCenterBaseAPIView):
    def get(self, request):
        summary = get_command_center_summary(
            organization=request.organization,
        )
        serializer = CommandCenterSummarySerializer(summary)
        return Response(serializer.data)


class CommandCenterOperationalAlertsAPIView(
    CommandCenterBaseAPIView
):
    def get(self, request):
        alerts = get_operational_alerts(
            organization=request.organization,
        )
        serializer = OperationalAlertSerializer(
            alerts,
            many=True,
        )
        return Response(serializer.data)


class CommandCenterPriorityQueuesAPIView(
    CommandCenterBaseAPIView
):
    def get(self, request):
        queues = get_priority_queues(
            organization=request.organization,
        )
        serializer = PriorityQueuesSerializer(queues)
        return Response(serializer.data)


class CommandCenterRecentActivityAPIView(
    CommandCenterBaseAPIView
):
    def get(self, request):
        activity = get_recent_operational_activity(
            organization=request.organization,
        )
        serializer = OperationalActivitySerializer(
            activity,
            many=True,
        )
        return Response(serializer.data)


class OperationsCopilotAPIView(CommandCenterBaseAPIView):
    throttle_classes = [CopilotRateThrottle]
    throttle_scope = "copilot"

    def post(self, request):
        request_serializer = OperationsCopilotRequestSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        try:
            result = ask_operations_copilot(
                organization=request.organization,
                question=request_serializer.validated_data[
                    "question"
                ],
            )
        except CopilotDomainError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except CopilotProviderError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_serializer = OperationsCopilotResponseSerializer(
            result
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )
