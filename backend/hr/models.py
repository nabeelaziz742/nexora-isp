import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from tenancy.base_models import TenantScopedModel


class StaffAttendance(TenantScopedModel):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "Late"
        HALF_DAY = "HALF_DAY", "Half Day"
        ON_LEAVE = "ON_LEAVE", "On Leave"
        HOLIDAY = "HOLIDAY", "Holiday"

    class ShiftType(models.TextChoices):
        REGULAR = "REGULAR", "Regular Shift (9AM - 6PM)"
        MORNING = "MORNING", "Morning Shift (8AM - 4PM)"
        EVENING = "EVENING", "Evening Shift (4PM - 12AM)"
        NIGHT = "NIGHT", "Night NOC Shift (12AM - 8AM)"
        FLEXIBLE = "FLEXIBLE", "Flexible Field Shift"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    staff = models.ForeignKey(
        "tenancy.StaffProfile",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    date = models.DateField(
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT,
    )

    check_in = models.TimeField(
        null=True,
        blank=True,
    )

    check_out = models.TimeField(
        null=True,
        blank=True,
    )

    shift_type = models.CharField(
        max_length=30,
        choices=ShiftType.choices,
        default=ShiftType.REGULAR,
    )

    late_minutes = models.PositiveIntegerField(
        default=0,
    )

    overtime_minutes = models.PositiveIntegerField(
        default=0,
    )

    is_excused = models.BooleanField(
        default=False,
    )

    notes = models.TextField(
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    location_coordinates = models.CharField(
        max_length=100,
        blank=True,
    )

    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="marked_attendances",
    )

    is_manual_override = models.BooleanField(
        default=False,
    )

    override_reason = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "hr_staff_attendance"
        ordering = ["-date", "staff__staff_code"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "staff", "date"],
                name="unique_staff_daily_attendance",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "date"],
                name="attendance_org_date_idx",
            ),
            models.Index(
                fields=["organization", "staff", "date"],
                name="attendance_org_stf_date_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="attendance_org_status_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.staff and self.staff.organization_id != self.organization_id:
            raise ValidationError("Staff profile must belong to the same organization.")
        if self.is_manual_override and not self.override_reason.strip():
            raise ValidationError("Override reason is mandatory for manual attendance overrides.")

    def __str__(self):
        return f"{self.staff.staff_code} | {self.date} | {self.status}"


class StaffLeaveRequest(TenantScopedModel):
    class LeaveType(models.TextChoices):
        CASUAL = "CASUAL", "Casual Leave"
        SICK = "SICK", "Sick Leave"
        ANNUAL = "ANNUAL", "Annual Paid Leave"
        UNPAID = "UNPAID", "Unpaid Leave"
        EMERGENCY = "EMERGENCY", "Emergency Leave"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    staff = models.ForeignKey(
        "tenancy.StaffProfile",
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )

    leave_type = models.CharField(
        max_length=30,
        choices=LeaveType.choices,
        default=LeaveType.CASUAL,
    )

    start_date = models.DateField()

    end_date = models.DateField()

    total_days = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=Decimal("1.0"),
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_leaves",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    review_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "hr_staff_leave_request"
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="leave_end_date_gte_start_date",
            ),
            models.CheckConstraint(
                condition=models.Q(total_days__gt=0),
                name="leave_total_days_gt_zero",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="leave_org_status_idx",
            ),
            models.Index(
                fields=["organization", "staff", "status"],
                name="leave_org_staff_status_idx",
            ),
            models.Index(
                fields=["organization", "start_date", "end_date"],
                name="leave_org_dates_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.staff and self.staff.organization_id != self.organization_id:
            raise ValidationError("Staff profile must belong to the same organization.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be earlier than start date.")

    def __str__(self):
        return f"{self.staff.staff_code} | {self.leave_type} ({self.start_date} to {self.end_date}) [{self.status}]"
