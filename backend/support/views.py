from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from support.models import (
    Complaint,
    ComplaintInternalNote,
    ComplaintSLAPolicy,
    ComplaintTimeline,
    Incident,
)
from support.serializers import (
    ComplaintAssignSerializer,
    ComplaintCloseSerializer,
    ComplaintCreateSerializer,
    ComplaintEscalateSerializer,
    ComplaintInternalNoteSerializer,
    ComplaintReassignSerializer,
    ComplaintResolveSerializer,
    ComplaintSLAPolicySerializer,
    ComplaintSerializer,
    ComplaintStatusTransitionSerializer,
    ComplaintTimelineSerializer,
    IncidentCreateSerializer,
    IncidentSerializer,
    IncidentStatusTransitionSerializer,
)
from support.services import (
    SupportDomainError,
    add_internal_note,
    assign_complaint,
    confirm_and_close_complaint,
    create_complaint,
    create_incident,
    escalate_complaint,
    get_support_dashboard_metrics,
    reassign_complaint,
    resolve_complaint,
    transition_complaint_status,
    transition_incident_status,
)
from tenancy.permissions import IsOrganizationStaffOrOwner


class ComplaintListCreateAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        complaints = (
            Complaint.objects
            .for_organization(request.organization)
            .select_related(
                "customer",
                "service_account",
                "assigned_to",
                "assigned_by",
                "created_by",
                "resolved_by",
                "escalated_by",
                "escalated_to",
                "linked_incident",
            )
            .prefetch_related(
                "timeline_events__actor",
                "internal_notes_list__author",
            )
        )

        status_value = request.query_params.get("status")
        priority = request.query_params.get("priority")
        category = request.query_params.get("category")
        source = request.query_params.get("source")
        sla_status = request.query_params.get("sla_status")
        assigned_to_id = request.query_params.get("assigned_to_id")
        customer_id = request.query_params.get("customer_id")
        service_account_id = request.query_params.get("service_account_id")
        is_unassigned = request.query_params.get("is_unassigned")
        search = request.query_params.get("search")

        if status_value:
            statuses = [s.strip() for s in status_value.split(",") if s.strip()]
            if len(statuses) == 1:
                complaints = complaints.filter(status=statuses[0])
            elif len(statuses) > 1:
                complaints = complaints.filter(status__in=statuses)

        if priority:
            complaints = complaints.filter(priority=priority)

        if category:
            complaints = complaints.filter(category=category)

        if source:
            complaints = complaints.filter(source=source)

        if sla_status:
            complaints = complaints.filter(sla_status=sla_status)

        if is_unassigned and is_unassigned.lower() in {"true", "1"}:
            complaints = complaints.filter(assigned_to__isnull=True)
        elif assigned_to_id:
            complaints = complaints.filter(assigned_to_id=assigned_to_id)

        if customer_id:
            complaints = complaints.filter(customer_id=customer_id)

        if service_account_id:
            complaints = complaints.filter(service_account_id=service_account_id)

        if search:
            complaints = complaints.filter(
                Q(complaint_number__icontains=search)
                | Q(customer__customer_number__icontains=search)
                | Q(customer__first_name__icontains=search)
                | Q(customer__last_name__icontains=search)
                | Q(customer__phone__icontains=search)
                | Q(service_account__service_number__icontains=search)
                | Q(subject__icontains=search)
                | Q(description__icontains=search)
            )

        serializer = ComplaintSerializer(complaints, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ComplaintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = create_complaint(
                organization=request.organization,
                created_by=request.user,
                **serializer.validated_data,
            )
        except SupportDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ComplaintSerializer(result.complaint)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ComplaintDetailAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request, complaint_id):
        try:
            complaint = (
                Complaint.objects
                .for_organization(request.organization)
                .select_related(
                    "customer",
                    "service_account",
                    "assigned_to",
                    "assigned_by",
                    "created_by",
                    "resolved_by",
                    "escalated_by",
                    "escalated_to",
                    "linked_incident",
                )
                .prefetch_related(
                    "timeline_events__actor",
                    "internal_notes_list__author",
                )
                .get(id=complaint_id)
            )
        except Complaint.DoesNotExist:
            return Response({"detail": "Complaint was not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ComplaintSerializer(complaint)
        return Response(serializer.data)


class ComplaintAssignAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, complaint_id):
        serializer = ComplaintAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = assign_complaint(
                organization=request.organization,
                complaint_id=complaint_id,
                technician_id=serializer.validated_data["technician_id"],
                notes=serializer.validated_data.get("notes", ""),
                actor=request.user,
            )
        except SupportDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ComplaintSerializer(result.complaint)
        return Response(response_serializer.data)


class ComplaintReassignAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, complaint_id):
        serializer = ComplaintReassignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = reassign_complaint(
                organization=request.organization,
                complaint_id=complaint_id,
                technician_id=serializer.validated_data["technician_id"],
                reason=serializer.validated_data["reason"],
                notes=serializer.validated_data.get("notes", ""),
                actor=request.user,
            )
        except SupportDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ComplaintSerializer(result.complaint)
        return Response(response_serializer.data)


class ComplaintStatusTransitionAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, complaint_id):
        serializer = ComplaintStatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_status = serializer.validated_data["target_status"]
        notes = serializer.validated_data.get("notes", "")

        try:
            result = transition_complaint_status(
                organization=request.organization,
                complaint_id=complaint_id,
                target_status=target_status,
                notes=notes,
                actor=request.user,
            )
        except SupportDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ComplaintSerializer(result.complaint)
        return Response(response_serializer.data)


class ComplaintEscalateAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, complaint_id):
        serializer = ComplaintEscalateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = escalate_complaint(
                organization=request.organization,
                complaint_id=complaint_id,
                reason=serializer.validated_data["reason"],
                escalated_to_id=serializer.validated_data.get("escalated_to_id"),
                actor=request.user,
            )
        except SupportDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ComplaintSerializer(result.complaint)
        return Response(response_serializer.data)


class ComplaintInternalNoteAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request, complaint_id):
        notes = (
            ComplaintInternalNote.objects
            .for_organization(request.organization)
            .filter(complaint_id=complaint_id)
            .select_related("author")
            .order_by("-created_at")
        )
        serializer = ComplaintInternalNoteSerializer(notes, many=True)
        return Response(serializer.data)

    def post(self, request, complaint_id):
        serializer = ComplaintInternalNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            note = add_internal_note(
                organization=request.organization,
                complaint_id=complaint_id,
                note=serializer.validated_data["note"],
                actor=request.user,
            )
        except SupportDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ComplaintInternalNoteSerializer(note)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ComplaintResolveAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, complaint_id):
        serializer = ComplaintResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = resolve_complaint(
                organization=request.organization,
                complaint_id=complaint_id,
                diagnosis_category=serializer.validated_data["diagnosis_category"],
                resolution_summary=serializer.validated_data["resolution_summary"],
                resolution_notes=serializer.validated_data.get("resolution_notes", ""),
                actor=request.user,
            )
        except SupportDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ComplaintSerializer(result.complaint)
        return Response(response_serializer.data)


class ComplaintCloseAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, complaint_id):
        serializer = ComplaintCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = confirm_and_close_complaint(
                organization=request.organization,
                complaint_id=complaint_id,
                confirmation=serializer.validated_data["confirmation"],
                feedback_rating=serializer.validated_data.get("feedback_rating"),
                feedback_notes=serializer.validated_data.get("feedback_notes", ""),
                actor=request.user,
            )
        except SupportDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ComplaintSerializer(result.complaint)
        return Response(response_serializer.data)


class ComplaintTimelineAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request, complaint_id):
        events = (
            ComplaintTimeline.objects
            .for_organization(request.organization)
            .filter(complaint_id=complaint_id)
            .select_related("actor")
            .order_by("-created_at")
        )
        serializer = ComplaintTimelineSerializer(events, many=True)
        return Response(serializer.data)


class SupportDashboardMetricsAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        metrics = get_support_dashboard_metrics(request.organization)
        return Response(metrics)


class ComplaintSLAPolicyListUpdateAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        policies = ComplaintSLAPolicy.objects.for_organization(request.organization).order_by("priority")
        serializer = ComplaintSLAPolicySerializer(policies, many=True)
        return Response(serializer.data)

    def put(self, request):
        policies_data = request.data.get("policies", [])
        if not isinstance(policies_data, list):
            return Response({"detail": "Expected list of policies in 'policies' key."}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for item in policies_data:
            priority = item.get("priority")
            if not priority or priority not in Complaint.Priority.values:
                continue

            policy, _ = ComplaintSLAPolicy.objects.update_or_create(
                organization=request.organization,
                priority=priority,
                defaults={
                    "response_target_minutes": item.get("response_target_minutes", 60),
                    "resolution_target_hours": item.get("resolution_target_hours", 24),
                    "escalation_threshold_hours": item.get("escalation_threshold_hours", 12),
                    "is_active": item.get("is_active", True),
                },
            )
            results.append(policy)

        serializer = ComplaintSLAPolicySerializer(results, many=True)
        return Response(serializer.data)


# ==================== INCIDENT VIEWS (PRESERVED) ====================

class IncidentListCreateAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

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
        network_node_id = request.query_params.get("network_node_id")
        service_account_id = request.query_params.get("service_account_id")
        search = request.query_params.get("search")

        if status_value:
            incidents = incidents.filter(status=status_value)

        if severity:
            incidents = incidents.filter(severity=severity)

        if network_node_id:
            incidents = incidents.filter(network_node_id=network_node_id)

        if service_account_id:
            incidents = incidents.filter(
                affected_services__service_account_id=service_account_id
            )

        if search:
            incidents = incidents.filter(
                Q(incident_number__icontains=search)
                | Q(title__icontains=search)
                | Q(network_node__name__icontains=search)
                | Q(network_node__code__icontains=search)
                | Q(affected_services__service_account__service_number__icontains=search)
                | Q(affected_services__service_account__customer__customer_number__icontains=search)
                | Q(affected_services__service_account__customer__first_name__icontains=search)
                | Q(affected_services__service_account__customer__last_name__icontains=search)
            )

        incidents = incidents.distinct()
        serializer = IncidentSerializer(incidents, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = IncidentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = create_incident(
                organization=request.organization,
                created_by=request.user,
                **serializer.validated_data,
            )
        except SupportDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

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
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class IncidentDetailAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

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
            return Response({"detail": "Incident was not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = IncidentSerializer(incident)
        return Response(serializer.data)


class IncidentStatusTransitionAPIView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, incident_id):
        serializer = IncidentStatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = transition_incident_status(
                organization=request.organization,
                incident_id=incident_id,
                actor=request.user,
                **serializer.validated_data,
            )
        except SupportDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

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