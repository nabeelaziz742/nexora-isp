from django.db.models import Count, Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from network.models import (
    NetworkAssignment,
    NetworkNode,
    PointOfPresence,
    ProvisioningRequest,
)
from network.serializers import (
    NetworkAssignmentSerializer,
    NetworkNodeSerializer,
    PointOfPresenceDetailSerializer,
    PointOfPresenceSerializer,
    ProvisioningRequestSerializer,
    RequestPackageChangeSerializer,
)
from network.services import (
    PopDomainError,
    ServiceLifecycleError,
    create_pop_site,
    get_pop_statistics,
    request_package_change,
    request_service_restore,
    request_service_suspension,
    update_pop_site,
)
from tenancy.permissions import CanManageNetwork, HasActiveTenantContext, IsOrganizationStaffOrOwner


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


# ==============================================================================
# POINT OF PRESENCE (POP) REST API VIEWS (BATCH 13)
# ==============================================================================

class PopSiteListCreateView(APIView):
    permission_classes = [CanManageNetwork]

    def get(self, request):
        qs = (
            PointOfPresence.objects
            .for_organization(request.organization)
            .select_related("area", "area__city", "supervisor")
            .prefetch_related("nodes")
            .order_by("name")
        )

        pop_type = request.query_params.get("pop_type", "").strip()
        pop_status = request.query_params.get("status", "").strip()
        area_id = request.query_params.get("area_id", "").strip()
        search = request.query_params.get("search", "").strip()

        if pop_type:
            qs = qs.filter(pop_type=pop_type)
        if pop_status:
            qs = qs.filter(status=pop_status)
        if area_id:
            qs = qs.filter(area_id=area_id)
        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(name__icontains=search)
                | Q(address__icontains=search)
                | Q(notes__icontains=search)
            )

        pop_list = []
        for pop in qs:
            stats = get_pop_statistics(organization=request.organization, pop=pop)
            pop.nodes_count = stats["nodes_count"]
            pop.active_subscribers_count = stats["active_subscribers_count"]
            pop_list.append(pop)

        serializer = PointOfPresenceSerializer(pop_list, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PointOfPresenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            pop = create_pop_site(
                organization=request.organization,
                actor=request.user,
                code=data["code"],
                name=data["name"],
                pop_type=data.get("pop_type", PointOfPresence.PopType.DISTRIBUTION),
                area_id=data.get("area").id if data.get("area") else None,
                address=data.get("address", ""),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                rack_capacity_units=data.get("rack_capacity_units", 42),
                power_backup_type=data.get("power_backup_type", "UPS_GENERATOR"),
                status=data.get("status", PointOfPresence.Status.ACTIVE),
                supervisor_id=data.get("supervisor").id if data.get("supervisor") else None,
                notes=data.get("notes", ""),
            )
        except PopDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        reloaded = (
            PointOfPresence.objects
            .for_organization(request.organization)
            .select_related("area", "area__city", "supervisor")
            .get(id=pop.id)
        )
        return Response(PointOfPresenceSerializer(reloaded).data, status=status.HTTP_201_CREATED)


class PopSiteDetailView(APIView):
    permission_classes = [CanManageNetwork]

    def _get_pop(self, request, pop_id):
        try:
            return (
                PointOfPresence.objects
                .for_organization(request.organization)
                .select_related("area", "area__city", "supervisor")
                .prefetch_related("nodes")
                .get(id=pop_id)
            )
        except PointOfPresence.DoesNotExist as exc:
            raise NotFound("POP site was not found in this organization.") from exc

    def get(self, request, pop_id):
        pop = self._get_pop(request, pop_id)
        stats = get_pop_statistics(organization=request.organization, pop=pop)
        pop.nodes_count = stats["nodes_count"]
        pop.active_subscribers_count = stats["active_subscribers_count"]
        return Response(PointOfPresenceDetailSerializer(pop).data)

    def patch(self, request, pop_id):
        serializer = PointOfPresenceSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        kwargs = {}
        if "code" in data:
            kwargs["code"] = data["code"]
        if "name" in data:
            kwargs["name"] = data["name"]
        if "pop_type" in data:
            kwargs["pop_type"] = data["pop_type"]
        if "area" in data:
            kwargs["area_id"] = data["area"].id if data["area"] else None
        if "address" in data:
            kwargs["address"] = data["address"]
        if "latitude" in data:
            kwargs["latitude"] = data["latitude"]
        if "longitude" in data:
            kwargs["longitude"] = data["longitude"]
        if "rack_capacity_units" in data:
            kwargs["rack_capacity_units"] = data["rack_capacity_units"]
        if "power_backup_type" in data:
            kwargs["power_backup_type"] = data["power_backup_type"]
        if "status" in data:
            kwargs["status"] = data["status"]
        if "supervisor" in data:
            kwargs["supervisor_id"] = data["supervisor"].id if data["supervisor"] else None
        if "notes" in data:
            kwargs["notes"] = data["notes"]
        if "is_active" in data:
            kwargs["is_active"] = data["is_active"]

        try:
            pop = update_pop_site(
                organization=request.organization,
                actor=request.user,
                pop_id=pop_id,
                **kwargs,
            )
        except PopDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        reloaded = (
            PointOfPresence.objects
            .for_organization(request.organization)
            .select_related("area", "area__city", "supervisor")
            .prefetch_related("nodes")
            .get(id=pop.id)
        )
        stats = get_pop_statistics(organization=request.organization, pop=reloaded)
        reloaded.nodes_count = stats["nodes_count"]
        reloaded.active_subscribers_count = stats["active_subscribers_count"]
        return Response(PointOfPresenceDetailSerializer(reloaded).data)