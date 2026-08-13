from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from support.models import (
    Complaint,
    Incident,
)
from support.serializers import (
    ComplaintCreateSerializer,
    ComplaintSerializer,
    ComplaintStatusTransitionSerializer,
    IncidentCreateSerializer,
    IncidentSerializer,
    IncidentStatusTransitionSerializer,
)
from support.services import (
    SupportDomainError,
    create_complaint,
    create_incident,
    transition_complaint_status,
    transition_incident_status,
)
from tenancy.permissions import IsOrganizationStaffOrOwner


class ComplaintListCreateAPIView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner,
    ]

    def get(self, request):
        complaints = (
            Complaint.objects
            .for_organization(request.organization)
            .select_related(
                "customer",
                "service_account",
                "created_by",
                "resolved_by",
            )
        )

        status_value = request.query_params.get("status")
        priority = request.query_params.get("priority")
        category = request.query_params.get("category")
        customer_id = request.query_params.get("customer_id")
        service_account_id = request.query_params.get(
            "service_account_id"
        )
        search = request.query_params.get("search")

        if status_value:
            complaints = complaints.filter(
                status=status_value,
            )

        if priority:
            complaints = complaints.filter(
                priority=priority,
            )

        if category:
            complaints = complaints.filter(
                category=category,
            )

        if customer_id:
            complaints = complaints.filter(
                customer_id=customer_id,
            )

        if service_account_id:
            complaints = complaints.filter(
                service_account_id=service_account_id,
            )

        if search:
            complaints = complaints.filter(
                Q(complaint_number__icontains=search)
                | Q(
                    customer__customer_number__icontains=search
                )
                | Q(
                    customer__first_name__icontains=search
                )
                | Q(
                    customer__last_name__icontains=search
                )
                | Q(
                    service_account__service_number__icontains=search
                )
                | Q(subject__icontains=search)
            )

        serializer = ComplaintSerializer(
            complaints,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = ComplaintCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = create_complaint(
                organization=request.organization,
                created_by=request.user,
                **serializer.validated_data,
            )
        except SupportDomainError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = ComplaintSerializer(
            result.complaint,
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ComplaintDetailAPIView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner,
    ]

    def get(self, request, complaint_id):
        try:
            complaint = (
                Complaint.objects
                .for_organization(request.organization)
                .select_related(
                    "customer",
                    "service_account",
                    "created_by",
                    "resolved_by",
                )
                .get(id=complaint_id)
            )
        except Complaint.DoesNotExist:
            return Response(
                {
                    "detail": "Complaint was not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ComplaintSerializer(complaint)

        return Response(serializer.data)


class ComplaintStatusTransitionAPIView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner,
    ]

    def post(self, request, complaint_id):
        serializer = ComplaintStatusTransitionSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = transition_complaint_status(
                organization=request.organization,
                complaint_id=complaint_id,
                actor=request.user,
                **serializer.validated_data,
            )
        except SupportDomainError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = ComplaintSerializer(
            result.complaint,
        )

        return Response(response_serializer.data)


class IncidentListCreateAPIView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner,
    ]

    def get(self, request):
        incidents = (
            Incident.objects
            .for_organization(request.organization)
            .select_related(
                "network_node",
                "created_by",
                "resolved_by",
            )
            .prefetch_related(
                "affected_services__service_account__customer",
            )
        )

        status_value = request.query_params.get("status")
        severity = request.query_params.get("severity")
        network_node_id = request.query_params.get(
            "network_node_id"
        )
        service_account_id = request.query_params.get(
            "service_account_id"
        )
        search = request.query_params.get("search")

        if status_value:
            incidents = incidents.filter(
                status=status_value,
            )

        if severity:
            incidents = incidents.filter(
                severity=severity,
            )

        if network_node_id:
            incidents = incidents.filter(
                network_node_id=network_node_id,
            )

        if service_account_id:
            incidents = incidents.filter(
                affected_services__service_account_id=(
                    service_account_id
                ),
            )

        if search:
            incidents = incidents.filter(
                Q(incident_number__icontains=search)
                | Q(title__icontains=search)
                | Q(network_node__name__icontains=search)
                | Q(network_node__code__icontains=search)
                | Q(
                    affected_services__service_account__service_number__icontains=search
                )
                | Q(
                    affected_services__service_account__customer__customer_number__icontains=search
                )
                | Q(
                    affected_services__service_account__customer__first_name__icontains=search
                )
                | Q(
                    affected_services__service_account__customer__last_name__icontains=search
                )
            )

        incidents = incidents.distinct()

        serializer = IncidentSerializer(
            incidents,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = IncidentCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = create_incident(
                organization=request.organization,
                created_by=request.user,
                **serializer.validated_data,
            )
        except SupportDomainError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        incident = (
            Incident.objects
            .for_organization(request.organization)
            .select_related(
                "network_node",
                "created_by",
                "resolved_by",
            )
            .prefetch_related(
                "affected_services__service_account__customer",
            )
            .get(id=result.incident.id)
        )

        response_serializer = IncidentSerializer(incident)

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class IncidentDetailAPIView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner,
    ]

    def get(self, request, incident_id):
        try:
            incident = (
                Incident.objects
                .for_organization(request.organization)
                .select_related(
                    "network_node",
                    "created_by",
                    "resolved_by",
                )
                .prefetch_related(
                    "affected_services__service_account__customer",
                )
                .get(id=incident_id)
            )
        except Incident.DoesNotExist:
            return Response(
                {
                    "detail": "Incident was not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = IncidentSerializer(incident)

        return Response(serializer.data)


class IncidentStatusTransitionAPIView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner,
    ]

    def post(self, request, incident_id):
        serializer = IncidentStatusTransitionSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = transition_incident_status(
                organization=request.organization,
                incident_id=incident_id,
                actor=request.user,
                **serializer.validated_data,
            )
        except SupportDomainError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        incident = (
            Incident.objects
            .for_organization(request.organization)
            .select_related(
                "network_node",
                "created_by",
                "resolved_by",
            )
            .prefetch_related(
                "affected_services__service_account__customer",
            )
            .get(id=result.incident.id)
        )

        response_serializer = IncidentSerializer(incident)

        return Response(response_serializer.data)