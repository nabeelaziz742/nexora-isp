from django.db.models import Count, Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from network.models import (
    NetworkAssignment,
    NetworkNode,
    ProvisioningRequest,
)
from network.serializers import (
    NetworkAssignmentSerializer,
    NetworkNodeSerializer,
    ProvisioningRequestSerializer,
    RequestPackageChangeSerializer,
)
from network.services import (
    ServiceLifecycleError,
    request_package_change,
    request_service_restore,
    request_service_suspension,
)
from tenancy.permissions import IsOrganizationStaffOrOwner


def apply_customer_service_search(queryset, search):
    search_terms = [
        term
        for term in search.split()
        if term.strip()
    ]

    for term in search_terms:
        queryset = queryset.filter(
            Q(
                service_account__service_number__icontains=term
            )
            | Q(
                service_account__customer__customer_number__icontains=term
            )
            | Q(
                service_account__customer__first_name__icontains=term
            )
            | Q(
                service_account__customer__last_name__icontains=term
            )
        )

    return queryset


class NetworkNodeListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        nodes = (
            NetworkNode.objects
            .for_organization(request.organization)
            .annotate(
                assignment_count=Count(
                    "service_assignments",
                    filter=Q(
                        service_assignments__is_active=True
                    ),
                )
            )
        )

        active = request.query_params.get(
            "active",
            "",
        ).strip().lower()

        node_type = request.query_params.get(
            "type",
            "",
        ).strip()

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        if active == "true":
            nodes = nodes.filter(is_active=True)
        elif active == "false":
            nodes = nodes.filter(is_active=False)

        if node_type:
            nodes = nodes.filter(node_type=node_type)

        if search:
            nodes = nodes.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(management_ip__icontains=search)
                | Q(location__icontains=search)
            )

        nodes = nodes.order_by("name")

        serializer = NetworkNodeSerializer(
            nodes,
            many=True,
        )

        return Response(serializer.data)


class NetworkNodeDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request, node_id):
        try:
            node = (
                NetworkNode.objects
                .for_organization(request.organization)
                .annotate(
                    assignment_count=Count(
                        "service_assignments",
                        filter=Q(
                            service_assignments__is_active=True
                        ),
                    )
                )
                .get(id=node_id)
            )
        except NetworkNode.DoesNotExist as exc:
            raise NotFound(
                "Network node was not found in this organization."
            ) from exc

        serializer = NetworkNodeSerializer(node)

        return Response(serializer.data)


class NetworkAssignmentListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        assignments = (
            NetworkAssignment.objects
            .for_organization(request.organization)
            .select_related(
                "service_account",
                "service_account__customer",
                "network_node",
            )
        )

        node_id = request.query_params.get(
            "node_id",
            "",
        ).strip()

        active = request.query_params.get(
            "active",
            "",
        ).strip().lower()

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        if node_id:
            assignments = assignments.filter(
                network_node_id=node_id
            )

        if active == "true":
            assignments = assignments.filter(
                is_active=True
            )
        elif active == "false":
            assignments = assignments.filter(
                is_active=False
            )

        if search:
            search_terms = [
                term
                for term in search.split()
                if term.strip()
            ]

            for term in search_terms:
                assignments = assignments.filter(
                    Q(
                        service_account__service_number__icontains=term
                    )
                    | Q(
                        service_account__customer__customer_number__icontains=term
                    )
                    | Q(
                        service_account__customer__first_name__icontains=term
                    )
                    | Q(
                        service_account__customer__last_name__icontains=term
                    )
                    | Q(username__icontains=term)
                    | Q(ip_address__icontains=term)
                    | Q(
                        network_node__name__icontains=term
                    )
                    | Q(
                        network_node__code__icontains=term
                    )
                )

        assignments = assignments.order_by(
            "-assigned_at"
        )

        serializer = NetworkAssignmentSerializer(
            assignments,
            many=True,
        )

        return Response(serializer.data)


class ProvisioningRequestListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        requests = (
            ProvisioningRequest.objects
            .for_organization(request.organization)
            .select_related(
                "service_account",
                "service_account__customer",
                "network_assignment",
                "network_assignment__network_node",
            )
        )

        request_status = request.query_params.get(
            "status",
            "",
        ).strip()

        action = request.query_params.get(
            "action",
            "",
        ).strip()

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        if request_status:
            requests = requests.filter(
                status=request_status
            )

        if action:
            requests = requests.filter(
                action=action
            )

        if search:
            search_terms = [
                term
                for term in search.split()
                if term.strip()
            ]

            for term in search_terms:
                requests = requests.filter(
                    Q(
                        service_account__service_number__icontains=term
                    )
                    | Q(
                        service_account__customer__customer_number__icontains=term
                    )
                    | Q(
                        service_account__customer__first_name__icontains=term
                    )
                    | Q(
                        service_account__customer__last_name__icontains=term
                    )
                    | Q(
                        provider_reference__icontains=term
                    )
                    | Q(
                        network_assignment__network_node__name__icontains=term
                    )
                    | Q(
                        network_assignment__network_node__code__icontains=term
                    )
                )

        requests = requests.order_by(
            "-requested_at"
        )

        serializer = ProvisioningRequestSerializer(
            requests,
            many=True,
        )

        return Response(serializer.data)


class ServiceSuspensionRequestView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, service_account_id):
        try:
            result = request_service_suspension(
                organization=request.organization,
                service_account_id=service_account_id,
                requested_by=request.user,
            )
        except ServiceLifecycleError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProvisioningRequestSerializer(
            result.provisioning_request
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ServiceRestoreRequestView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, service_account_id):
        try:
            result = request_service_restore(
                organization=request.organization,
                service_account_id=service_account_id,
                requested_by=request.user,
            )
        except ServiceLifecycleError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProvisioningRequestSerializer(
            result.provisioning_request
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ServicePackageChangeRequestView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, service_account_id):
        input_serializer = RequestPackageChangeSerializer(
            data=request.data
        )
        input_serializer.is_valid(
            raise_exception=True
        )

        try:
            result = request_package_change(
                organization=request.organization,
                service_account_id=service_account_id,
                internet_package_id=(
                    input_serializer.validated_data[
                        "internet_package_id"
                    ]
                ),
                requested_by=request.user,
            )
        except ServiceLifecycleError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProvisioningRequestSerializer(
            result.provisioning_request
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )