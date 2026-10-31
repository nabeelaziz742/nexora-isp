from decimal import Decimal
from rest_framework import serializers

from hr.models import StaffAttendance, StaffLeaveRequest
from tenancy.models import StaffProfile


class StaffSimpleSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            "id",
            "staff_code",
            "full_name",
            "email",
            "department",
            "designation",
            "role",
            "status",
        ]

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.email


class StaffAttendanceSerializer(serializers.ModelSerializer):
    staff = StaffSimpleSerializer(read_only=True)
    marked_by_email = serializers.EmailField(
        source="marked_by.email", read_only=True, default=None
    )

    class Meta:
        model = StaffAttendance
        fields = [
            "id",
            "staff",
            "date",
            "status",
            "check_in",
            "check_out",
            "shift_type",
            "late_minutes",
            "overtime_minutes",
            "is_excused",
            "notes",
            "ip_address",
            "location_coordinates",
            "is_manual_override",
            "override_reason",
            "marked_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class StaffCheckInSerializer(serializers.Serializer):
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    shift_type = serializers.ChoiceField(
        choices=StaffAttendance.ShiftType.choices,
        default=StaffAttendance.ShiftType.REGULAR,
    )
    ip_address = serializers.IPAddressField(
        required=False, allow_null=True, allow_blank=True
    )
    location_coordinates = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    timestamp = serializers.DateTimeField(required=False, allow_null=True)


class StaffCheckOutSerializer(serializers.Serializer):
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    target_date = serializers.DateField(required=False, allow_null=True)
    timestamp = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    location_coordinates = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class StaffAttendanceOverrideSerializer(serializers.Serializer):
    staff_id = serializers.UUIDField(required=True)
    date = serializers.DateField(required=True)
    override_reason = serializers.CharField(required=True, allow_blank=False)
    status = serializers.ChoiceField(
        choices=StaffAttendance.Status.choices, required=False
    )
    check_in = serializers.TimeField(required=False, allow_null=True)
    check_out = serializers.TimeField(required=False, allow_null=True)
    shift_type = serializers.ChoiceField(
        choices=StaffAttendance.ShiftType.choices, required=False
    )
    late_minutes = serializers.IntegerField(
        required=False, min_value=0, allow_null=True
    )
    overtime_minutes = serializers.IntegerField(
        required=False, min_value=0, allow_null=True
    )
    is_excused = serializers.BooleanField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_override_reason(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Override reason cannot be empty.")
        return value.strip()


class BulkAttendanceMarkSerializer(serializers.Serializer):
    date = serializers.DateField(required=True)
    status = serializers.ChoiceField(
        choices=StaffAttendance.Status.choices, required=True
    )
    staff_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        default=list,
    )
    shift_type = serializers.ChoiceField(
        choices=StaffAttendance.ShiftType.choices,
        default=StaffAttendance.ShiftType.REGULAR,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    overwrite_existing = serializers.BooleanField(default=False)


class StaffLeaveRequestSerializer(serializers.ModelSerializer):
    staff = StaffSimpleSerializer(read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StaffLeaveRequest
        fields = [
            "id",
            "staff",
            "leave_type",
            "start_date",
            "end_date",
            "total_days",
            "reason",
            "status",
            "reviewed_by_name",
            "reviewed_at",
            "review_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_reviewed_by_name(self, obj) -> str | None:
        if not obj.reviewed_by:
            return None
        return obj.reviewed_by.get_full_name() or obj.reviewed_by.email


class StaffLeaveRequestCreateSerializer(serializers.Serializer):
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    leave_type = serializers.ChoiceField(
        choices=StaffLeaveRequest.LeaveType.choices, required=True
    )
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    reason = serializers.CharField(required=True, allow_blank=False)
    total_days = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        allow_null=True,
        min_value=Decimal("0.5"),
    )

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be earlier than start date."}
            )
        reason = attrs.get("reason", "").strip()
        if not reason:
            raise serializers.ValidationError({"reason": "Leave reason is required."})
        return attrs


class StaffLeaveReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[("APPROVE", "Approve"), ("REJECT", "Reject")],
        required=True,
    )
    review_notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
