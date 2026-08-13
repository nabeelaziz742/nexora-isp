from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.permissions import (
    HasActiveTenantContext,
    IsOrganizationStaffOrOwner,
)

from .services import get_communication_dashboard_summary


class CommunicationDashboardAPIView(APIView):
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationStaffOrOwner,
    ]

    def get(self, request):
        summary = get_communication_dashboard_summary(
            organization=request.organization,
        )

        return Response(summary)