from django.urls import path

from hr.views import (
    BulkAttendanceMarkAPIView,
    DailyAttendanceSummaryAPIView,
    MonthlyAttendanceMatrixAPIView,
    StaffAttendanceOverrideAPIView,
    StaffCheckInAPIView,
    StaffCheckOutAPIView,
    StaffLeaveRequestListCreateAPIView,
    StaffLeaveReviewAPIView,
)

urlpatterns = [
    # Attendance Endpoints
    path(
        "attendance/daily/",
        DailyAttendanceSummaryAPIView.as_view(),
        name="hr-attendance-daily",
    ),
    path(
        "attendance/summary/",
        DailyAttendanceSummaryAPIView.as_view(),
        name="hr-attendance-summary",
    ),
    path(
        "attendance/check-in/",
        StaffCheckInAPIView.as_view(),
        name="hr-attendance-check-in",
    ),
    path(
        "attendance/check-out/",
        StaffCheckOutAPIView.as_view(),
        name="hr-attendance-check-out",
    ),
    path(
        "attendance/override/",
        StaffAttendanceOverrideAPIView.as_view(),
        name="hr-attendance-override",
    ),
    path(
        "attendance/bulk-mark/",
        BulkAttendanceMarkAPIView.as_view(),
        name="hr-attendance-bulk-mark",
    ),
    path(
        "attendance/monthly-matrix/",
        MonthlyAttendanceMatrixAPIView.as_view(),
        name="hr-attendance-monthly-matrix",
    ),

    # Leave Request Endpoints
    path(
        "attendance/leaves/",
        StaffLeaveRequestListCreateAPIView.as_view(),
        name="hr-attendance-leaves",
    ),
    path(
        "attendance/leaves/<uuid:leave_id>/review/",
        StaffLeaveReviewAPIView.as_view(),
        name="hr-attendance-leave-review",
    ),
]
