from django.contrib import admin

from hr.models import StaffAttendance, StaffLeaveRequest


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = [
        "staff",
        "date",
        "status",
        "check_in",
        "check_out",
        "late_minutes",
        "is_manual_override",
    ]
    list_filter = ["status", "shift_type", "is_manual_override", "date"]
    search_fields = ["staff__staff_code", "staff__user__email", "staff__user__first_name", "staff__user__last_name"]


@admin.register(StaffLeaveRequest)
class StaffLeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        "staff",
        "leave_type",
        "start_date",
        "end_date",
        "total_days",
        "status",
    ]
    list_filter = ["status", "leave_type"]
    search_fields = ["staff__staff_code", "staff__user__email", "staff__user__first_name", "staff__user__last_name"]
