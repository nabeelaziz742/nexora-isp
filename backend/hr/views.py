from datetime import date, datetime
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from hr.attendance_services import (
    HRDomainError,
    bulk_mark_attendance,
    check_in_staff,
    check_out_staff,
    create_leave_request,
    get_daily_attendance_summary,
    get_monthly_attendance_matrix,
    override_attendance,
    review_leave_request,
)
from hr.models import StaffLeaveRequest
from hr.permissions import CanManageHR, CanSubmitAttendance
from hr.serializers import (
    BulkAttendanceMarkSerializer,
    StaffAttendanceOverrideSerializer,
    StaffAttendanceSerializer,
    StaffCheckInSerializer,
    StaffCheckOutSerializer,
    StaffLeaveRequestCreateSerializer,
    StaffLeaveRequestSerializer,
    StaffLeaveReviewSerializer,
)
from tenancy.models import StaffProfile
from tenancy.permissions import get_effective_role


def _get_caller_staff_profile(organization, user) -> StaffProfile:
    """Finds the active StaffProfile for the authenticated user in the active tenant."""
    profile = StaffProfile.objects.filter(
        organization=organization,
        user=user,
        status=StaffProfile.Status.ACTIVE,
    ).first()
    if not profile:
        raise ValidationError(
            {"detail": "No active staff profile found for authenticated user in this organization."}
        )
    return profile


def _is_manager_or_above(request) -> bool:
    """Returns True if the caller has OWNER, ADMIN, or MANAGER role."""
    role = get_effective_role(request)
    return role in {
        StaffProfile.Role.OWNER,
        StaffProfile.Role.ADMIN,
        StaffProfile.Role.MANAGER,
    }


def _resolve_target_staff(request, staff_id: UUID | str | None) -> StaffProfile:
    """
    Resolves the target StaffProfile. If staff_id is provided and differs from caller,
    requires Manager/Admin/Owner authorization.
    """
    caller_profile = _get_caller_staff_profile(request.organization, request.user)
    if staff_id is None or str(staff_id) == str(caller_profile.id):
        return caller_profile

    if not _is_manager_or_above(request):
        raise PermissionDenied(
            "You do not have permission to perform actions for another staff member."
        )

    target_profile = StaffProfile.objects.filter(
        organization=request.organization,
        id=staff_id,
    ).first()

    if not target_profile:
        raise NotFound("Target staff profile was not found in this organization.")

    return target_profile


# ==============================================================================
# ATTENDANCE APIS
# ==============================================================================

class StaffCheckInAPIView(APIView):
    permission_classes = [CanSubmitAttendance]

    def post(self, request):
        serializer = StaffCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_staff = _resolve_target_staff(request, data.get("staff_id"))
        ip_addr = data.get("ip_address") or request.META.get("REMOTE_ADDR")

        try:
            attendance = check_in_staff(
                organization=request.organization,
                staff=target_staff,
                actor=request.user,
                timestamp=data.get("timestamp"),
                shift_type=data.get("shift_type"),
                ip_address=ip_addr,
                location_coordinates=data.get("location_coordinates", ""),
                notes=data.get("notes", ""),
            )
        except (HRDomainError, DjangoValidationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            StaffAttendanceSerializer(attendance).data,
            status=status.HTTP_201_CREATED,
        )


class StaffCheckOutAPIView(APIView):
    permission_classes = [CanSubmitAttendance]

    def post(self, request):
        serializer = StaffCheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_staff = _resolve_target_staff(request, data.get("staff_id"))

        try:
            attendance = check_out_staff(
                organization=request.organization,
                staff=target_staff,
                actor=request.user,
                timestamp=data.get("timestamp"),
                target_date=data.get("target_date"),
                notes=data.get("notes", ""),
                location_coordinates=data.get("location_coordinates", ""),
            )
        except (HRDomainError, DjangoValidationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            StaffAttendanceSerializer(attendance).data,
            status=status.HTTP_200_OK,
        )


class StaffAttendanceOverrideAPIView(APIView):
    permission_classes = [CanManageHR]

    def post(self, request):
        serializer = StaffAttendanceOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_staff = StaffProfile.objects.filter(
            organization=request.organization,
            id=data["staff_id"],
        ).first()

        if not target_staff:
            raise NotFound("Target staff profile was not found in this organization.")

        try:
            attendance = override_attendance(
                organization=request.organization,
                actor=request.user,
                staff=target_staff,
                date=data["date"],
                override_reason=data["override_reason"],
                status=data.get("status"),
                check_in=data.get("check_in"),
                check_out=data.get("check_out"),
                shift_type=data.get("shift_type"),
                late_minutes=data.get("late_minutes"),
                overtime_minutes=data.get("overtime_minutes"),
                is_excused=data.get("is_excused"),
                notes=data.get("notes", ""),
            )
        except (HRDomainError, DjangoValidationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            StaffAttendanceSerializer(attendance).data,
            status=status.HTTP_200_OK,
        )


class BulkAttendanceMarkAPIView(APIView):
    permission_classes = [CanManageHR]

    def post(self, request):
        serializer = BulkAttendanceMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = bulk_mark_attendance(
                organization=request.organization,
                actor=request.user,
                date=data["date"],
                status=data["status"],
                staff_ids=data.get("staff_ids") or None,
                shift_type=data.get("shift_type"),
                notes=data.get("notes", ""),
                overwrite_existing=data.get("overwrite_existing", False),
            )
        except (HRDomainError, DjangoValidationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)


class DailyAttendanceSummaryAPIView(APIView):
    permission_classes = [CanSubmitAttendance]

    def get(self, request):
        date_param = request.query_params.get("date")
        department = request.query_params.get("department")

        target_date = None
        if date_param:
            try:
                target_date = date.fromisoformat(date_param)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        summary = get_daily_attendance_summary(
            organization=request.organization,
            target_date=target_date,
            department=department,
        )

        # Scoping: if regular staff, filter records to self
        if not _is_manager_or_above(request):
            caller_profile = _get_caller_staff_profile(request.organization, request.user)
            summary["records"] = [
                r for r in summary["records"] if r["staff_id"] == str(caller_profile.id)
            ]
            summary["total_active_staff"] = len(summary["records"])

        return Response(summary, status=status.HTTP_200_OK)


class MonthlyAttendanceMatrixAPIView(APIView):
    permission_classes = [CanSubmitAttendance]

    def get(self, request):
        today = date.today()
        year_param = request.query_params.get("year", str(today.year))
        month_param = request.query_params.get("month", str(today.month))
        department = request.query_params.get("department")

        try:
            year = int(year_param)
            month = int(month_param)
        except ValueError:
            return Response(
                {"detail": "Year and month must be valid integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            matrix = get_monthly_attendance_matrix(
                organization=request.organization,
                year=year,
                month=month,
                department=department,
            )
        except HRDomainError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Scoping: if regular staff, filter matrix to self
        if not _is_manager_or_above(request):
            caller_profile = _get_caller_staff_profile(request.organization, request.user)
            matrix["matrix"] = [
                row for row in matrix["matrix"] if row["staff_id"] == str(caller_profile.id)
            ]
            matrix["total_staff"] = len(matrix["matrix"])

        return Response(matrix, status=status.HTTP_200_OK)


# ==============================================================================
# LEAVE REQUEST APIS
# ==============================================================================

class StaffLeaveRequestListCreateAPIView(APIView):
    permission_classes = [CanSubmitAttendance]

    def get(self, request):
        queryset = StaffLeaveRequest.objects.for_organization(request.organization).select_related(
            "staff", "staff__user", "reviewed_by"
        )

        # Scoping: regular staff only see their own requests
        if not _is_manager_or_above(request):
            queryset = queryset.filter(staff__user=request.user)
        else:
            staff_id = request.query_params.get("staff_id")
            if staff_id:
                queryset = queryset.filter(staff_id=staff_id)

        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.upper())

        leave_type_param = request.query_params.get("leave_type")
        if leave_type_param:
            queryset = queryset.filter(leave_type=leave_type_param.upper())

        serializer = StaffLeaveRequestSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = StaffLeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_staff = _resolve_target_staff(request, data.get("staff_id"))

        try:
            leave_req = create_leave_request(
                organization=request.organization,
                actor=request.user,
                staff=target_staff,
                leave_type=data["leave_type"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                total_days=data.get("total_days"),
            )
        except (HRDomainError, DjangoValidationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            StaffLeaveRequestSerializer(leave_req).data,
            status=status.HTTP_201_CREATED,
        )


class StaffLeaveReviewAPIView(APIView):
    permission_classes = [CanManageHR]

    def post(self, request, leave_id):
        serializer = StaffLeaveReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        leave_req = StaffLeaveRequest.objects.for_organization(
            request.organization
        ).select_related("staff", "staff__user").filter(id=leave_id).first()

        if not leave_req:
            raise NotFound("Leave request not found in this organization.")

        try:
            reviewed_req = review_leave_request(
                organization=request.organization,
                actor=request.user,
                leave_request=leave_req,
                action=data["action"],
                review_notes=data.get("review_notes", ""),
            )
        except (HRDomainError, DjangoValidationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            StaffLeaveRequestSerializer(reviewed_req).data,
            status=status.HTTP_200_OK,
        )
