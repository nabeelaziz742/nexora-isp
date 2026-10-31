import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from hr.models import StaffAttendance, StaffLeaveRequest
from tenancy.models import Organization, OrganizationMembership, StaffProfile
from tenancy.services import record_audit_log

User = get_user_model()


class HRDomainError(Exception):
    """Base domain exception for HR and Attendance operations."""
    pass


# Default shift configuration defining operational windows and grace periods
SHIFT_CONFIG: dict[str, dict[str, Any]] = {
    StaffAttendance.ShiftType.REGULAR: {
        "start_time": time(9, 0),
        "end_time": time(18, 0),
        "grace_minutes": 15,
        "is_overnight": False,
    },
    StaffAttendance.ShiftType.MORNING: {
        "start_time": time(8, 0),
        "end_time": time(16, 0),
        "grace_minutes": 15,
        "is_overnight": False,
    },
    StaffAttendance.ShiftType.EVENING: {
        "start_time": time(16, 0),
        "end_time": time(0, 0),
        "grace_minutes": 15,
        "is_overnight": True,
    },
    StaffAttendance.ShiftType.NIGHT: {
        "start_time": time(0, 0),
        "end_time": time(8, 0),
        "grace_minutes": 15,
        "is_overnight": False,
    },
    StaffAttendance.ShiftType.FLEXIBLE: {
        "start_time": None,
        "end_time": None,
        "grace_minutes": 0,
        "is_overnight": False,
    },
}


def _get_actor_role(organization: Organization, actor: User) -> str:
    """
    Safely resolves the operational role for the actor within an organization.
    Returns StaffProfile.Role or empty string if not found / inactive.
    """
    if not actor or not actor.is_authenticated:
        return ""

    membership = OrganizationMembership.objects.filter(
        organization=organization,
        user=actor,
        is_active=True,
    ).first()
    if not membership:
        return ""

    if membership.role == OrganizationMembership.Role.OWNER:
        return StaffProfile.Role.OWNER

    profile = getattr(membership, "profile", None)
    if profile is None:
        profile = StaffProfile.objects.filter(
            organization=organization,
            user=actor,
        ).first()

    if profile and profile.role:
        return profile.role

    if membership.role == OrganizationMembership.Role.TECHNICIAN:
        return StaffProfile.Role.TECHNICIAN

    return StaffProfile.Role.STAFF


def _can_manage_hr(organization: Organization, actor: User) -> bool:
    """
    Checks if the actor has managerial or administrative privileges for HR operations.
    """
    role = _get_actor_role(organization, actor)
    return role in {
        StaffProfile.Role.OWNER,
        StaffProfile.Role.ADMIN,
        StaffProfile.Role.MANAGER,
    }


def _get_local_datetime(organization: Organization, dt: datetime | None = None) -> datetime:
    """
    Converts a datetime (or current time) to the organization's local timezone.
    """
    if dt is None:
        dt = timezone.now()
    elif timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)

    tz_name = (organization.timezone or "").strip() or "UTC"
    try:
        org_tz = ZoneInfo(tz_name)
    except Exception:
        org_tz = ZoneInfo("UTC")

    return dt.astimezone(org_tz)


def calculate_late_minutes(
    shift_type: str,
    check_in_time: time,
    custom_grace_minutes: int | None = None,
) -> tuple[int, str]:
    """
    Calculates late minutes and determines attendance status (PRESENT vs LATE).
    Returns (late_minutes, status).
    """
    config = SHIFT_CONFIG.get(shift_type, SHIFT_CONFIG[StaffAttendance.ShiftType.REGULAR])
    start_time = config["start_time"]
    if start_time is None:
        return 0, StaffAttendance.Status.PRESENT

    grace = custom_grace_minutes if custom_grace_minutes is not None else config["grace_minutes"]
    start_mins = start_time.hour * 60 + start_time.minute
    checkin_mins = check_in_time.hour * 60 + check_in_time.minute
    threshold_mins = start_mins + grace

    if checkin_mins > threshold_mins:
        late_mins = checkin_mins - start_mins
        return late_mins, StaffAttendance.Status.LATE

    return 0, StaffAttendance.Status.PRESENT


def calculate_overtime_minutes(
    shift_type: str,
    check_in_time: time,
    check_out_time: time,
) -> int:
    """
    Calculates overtime minutes based on shift boundaries and standard shift duration.
    """
    config = SHIFT_CONFIG.get(shift_type, SHIFT_CONFIG[StaffAttendance.ShiftType.REGULAR])
    end_time = config["end_time"]

    if end_time is None:
        # Flexible shift: overtime beyond 8 hours (480 minutes)
        in_mins = check_in_time.hour * 60 + check_in_time.minute
        out_mins = check_out_time.hour * 60 + check_out_time.minute
        duration = out_mins - in_mins if out_mins >= in_mins else (1440 - in_mins + out_mins)
        if duration > 480:
            return duration - 480
        return 0

    out_mins = check_out_time.hour * 60 + check_out_time.minute

    if config["is_overnight"]:
        # Evening shift ending at midnight (00:00 -> 24:00)
        if out_mins > 0 and out_mins < 12 * 60:
            # Overtime past midnight (e.g. 00:45 -> 45 minutes)
            return out_mins
        return 0

    end_mins = end_time.hour * 60 + end_time.minute
    if out_mins > end_mins:
        return out_mins - end_mins

    return 0


# ==============================================================================
# 1. STAFF CHECK-IN
# ==============================================================================

@transaction.atomic
def check_in_staff(
    *,
    organization: Organization,
    staff: StaffProfile,
    actor: User,
    timestamp: datetime | None = None,
    shift_type: str = StaffAttendance.ShiftType.REGULAR,
    ip_address: str | None = None,
    location_coordinates: str = "",
    notes: str = "",
) -> StaffAttendance:
    """
    Records staff check-in with timezone-awareness, late calculation, and audit logging.
    """
    if not organization.is_active:
        raise HRDomainError("Organization is not active.")

    if staff.organization_id != organization.id:
        raise HRDomainError("Staff profile does not belong to this organization.")

    if staff.status != StaffProfile.Status.ACTIVE:
        raise HRDomainError(f"Staff member is {staff.status} and cannot check in.")

    # Self check-in or Manager/Admin/Owner authorization
    if actor.id != staff.user_id and not _can_manage_hr(organization, actor):
        raise HRDomainError("Permission denied: You do not have permission to check in for this staff member.")

    if shift_type not in StaffAttendance.ShiftType.values:
        raise HRDomainError(f"Invalid shift type: {shift_type}.")

    local_dt = _get_local_datetime(organization, timestamp)
    target_date = local_dt.date()
    local_time = local_dt.time().replace(microsecond=0)

    # Check for existing record
    existing = StaffAttendance.objects.for_organization(organization).filter(
        staff=staff,
        date=target_date,
    ).first()

    if existing:
        if existing.check_in is not None:
            raise HRDomainError(
                f"Staff {staff.staff_code} has already checked in for {target_date} at {existing.check_in}."
            )
        if existing.status == StaffAttendance.Status.ON_LEAVE:
            raise HRDomainError(
                f"Cannot check in: Staff {staff.staff_code} has approved leave on {target_date}."
            )
        if existing.status == StaffAttendance.Status.HOLIDAY:
            raise HRDomainError(
                f"Cannot check in: {target_date} is marked as a holiday."
            )

        late_mins, status = calculate_late_minutes(shift_type, local_time)
        existing.check_in = local_time
        existing.shift_type = shift_type
        existing.late_minutes = late_mins
        existing.status = status
        existing.ip_address = ip_address
        existing.location_coordinates = location_coordinates.strip()
        if notes.strip():
            existing.notes = (existing.notes + "\n" + notes.strip()).strip() if existing.notes else notes.strip()
        existing.marked_by = actor
        existing.save()
        attendance = existing
    else:
        late_mins, status = calculate_late_minutes(shift_type, local_time)
        attendance = StaffAttendance.objects.create(
            organization=organization,
            staff=staff,
            date=target_date,
            status=status,
            check_in=local_time,
            shift_type=shift_type,
            late_minutes=late_mins,
            overtime_minutes=0,
            ip_address=ip_address,
            location_coordinates=location_coordinates.strip(),
            notes=notes.strip(),
            marked_by=actor,
        )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="STAFF_ATTENDANCE_CHECK_IN",
        resource_type="StaffAttendance",
        resource_id=str(attendance.id),
        metadata={
            "staff_id": str(staff.id),
            "staff_code": staff.staff_code,
            "date": str(target_date),
            "check_in": str(attendance.check_in),
            "status": attendance.status,
            "late_minutes": attendance.late_minutes,
            "shift_type": attendance.shift_type,
            "ip_address": ip_address,
            "location_coordinates": location_coordinates,
        },
    )

    return attendance


# ==============================================================================
# 2. STAFF CHECK-OUT
# ==============================================================================

@transaction.atomic
def check_out_staff(
    *,
    organization: Organization,
    staff: StaffProfile,
    actor: User,
    timestamp: datetime | None = None,
    target_date: date | None = None,
    notes: str = "",
    location_coordinates: str = "",
) -> StaffAttendance:
    """
    Records staff check-out, validates against check-in, computes overtime, and audit logs.
    """
    if not organization.is_active:
        raise HRDomainError("Organization is not active.")

    if staff.organization_id != organization.id:
        raise HRDomainError("Staff profile does not belong to this organization.")

    if staff.status != StaffProfile.Status.ACTIVE:
        raise HRDomainError(f"Staff member is {staff.status} and cannot check out.")

    if actor.id != staff.user_id and not _can_manage_hr(organization, actor):
        raise HRDomainError("Permission denied: You do not have permission to check out for this staff member.")

    local_dt = _get_local_datetime(organization, timestamp)
    check_date = target_date or local_dt.date()
    local_time = local_dt.time().replace(microsecond=0)

    attendance = StaffAttendance.objects.for_organization(organization).filter(
        staff=staff,
        date=check_date,
    ).first()

    if not attendance:
        raise HRDomainError(f"No attendance record found for staff {staff.staff_code} on {check_date}.")

    if attendance.check_in is None:
        raise HRDomainError(f"Staff {staff.staff_code} has not checked in for {check_date}.")

    if attendance.check_out is not None:
        raise HRDomainError(
            f"Staff {staff.staff_code} has already checked out for {check_date} at {attendance.check_out}."
        )

    # Validate checkout time is after check-in time for same-day shifts
    config = SHIFT_CONFIG.get(attendance.shift_type, SHIFT_CONFIG[StaffAttendance.ShiftType.REGULAR])
    if not config["is_overnight"] and local_time < attendance.check_in:
        raise HRDomainError("Check-out time cannot be earlier than check-in time.")

    overtime_mins = calculate_overtime_minutes(
        attendance.shift_type,
        attendance.check_in,
        local_time,
    )

    attendance.check_out = local_time
    attendance.overtime_minutes = overtime_mins
    if notes.strip():
        attendance.notes = (attendance.notes + "\n" + notes.strip()).strip() if attendance.notes else notes.strip()
    if location_coordinates.strip():
        attendance.location_coordinates = location_coordinates.strip()

    attendance.save(update_fields=["check_out", "overtime_minutes", "notes", "location_coordinates", "updated_at"])

    record_audit_log(
        organization=organization,
        actor=actor,
        action="STAFF_ATTENDANCE_CHECK_OUT",
        resource_type="StaffAttendance",
        resource_id=str(attendance.id),
        metadata={
            "staff_id": str(staff.id),
            "staff_code": staff.staff_code,
            "date": str(attendance.date),
            "check_in": str(attendance.check_in),
            "check_out": str(attendance.check_out),
            "overtime_minutes": attendance.overtime_minutes,
            "status": attendance.status,
        },
    )

    return attendance


# ==============================================================================
# 3. MANUAL ATTENDANCE OVERRIDE
# ==============================================================================

@transaction.atomic
def override_attendance(
    *,
    organization: Organization,
    actor: User,
    staff: StaffProfile,
    date: date,
    override_reason: str,
    status: str | None = None,
    check_in: time | None = None,
    check_out: time | None = None,
    shift_type: str | None = None,
    late_minutes: int | None = None,
    overtime_minutes: int | None = None,
    is_excused: bool | None = None,
    notes: str = "",
) -> StaffAttendance:
    """
    Manually overrides or creates an attendance record with before/after state audit logging.
    Requires Manager, Admin, or Owner privilege and non-empty override reason.
    """
    if not organization.is_active:
        raise HRDomainError("Organization is not active.")

    if not _can_manage_hr(organization, actor):
        raise HRDomainError("Permission denied: Only Owners, Admins, or Managers can perform manual attendance overrides.")

    if staff.organization_id != organization.id:
        raise HRDomainError("Staff profile does not belong to this organization.")

    reason = (override_reason or "").strip()
    if not reason:
        raise HRDomainError("Override reason is mandatory for manual attendance overrides.")

    if status is not None and status not in StaffAttendance.Status.values:
        raise HRDomainError(f"Invalid attendance status: {status}.")

    if shift_type is not None and shift_type not in StaffAttendance.ShiftType.values:
        raise HRDomainError(f"Invalid shift type: {shift_type}.")

    if check_in is not None and check_out is not None and check_out < check_in:
        effective_shift = shift_type or StaffAttendance.ShiftType.REGULAR
        config = SHIFT_CONFIG.get(effective_shift, SHIFT_CONFIG[StaffAttendance.ShiftType.REGULAR])
        if not config["is_overnight"]:
            raise HRDomainError("Check-out time cannot be earlier than check-in time.")

    attendance = StaffAttendance.objects.for_organization(organization).filter(
        staff=staff,
        date=date,
    ).first()

    if attendance:
        before_state = {
            "exists": True,
            "status": attendance.status,
            "check_in": str(attendance.check_in) if attendance.check_in else None,
            "check_out": str(attendance.check_out) if attendance.check_out else None,
            "late_minutes": attendance.late_minutes,
            "overtime_minutes": attendance.overtime_minutes,
            "shift_type": attendance.shift_type,
            "is_excused": attendance.is_excused,
            "is_manual_override": attendance.is_manual_override,
            "override_reason": attendance.override_reason,
            "marked_by": attendance.marked_by_id,
        }
    else:
        before_state = {"exists": False}
        attendance = StaffAttendance(
            organization=organization,
            staff=staff,
            date=date,
            status=status or StaffAttendance.Status.PRESENT,
        )

    attendance.is_manual_override = True
    attendance.override_reason = reason
    attendance.marked_by = actor

    if status is not None:
        attendance.status = status
    if check_in is not None:
        attendance.check_in = check_in
    if check_out is not None:
        attendance.check_out = check_out
    if shift_type is not None:
        attendance.shift_type = shift_type
    if late_minutes is not None:
        attendance.late_minutes = max(0, late_minutes)
    if overtime_minutes is not None:
        attendance.overtime_minutes = max(0, overtime_minutes)
    if is_excused is not None:
        attendance.is_excused = is_excused
    if notes.strip():
        attendance.notes = (attendance.notes + "\n" + notes.strip()).strip() if attendance.notes else notes.strip()

    attendance.full_clean()
    attendance.save()

    after_state = {
        "status": attendance.status,
        "check_in": str(attendance.check_in) if attendance.check_in else None,
        "check_out": str(attendance.check_out) if attendance.check_out else None,
        "late_minutes": attendance.late_minutes,
        "overtime_minutes": attendance.overtime_minutes,
        "shift_type": attendance.shift_type,
        "is_excused": attendance.is_excused,
        "is_manual_override": True,
        "override_reason": attendance.override_reason,
        "marked_by": str(actor.id),
    }

    record_audit_log(
        organization=organization,
        actor=actor,
        action="STAFF_ATTENDANCE_OVERRIDE",
        resource_type="StaffAttendance",
        resource_id=str(attendance.id),
        metadata={
            "staff_id": str(staff.id),
            "staff_code": staff.staff_code,
            "date": str(date),
            "override_reason": reason,
            "before_state": before_state,
            "after_state": after_state,
        },
    )

    return attendance


# ==============================================================================
# 4. BULK ATTENDANCE MARKING
# ==============================================================================

@transaction.atomic
def bulk_mark_attendance(
    *,
    organization: Organization,
    actor: User,
    date: date,
    status: str,
    staff_ids: list[UUID | str] | None = None,
    shift_type: str = StaffAttendance.ShiftType.REGULAR,
    notes: str = "",
    overwrite_existing: bool = False,
) -> dict[str, int]:
    """
    Bulk marks attendance for tenant staff safely and idempotently.
    Preserves approved leave and existing punch-ins unless explicitly overridden.
    """
    if not organization.is_active:
        raise HRDomainError("Organization is not active.")

    if not _can_manage_hr(organization, actor):
        raise HRDomainError("Permission denied: Only Owners, Admins, or Managers can bulk mark attendance.")

    if status not in StaffAttendance.Status.values:
        raise HRDomainError(f"Invalid attendance status: {status}.")

    if shift_type not in StaffAttendance.ShiftType.values:
        raise HRDomainError(f"Invalid shift type: {shift_type}.")

    staff_qs = StaffProfile.objects.filter(
        organization=organization,
        status=StaffProfile.Status.ACTIVE,
    )
    if staff_ids is not None:
        staff_qs = staff_qs.filter(id__in=staff_ids)

    staff_list = list(staff_qs)
    if not staff_list:
        return {"created": 0, "updated": 0, "skipped": 0, "total": 0}

    existing_map = {
        att.staff_id: att
        for att in StaffAttendance.objects.for_organization(organization).filter(
            date=date,
            staff__in=staff_list,
        )
    }

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for staff in staff_list:
        existing = existing_map.get(staff.id)
        if existing:
            # Never overwrite approved leave
            if existing.status == StaffAttendance.Status.ON_LEAVE:
                skipped_count += 1
                continue

            # Preserve manual override or punched records unless overwrite_existing is True
            if (existing.is_manual_override or existing.check_in is not None) and not overwrite_existing:
                skipped_count += 1
                continue

            if overwrite_existing or (existing.check_in is None and not existing.is_manual_override):
                existing.status = status
                existing.shift_type = shift_type
                if notes.strip():
                    existing.notes = (existing.notes + "\n" + notes.strip()).strip() if existing.notes else notes.strip()
                existing.marked_by = actor
                existing.save()
                updated_count += 1
            else:
                skipped_count += 1
        else:
            StaffAttendance.objects.create(
                organization=organization,
                staff=staff,
                date=date,
                status=status,
                shift_type=shift_type,
                notes=notes.strip(),
                marked_by=actor,
            )
            created_count += 1

    record_audit_log(
        organization=organization,
        actor=actor,
        action="STAFF_ATTENDANCE_BULK_MARKED",
        resource_type="StaffAttendance",
        resource_id="",
        metadata={
            "date": str(date),
            "status": status,
            "shift_type": shift_type,
            "total_staff": len(staff_list),
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
        },
    )

    return {
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total": len(staff_list),
    }


# ==============================================================================
# 5. LEAVE REQUEST CREATION
# ==============================================================================

@transaction.atomic
def create_leave_request(
    *,
    organization: Organization,
    actor: User,
    staff: StaffProfile,
    leave_type: str,
    start_date: date,
    end_date: date,
    reason: str,
    total_days: Decimal | float | int | None = None,
) -> StaffLeaveRequest:
    """
    Submits a staff leave request, validating date range, duration, and preventing overlapping leaves.
    """
    if not organization.is_active:
        raise HRDomainError("Organization is not active.")

    if staff.organization_id != organization.id:
        raise HRDomainError("Staff profile does not belong to this organization.")

    if staff.status != StaffProfile.Status.ACTIVE:
        raise HRDomainError(f"Staff member is {staff.status} and cannot submit leave requests.")

    # Self leave request or Manager/Admin/Owner authorization
    if actor.id != staff.user_id and not _can_manage_hr(organization, actor):
        raise HRDomainError("Permission denied: You do not have permission to submit a leave request for this staff member.")

    if leave_type not in StaffLeaveRequest.LeaveType.values:
        raise HRDomainError(f"Invalid leave type: {leave_type}.")

    if end_date < start_date:
        raise HRDomainError("End date cannot be earlier than start date.")

    cleaned_reason = (reason or "").strip()
    if not cleaned_reason:
        raise HRDomainError("Leave reason is required.")

    if total_days is None:
        calc_days = (end_date - start_date).days + 1
        days_decimal = Decimal(str(calc_days))
    else:
        try:
            days_decimal = Decimal(str(total_days))
        except Exception as exc:
            raise HRDomainError(f"Invalid total_days value: {total_days}.") from exc

    if days_decimal <= Decimal("0"):
        raise HRDomainError("Total leave days must be greater than zero.")

    # Check for overlapping pending or approved leave requests
    overlap = StaffLeaveRequest.objects.for_organization(organization).filter(
        staff=staff,
        status__in=[
            StaffLeaveRequest.Status.PENDING,
            StaffLeaveRequest.Status.APPROVED,
        ],
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).first()

    if overlap:
        raise HRDomainError(
            f"Staff already has an overlapping {overlap.leave_type} leave request "
            f"({overlap.start_date} to {overlap.end_date}) in {overlap.status} status."
        )

    leave_request = StaffLeaveRequest.objects.create(
        organization=organization,
        staff=staff,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        total_days=days_decimal,
        reason=cleaned_reason,
        status=StaffLeaveRequest.Status.PENDING,
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="STAFF_LEAVE_REQUESTED",
        resource_type="StaffLeaveRequest",
        resource_id=str(leave_request.id),
        metadata={
            "staff_id": str(staff.id),
            "staff_code": staff.staff_code,
            "leave_type": leave_request.leave_type,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_days": str(leave_request.total_days),
        },
    )

    return leave_request


# ==============================================================================
# 6. LEAVE APPROVAL & REJECTION
# ==============================================================================

@transaction.atomic
def review_leave_request(
    *,
    organization: Organization,
    actor: User,
    leave_request: StaffLeaveRequest,
    action: str,
    review_notes: str = "",
) -> StaffLeaveRequest:
    """
    Approves or rejects a pending leave request with strict RBAC, separation of duties,
    and automatic attendance synchronization on approval.
    """
    if not organization.is_active:
        raise HRDomainError("Organization is not active.")

    if not _can_manage_hr(organization, actor):
        raise HRDomainError("Permission denied: Only Owners, Admins, or Managers can approve or reject leave requests.")

    if leave_request.organization_id != organization.id:
        raise HRDomainError("Leave request does not belong to this organization.")

    # Separation of duties: cannot approve/reject own leave request
    if leave_request.staff.user_id == actor.id:
        raise HRDomainError("Staff members cannot approve or reject their own leave requests.")

    if leave_request.status != StaffLeaveRequest.Status.PENDING:
        raise HRDomainError(
            f"Cannot review leave request in '{leave_request.status}' status. Only PENDING requests can be reviewed."
        )

    action_upper = action.strip().upper()
    if action_upper not in {"APPROVE", "REJECT"}:
        raise HRDomainError(f"Invalid review action: '{action}'. Must be 'APPROVE' or 'REJECT'.")

    now = timezone.now()
    cleaned_notes = (review_notes or "").strip()

    if action_upper == "APPROVE":
        leave_request.status = StaffLeaveRequest.Status.APPROVED
        leave_request.reviewed_by = actor
        leave_request.reviewed_at = now
        leave_request.review_notes = cleaned_notes
        leave_request.save()

        # Synchronize attendance to ON_LEAVE across the date span
        sync_approved_leave_attendance(
            organization=organization,
            leave_request=leave_request,
            actor=actor,
        )

        record_audit_log(
            organization=organization,
            actor=actor,
            action="STAFF_LEAVE_APPROVED",
            resource_type="StaffLeaveRequest",
            resource_id=str(leave_request.id),
            metadata={
                "staff_id": str(leave_request.staff_id),
                "staff_code": leave_request.staff.staff_code,
                "leave_type": leave_request.leave_type,
                "start_date": str(leave_request.start_date),
                "end_date": str(leave_request.end_date),
                "total_days": str(leave_request.total_days),
                "review_notes": cleaned_notes,
            },
        )
    else:
        leave_request.status = StaffLeaveRequest.Status.REJECTED
        leave_request.reviewed_by = actor
        leave_request.reviewed_at = now
        leave_request.review_notes = cleaned_notes
        leave_request.save()

        record_audit_log(
            organization=organization,
            actor=actor,
            action="STAFF_LEAVE_REJECTED",
            resource_type="StaffLeaveRequest",
            resource_id=str(leave_request.id),
            metadata={
                "staff_id": str(leave_request.staff_id),
                "staff_code": leave_request.staff.staff_code,
                "leave_type": leave_request.leave_type,
                "start_date": str(leave_request.start_date),
                "end_date": str(leave_request.end_date),
                "review_notes": cleaned_notes,
            },
        )

    return leave_request


def approve_leave_request(
    *,
    organization: Organization,
    actor: User,
    leave_request: StaffLeaveRequest,
    review_notes: str = "",
) -> StaffLeaveRequest:
    """Convenience helper to approve a leave request."""
    return review_leave_request(
        organization=organization,
        actor=actor,
        leave_request=leave_request,
        action="APPROVE",
        review_notes=review_notes,
    )


def reject_leave_request(
    *,
    organization: Organization,
    actor: User,
    leave_request: StaffLeaveRequest,
    review_notes: str = "",
) -> StaffLeaveRequest:
    """Convenience helper to reject a leave request."""
    return review_leave_request(
        organization=organization,
        actor=actor,
        leave_request=leave_request,
        action="REJECT",
        review_notes=review_notes,
    )


# ==============================================================================
# 7. APPROVED LEAVE → ON_LEAVE ATTENDANCE SYNCHRONIZATION
# ==============================================================================

@transaction.atomic
def sync_approved_leave_attendance(
    *,
    organization: Organization,
    leave_request: StaffLeaveRequest,
    actor: User | None = None,
) -> int:
    """
    Synchronizes attendance records for an approved leave request across all covered dates.
    Preserves manual override semantics while updating regular daily records to ON_LEAVE.
    """
    if leave_request.status != StaffLeaveRequest.Status.APPROVED:
        raise HRDomainError("Cannot sync attendance for a non-approved leave request.")

    if leave_request.organization_id != organization.id:
        raise HRDomainError("Leave request does not belong to this organization.")

    existing_records = {
        att.date: att
        for att in StaffAttendance.objects.for_organization(organization).filter(
            staff=leave_request.staff,
            date__gte=leave_request.start_date,
            date__lte=leave_request.end_date,
        )
    }

    synced_count = 0
    current_date = leave_request.start_date
    sync_user = actor or leave_request.reviewed_by

    while current_date <= leave_request.end_date:
        existing = existing_records.get(current_date)
        leave_note = f"Approved Leave ({leave_request.leave_type})"

        if existing:
            if existing.is_manual_override:
                # Keep manual override intact, append note if not already present
                if leave_note not in existing.notes:
                    existing.notes = (existing.notes + f" | {leave_note}").strip() if existing.notes else leave_note
                    existing.save(update_fields=["notes", "updated_at"])
            else:
                existing.status = StaffAttendance.Status.ON_LEAVE
                existing.notes = leave_note
                existing.marked_by = sync_user
                existing.save()
                synced_count += 1
        else:
            StaffAttendance.objects.create(
                organization=organization,
                staff=leave_request.staff,
                date=current_date,
                status=StaffAttendance.Status.ON_LEAVE,
                notes=leave_note,
                marked_by=sync_user,
            )
            synced_count += 1

        current_date += timedelta(days=1)

    record_audit_log(
        organization=organization,
        actor=sync_user,
        action="STAFF_LEAVE_ATTENDANCE_SYNCED",
        resource_type="StaffLeaveRequest",
        resource_id=str(leave_request.id),
        metadata={
            "staff_id": str(leave_request.staff_id),
            "staff_code": leave_request.staff.staff_code,
            "start_date": str(leave_request.start_date),
            "end_date": str(leave_request.end_date),
            "synced_days": synced_count,
        },
    )

    return synced_count


# ==============================================================================
# 8. DAILY ATTENDANCE SUMMARY
# ==============================================================================

def get_daily_attendance_summary(
    *,
    organization: Organization,
    target_date: date | None = None,
    department: str | None = None,
) -> dict[str, Any]:
    """
    Returns an efficient, queryset-based daily attendance summary with deterministic ordering.
    """
    if target_date is None:
        target_date = _get_local_datetime(organization).date()

    staff_qs = StaffProfile.objects.filter(
        organization=organization,
        status=StaffProfile.Status.ACTIVE,
    ).select_related("user")

    if department and department.strip():
        staff_qs = staff_qs.filter(department__iexact=department.strip())

    staff_list = list(staff_qs.order_by("staff_code"))

    att_qs = StaffAttendance.objects.for_organization(organization).filter(
        date=target_date,
        staff__in=staff_list,
    ).select_related("staff", "staff__user", "marked_by")

    att_map = {att.staff_id: att for att in att_qs}

    present_count = 0
    late_count = 0
    half_day_count = 0
    on_leave_count = 0
    holiday_count = 0
    absent_count = 0
    unmarked_count = 0
    total_late_minutes = 0
    total_overtime_minutes = 0

    records = []
    for staff in staff_list:
        att = att_map.get(staff.id)
        if att:
            if att.status == StaffAttendance.Status.PRESENT:
                present_count += 1
            elif att.status == StaffAttendance.Status.LATE:
                late_count += 1
            elif att.status == StaffAttendance.Status.HALF_DAY:
                half_day_count += 1
            elif att.status == StaffAttendance.Status.ON_LEAVE:
                on_leave_count += 1
            elif att.status == StaffAttendance.Status.HOLIDAY:
                holiday_count += 1
            elif att.status == StaffAttendance.Status.ABSENT:
                absent_count += 1

            total_late_minutes += att.late_minutes
            total_overtime_minutes += att.overtime_minutes

            records.append({
                "staff_id": str(staff.id),
                "staff_code": staff.staff_code,
                "full_name": staff.user.get_full_name() or staff.user.email,
                "email": staff.user.email,
                "department": staff.department,
                "designation": staff.designation,
                "role": staff.role,
                "status": att.status,
                "check_in": str(att.check_in) if att.check_in else None,
                "check_out": str(att.check_out) if att.check_out else None,
                "late_minutes": att.late_minutes,
                "overtime_minutes": att.overtime_minutes,
                "shift_type": att.shift_type,
                "is_manual_override": att.is_manual_override,
                "is_excused": att.is_excused,
                "marked_by": att.marked_by.email if att.marked_by else None,
                "notes": att.notes,
            })
        else:
            unmarked_count += 1
            records.append({
                "staff_id": str(staff.id),
                "staff_code": staff.staff_code,
                "full_name": staff.user.get_full_name() or staff.user.email,
                "email": staff.user.email,
                "department": staff.department,
                "designation": staff.designation,
                "role": staff.role,
                "status": "UNMARKED",
                "check_in": None,
                "check_out": None,
                "late_minutes": 0,
                "overtime_minutes": 0,
                "shift_type": None,
                "is_manual_override": False,
                "is_excused": False,
                "marked_by": None,
                "notes": "",
            })

    return {
        "date": str(target_date),
        "department": department.strip() if department else None,
        "total_active_staff": len(staff_list),
        "present_count": present_count,
        "late_count": late_count,
        "half_day_count": half_day_count,
        "on_leave_count": on_leave_count,
        "holiday_count": holiday_count,
        "absent_count": absent_count,
        "unmarked_count": unmarked_count,
        "total_late_minutes": total_late_minutes,
        "total_overtime_minutes": total_overtime_minutes,
        "records": records,
    }


# ==============================================================================
# 9. MONTHLY ATTENDANCE MATRIX
# ==============================================================================

def get_monthly_attendance_matrix(
    *,
    organization: Organization,
    year: int,
    month: int,
    department: str | None = None,
) -> dict[str, Any]:
    """
    Computes a monthly attendance matrix per staff member without N+1 queries.
    """
    if not (1900 <= year <= 2100):
        raise HRDomainError(f"Invalid year: {year}.")

    if not (1 <= month <= 12):
        raise HRDomainError(f"Invalid month: {month}. Must be between 1 and 12.")

    _, total_days = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, total_days)

    staff_qs = StaffProfile.objects.filter(
        organization=organization,
        status=StaffProfile.Status.ACTIVE,
    ).select_related("user")

    if department and department.strip():
        staff_qs = staff_qs.filter(department__iexact=department.strip())

    staff_list = list(staff_qs.order_by("staff_code"))

    att_qs = StaffAttendance.objects.for_organization(organization).filter(
        date__gte=start_date,
        date__lte=end_date,
        staff__in=staff_list,
    )

    # Group by staff_id -> day -> att
    att_by_staff_and_day: dict[UUID, dict[int, StaffAttendance]] = {}
    for att in att_qs:
        att_by_staff_and_day.setdefault(att.staff_id, {})[att.date.day] = att

    matrix_rows = []
    for staff in staff_list:
        staff_records = att_by_staff_and_day.get(staff.id, {})
        daily_attendance: dict[int, dict[str, Any]] = {}

        present_cnt = 0
        late_cnt = 0
        half_day_cnt = 0
        on_leave_cnt = 0
        holiday_cnt = 0
        absent_cnt = 0
        unmarked_cnt = 0
        total_late = 0
        total_overtime = 0

        for day in range(1, total_days + 1):
            att = staff_records.get(day)
            if att:
                daily_attendance[day] = {
                    "status": att.status,
                    "check_in": str(att.check_in) if att.check_in else None,
                    "check_out": str(att.check_out) if att.check_out else None,
                    "late_minutes": att.late_minutes,
                    "overtime_minutes": att.overtime_minutes,
                    "is_manual_override": att.is_manual_override,
                }
                if att.status == StaffAttendance.Status.PRESENT:
                    present_cnt += 1
                elif att.status == StaffAttendance.Status.LATE:
                    late_cnt += 1
                elif att.status == StaffAttendance.Status.HALF_DAY:
                    half_day_cnt += 1
                elif att.status == StaffAttendance.Status.ON_LEAVE:
                    on_leave_cnt += 1
                elif att.status == StaffAttendance.Status.HOLIDAY:
                    holiday_cnt += 1
                elif att.status == StaffAttendance.Status.ABSENT:
                    absent_cnt += 1

                total_late += att.late_minutes
                total_overtime += att.overtime_minutes
            else:
                daily_attendance[day] = {
                    "status": None,
                    "check_in": None,
                    "check_out": None,
                    "late_minutes": 0,
                    "overtime_minutes": 0,
                    "is_manual_override": False,
                }
                unmarked_cnt += 1

        matrix_rows.append({
            "staff_id": str(staff.id),
            "staff_code": staff.staff_code,
            "full_name": staff.user.get_full_name() or staff.user.email,
            "department": staff.department,
            "designation": staff.designation,
            "role": staff.role,
            "daily_attendance": daily_attendance,
            "summary": {
                "present": present_cnt,
                "late": late_cnt,
                "half_day": half_day_cnt,
                "on_leave": on_leave_cnt,
                "holiday": holiday_cnt,
                "absent": absent_cnt,
                "unmarked": unmarked_cnt,
                "total_late_minutes": total_late,
                "total_overtime_minutes": total_overtime,
            },
        })

    return {
        "year": year,
        "month": month,
        "total_days": total_days,
        "department": department.strip() if department else None,
        "total_staff": len(staff_list),
        "matrix": matrix_rows,
    }
