from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from hr.attendance_services import (
    HRDomainError,
    approve_leave_request,
    bulk_mark_attendance,
    calculate_late_minutes,
    calculate_overtime_minutes,
    check_in_staff,
    check_out_staff,
    create_leave_request,
    get_daily_attendance_summary,
    get_monthly_attendance_matrix,
    override_attendance,
    reject_leave_request,
    review_leave_request,
    sync_approved_leave_attendance,
)
from hr.models import StaffAttendance, StaffLeaveRequest
from tenancy.models import AuditLog, Organization, OrganizationMembership, StaffProfile

User = get_user_model()


class AttendanceServicesTestCase(TestCase):
    def setUp(self):
        # Organization A
        self.org_a = Organization.objects.create(
            name="Alpha Fiber Corp",
            code="ALPHA",
            timezone="Asia/Karachi",
            is_active=True,
        )

        # Organization B (for isolation tests)
        self.org_b = Organization.objects.create(
            name="Beta Networks",
            code="BETA",
            timezone="Asia/Karachi",
            is_active=True,
        )

        # Owner Org A
        self.user_owner = User.objects.create_user(
            username="owner@alpha.test",
            email="owner@alpha.test",
            password="Password123!",
            first_name="Alpha",
            last_name="Owner",
        )
        self.membership_owner = OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        self.profile_owner = StaffProfile.objects.create(
            organization=self.org_a,
            membership=self.membership_owner,
            user=self.user_owner,
            staff_code="ALPHA-OWN-0001",
            role=StaffProfile.Role.OWNER,
            status=StaffProfile.Status.ACTIVE,
        )

        # Manager Org A
        self.user_manager = User.objects.create_user(
            username="manager@alpha.test",
            email="manager@alpha.test",
            password="Password123!",
            first_name="Majid",
            last_name="Manager",
        )
        self.membership_manager = OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_manager,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.profile_manager = StaffProfile.objects.create(
            organization=self.org_a,
            membership=self.membership_manager,
            user=self.user_manager,
            staff_code="ALPHA-MGR-0001",
            role=StaffProfile.Role.MANAGER,
            department="Operations",
            status=StaffProfile.Status.ACTIVE,
        )

        # Staff 1 Org A (Field Tech)
        self.user_staff1 = User.objects.create_user(
            username="staff1@alpha.test",
            email="staff1@alpha.test",
            password="Password123!",
            first_name="Tariq",
            last_name="Tech",
        )
        self.membership_staff1 = OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_staff1,
            role=OrganizationMembership.Role.TECHNICIAN,
            is_active=True,
        )
        self.profile_staff1 = StaffProfile.objects.create(
            organization=self.org_a,
            membership=self.membership_staff1,
            user=self.user_staff1,
            staff_code="ALPHA-STF-0001",
            role=StaffProfile.Role.TECHNICIAN,
            department="Operations",
            designation="Field Tech",
            status=StaffProfile.Status.ACTIVE,
        )

        # Staff 2 Org A (Customer Support)
        self.user_staff2 = User.objects.create_user(
            username="staff2@alpha.test",
            email="staff2@alpha.test",
            password="Password123!",
            first_name="Sara",
            last_name="Support",
        )
        self.membership_staff2 = OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_staff2,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.profile_staff2 = StaffProfile.objects.create(
            organization=self.org_a,
            membership=self.membership_staff2,
            user=self.user_staff2,
            staff_code="ALPHA-STF-0002",
            role=StaffProfile.Role.SUPPORT_OFFICER,
            department="Support",
            designation="Support Officer",
            status=StaffProfile.Status.ACTIVE,
        )

        # Staff Org B
        self.user_b = User.objects.create_user(
            username="staff_b@beta.test",
            email="staff_b@beta.test",
            password="Password123!",
            first_name="Bilal",
            last_name="Beta",
        )
        self.membership_b = OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.profile_b = StaffProfile.objects.create(
            organization=self.org_b,
            membership=self.membership_b,
            user=self.user_b,
            staff_code="BETA-STF-0001",
            role=StaffProfile.Role.STAFF,
            status=StaffProfile.Status.ACTIVE,
        )

    # --------------------------------------------------------------------------
    # CHECK-IN & LATE CALCULATION TESTS
    # --------------------------------------------------------------------------

    def test_self_check_in_on_time(self):
        # 08:50 AM check-in for REGULAR (09:00 AM start, 15 min grace)
        tz = ZoneInfo("Asia/Karachi")
        punch_dt = datetime(2026, 9, 16, 8, 50, 0, tzinfo=tz)

        att = check_in_staff(
            organization=self.org_a,
            staff=self.profile_staff1,
            actor=self.user_staff1,
            timestamp=punch_dt,
            shift_type=StaffAttendance.ShiftType.REGULAR,
            notes="On time punch",
        )

        self.assertEqual(att.status, StaffAttendance.Status.PRESENT)
        self.assertEqual(att.late_minutes, 0)
        self.assertEqual(att.check_in, time(8, 50, 0))
        self.assertEqual(att.date, date(2026, 9, 16))

        # Check Audit Log
        audit = AuditLog.objects.filter(
            organization=self.org_a,
            action="STAFF_ATTENDANCE_CHECK_IN",
            resource_id=str(att.id),
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.user_staff1)
        self.assertEqual(audit.metadata["status"], StaffAttendance.Status.PRESENT)

    def test_self_check_in_within_grace_period(self):
        # 09:12 AM check-in for REGULAR (within 15 min grace period)
        tz = ZoneInfo("Asia/Karachi")
        punch_dt = datetime(2026, 9, 16, 9, 12, 0, tzinfo=tz)

        att = check_in_staff(
            organization=self.org_a,
            staff=self.profile_staff1,
            actor=self.user_staff1,
            timestamp=punch_dt,
            shift_type=StaffAttendance.ShiftType.REGULAR,
        )

        self.assertEqual(att.status, StaffAttendance.Status.PRESENT)
        self.assertEqual(att.late_minutes, 0)

    def test_self_check_in_late(self):
        # 09:35 AM check-in for REGULAR (35 minutes after 09:00 AM)
        tz = ZoneInfo("Asia/Karachi")
        punch_dt = datetime(2026, 9, 16, 9, 35, 0, tzinfo=tz)

        att = check_in_staff(
            organization=self.org_a,
            staff=self.profile_staff1,
            actor=self.user_staff1,
            timestamp=punch_dt,
            shift_type=StaffAttendance.ShiftType.REGULAR,
        )

        self.assertEqual(att.status, StaffAttendance.Status.LATE)
        self.assertEqual(att.late_minutes, 35)

    def test_duplicate_check_in_prevented(self):
        tz = ZoneInfo("Asia/Karachi")
        punch_dt = datetime(2026, 9, 16, 9, 0, 0, tzinfo=tz)

        check_in_staff(
            organization=self.org_a,
            staff=self.profile_staff1,
            actor=self.user_staff1,
            timestamp=punch_dt,
        )

        # Attempting check-in again on same date must raise HRDomainError
        with self.assertRaises(HRDomainError) as ctx:
            check_in_staff(
                organization=self.org_a,
                staff=self.profile_staff1,
                actor=self.user_staff1,
                timestamp=punch_dt + timedelta(minutes=10),
            )
        self.assertIn("already checked in", str(ctx.exception))

    def test_check_in_when_on_leave_or_holiday_prevented(self):
        target_date = date(2026, 9, 16)
        # Pre-existing ON_LEAVE record
        StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            date=target_date,
            status=StaffAttendance.Status.ON_LEAVE,
        )

        tz = ZoneInfo("Asia/Karachi")
        punch_dt = datetime(2026, 9, 16, 9, 0, 0, tzinfo=tz)

        with self.assertRaises(HRDomainError) as ctx:
            check_in_staff(
                organization=self.org_a,
                staff=self.profile_staff1,
                actor=self.user_staff1,
                timestamp=punch_dt,
            )
        self.assertIn("approved leave", str(ctx.exception))

    def test_check_in_inactive_staff_prevented(self):
        self.profile_staff1.status = StaffProfile.Status.SUSPENDED
        self.profile_staff1.save()

        tz = ZoneInfo("Asia/Karachi")
        punch_dt = datetime(2026, 9, 16, 9, 0, 0, tzinfo=tz)

        with self.assertRaises(HRDomainError) as ctx:
            check_in_staff(
                organization=self.org_a,
                staff=self.profile_staff1,
                actor=self.user_staff1,
                timestamp=punch_dt,
            )
        self.assertIn("cannot check in", str(ctx.exception))

    # --------------------------------------------------------------------------
    # CHECK-OUT & OVERTIME TESTS
    # --------------------------------------------------------------------------

    def test_check_out_success_and_overtime_calculation(self):
        tz = ZoneInfo("Asia/Karachi")
        check_in_dt = datetime(2026, 9, 16, 8, 55, 0, tzinfo=tz)
        check_out_dt = datetime(2026, 9, 16, 19, 30, 0, tzinfo=tz)  # 1.5h past 18:00 -> 90 mins overtime

        att = check_in_staff(
            organization=self.org_a,
            staff=self.profile_staff1,
            actor=self.user_staff1,
            timestamp=check_in_dt,
            shift_type=StaffAttendance.ShiftType.REGULAR,
        )

        updated_att = check_out_staff(
            organization=self.org_a,
            staff=self.profile_staff1,
            actor=self.user_staff1,
            timestamp=check_out_dt,
            notes="Completed extra tickets",
        )

        self.assertEqual(updated_att.check_out, time(19, 30, 0))
        self.assertEqual(updated_att.overtime_minutes, 90)
        self.assertIn("Completed extra tickets", updated_att.notes)

        # Verify audit log
        audit = AuditLog.objects.filter(
            organization=self.org_a,
            action="STAFF_ATTENDANCE_CHECK_OUT",
            resource_id=str(updated_att.id),
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata["overtime_minutes"], 90)

    def test_check_out_without_check_in_fails(self):
        tz = ZoneInfo("Asia/Karachi")
        check_out_dt = datetime(2026, 9, 16, 18, 0, 0, tzinfo=tz)

        with self.assertRaises(HRDomainError) as ctx:
            check_out_staff(
                organization=self.org_a,
                staff=self.profile_staff1,
                actor=self.user_staff1,
                timestamp=check_out_dt,
            )
        self.assertIn("No attendance record found", str(ctx.exception))

    def test_check_out_before_check_in_time_fails(self):
        tz = ZoneInfo("Asia/Karachi")
        check_in_dt = datetime(2026, 9, 16, 14, 0, 0, tzinfo=tz)
        invalid_out_dt = datetime(2026, 9, 16, 10, 0, 0, tzinfo=tz)

        check_in_staff(
            organization=self.org_a,
            staff=self.profile_staff1,
            actor=self.user_staff1,
            timestamp=check_in_dt,
        )

        with self.assertRaises(HRDomainError) as ctx:
            check_out_staff(
                organization=self.org_a,
                staff=self.profile_staff1,
                actor=self.user_staff1,
                timestamp=invalid_out_dt,
            )
        self.assertIn("earlier than check-in time", str(ctx.exception))

    def test_duplicate_check_out_fails(self):
        tz = ZoneInfo("Asia/Karachi")
        check_in_dt = datetime(2026, 9, 16, 9, 0, 0, tzinfo=tz)
        check_out_dt = datetime(2026, 9, 16, 18, 0, 0, tzinfo=tz)

        check_in_staff(
            organization=self.org_a,
            staff=self.profile_staff1,
            actor=self.user_staff1,
            timestamp=check_in_dt,
        )
        check_out_staff(
            organization=self.org_a,
            staff=self.profile_staff1,
            actor=self.user_staff1,
            timestamp=check_out_dt,
        )

        with self.assertRaises(HRDomainError) as ctx:
            check_out_staff(
                organization=self.org_a,
                staff=self.profile_staff1,
                actor=self.user_staff1,
                timestamp=check_out_dt + timedelta(minutes=30),
            )
        self.assertIn("already checked out", str(ctx.exception))

    # --------------------------------------------------------------------------
    # MANUAL OVERRIDE & AUDIT TESTS
    # --------------------------------------------------------------------------

    def test_manual_override_success_and_audit(self):
        target_date = date(2026, 9, 15)

        # Initial regular record
        att = StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            date=target_date,
            status=StaffAttendance.Status.ABSENT,
        )

        # Manager overrides to PRESENT with custom punch times
        overridden = override_attendance(
            organization=self.org_a,
            actor=self.user_manager,
            staff=self.profile_staff1,
            date=target_date,
            override_reason="Biometric device was offline; confirmed manual punch sheet",
            status=StaffAttendance.Status.PRESENT,
            check_in=time(9, 0),
            check_out=time(18, 0),
            late_minutes=0,
            overtime_minutes=0,
        )

        self.assertTrue(overridden.is_manual_override)
        self.assertEqual(overridden.status, StaffAttendance.Status.PRESENT)
        self.assertEqual(overridden.marked_by, self.user_manager)
        self.assertEqual(
            overridden.override_reason,
            "Biometric device was offline; confirmed manual punch sheet",
        )

        # Verify audit log captures before and after state
        audit = AuditLog.objects.filter(
            organization=self.org_a,
            action="STAFF_ATTENDANCE_OVERRIDE",
            resource_id=str(overridden.id),
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata["before_state"]["status"], StaffAttendance.Status.ABSENT)
        self.assertEqual(audit.metadata["after_state"]["status"], StaffAttendance.Status.PRESENT)
        self.assertEqual(audit.metadata["after_state"]["is_manual_override"], True)

    def test_manual_override_empty_reason_fails(self):
        with self.assertRaises(HRDomainError) as ctx:
            override_attendance(
                organization=self.org_a,
                actor=self.user_manager,
                staff=self.profile_staff1,
                date=date(2026, 9, 15),
                override_reason="   ",
            )
        self.assertIn("Override reason is mandatory", str(ctx.exception))

    def test_manual_override_rbac_enforcement(self):
        # Regular staff member trying to override attendance
        with self.assertRaises(HRDomainError) as ctx:
            override_attendance(
                organization=self.org_a,
                actor=self.user_staff2,
                staff=self.profile_staff1,
                date=date(2026, 9, 15),
                override_reason="Tampering attempt",
                status=StaffAttendance.Status.PRESENT,
            )
        self.assertIn("Permission denied", str(ctx.exception))

    # --------------------------------------------------------------------------
    # BULK MARKING TESTS
    # --------------------------------------------------------------------------

    def test_bulk_mark_attendance_safely(self):
        target_date = date(2026, 9, 10)

        # Pre-condition: staff1 has an approved leave, staff2 has no record
        StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            date=target_date,
            status=StaffAttendance.Status.ON_LEAVE,
        )

        res = bulk_mark_attendance(
            organization=self.org_a,
            actor=self.user_manager,
            date=target_date,
            status=StaffAttendance.Status.PRESENT,
            notes="Company-wide field day",
        )

        # Staff 1 (ON_LEAVE) should be skipped, Staff 2 and Owner/Manager created
        self.assertGreaterEqual(res["created"], 1)
        self.assertEqual(res["skipped"], 1)

        # Verify Staff 1 is still ON_LEAVE
        staff1_att = StaffAttendance.objects.get(
            organization=self.org_a,
            staff=self.profile_staff1,
            date=target_date,
        )
        self.assertEqual(staff1_att.status, StaffAttendance.Status.ON_LEAVE)

        # Verify audit log
        audit = AuditLog.objects.filter(
            organization=self.org_a,
            action="STAFF_ATTENDANCE_BULK_MARKED",
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata["status"], StaffAttendance.Status.PRESENT)

    def test_bulk_mark_attendance_rbac(self):
        with self.assertRaises(HRDomainError) as ctx:
            bulk_mark_attendance(
                organization=self.org_a,
                actor=self.user_staff1,
                date=date(2026, 9, 10),
                status=StaffAttendance.Status.PRESENT,
            )
        self.assertIn("Permission denied", str(ctx.exception))

    # --------------------------------------------------------------------------
    # LEAVE REQUEST, APPROVAL, REJECTION & SYNC TESTS
    # --------------------------------------------------------------------------

    def test_create_leave_request_and_audit(self):
        start = date(2026, 9, 20)
        end = date(2026, 9, 22)

        leave_req = create_leave_request(
            organization=self.org_a,
            actor=self.user_staff1,
            staff=self.profile_staff1,
            leave_type=StaffLeaveRequest.LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Family gathering",
        )

        self.assertEqual(leave_req.status, StaffLeaveRequest.Status.PENDING)
        self.assertEqual(leave_req.total_days, Decimal("3"))
        self.assertEqual(leave_req.staff, self.profile_staff1)

        audit = AuditLog.objects.filter(
            organization=self.org_a,
            action="STAFF_LEAVE_REQUESTED",
            resource_id=str(leave_req.id),
        ).first()
        self.assertIsNotNone(audit)

    def test_overlapping_leave_request_prevented(self):
        start = date(2026, 9, 20)
        end = date(2026, 9, 22)

        create_leave_request(
            organization=self.org_a,
            actor=self.user_staff1,
            staff=self.profile_staff1,
            leave_type=StaffLeaveRequest.LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Family gathering",
        )

        # Overlapping start date
        with self.assertRaises(HRDomainError) as ctx:
            create_leave_request(
                organization=self.org_a,
                actor=self.user_staff1,
                staff=self.profile_staff1,
                leave_type=StaffLeaveRequest.LeaveType.SICK,
                start_date=date(2026, 9, 21),
                end_date=date(2026, 9, 25),
                reason="Medical emergency",
            )
        self.assertIn("overlapping", str(ctx.exception).lower())

    def test_leave_approval_and_attendance_synchronization(self):
        start = date(2026, 9, 20)
        end = date(2026, 9, 22)

        leave_req = create_leave_request(
            organization=self.org_a,
            actor=self.user_staff1,
            staff=self.profile_staff1,
            leave_type=StaffLeaveRequest.LeaveType.ANNUAL,
            start_date=start,
            end_date=end,
            reason="Annual trip",
        )

        # Manager approves
        approved_req = approve_leave_request(
            organization=self.org_a,
            actor=self.user_manager,
            leave_request=leave_req,
            review_notes="Approved with full balance",
        )

        self.assertEqual(approved_req.status, StaffLeaveRequest.Status.APPROVED)
        self.assertEqual(approved_req.reviewed_by, self.user_manager)
        self.assertIsNotNone(approved_req.reviewed_at)

        # Verify synchronized attendance for all 3 days
        attendances = StaffAttendance.objects.filter(
            organization=self.org_a,
            staff=self.profile_staff1,
            date__gte=start,
            date__lte=end,
        ).order_by("date")

        self.assertEqual(attendances.count(), 3)
        for att in attendances:
            self.assertEqual(att.status, StaffAttendance.Status.ON_LEAVE)
            self.assertIn("Approved Leave (ANNUAL)", att.notes)

        # Verify audit logs
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.org_a,
                action="STAFF_LEAVE_APPROVED",
                resource_id=str(approved_req.id),
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.org_a,
                action="STAFF_LEAVE_ATTENDANCE_SYNCED",
                resource_id=str(approved_req.id),
            ).exists()
        )

    def test_leave_rejection(self):
        start = date(2026, 9, 20)
        end = date(2026, 9, 21)

        leave_req = create_leave_request(
            organization=self.org_a,
            actor=self.user_staff1,
            staff=self.profile_staff1,
            leave_type=StaffLeaveRequest.LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Casual leave",
        )

        rejected_req = reject_leave_request(
            organization=self.org_a,
            actor=self.user_manager,
            leave_request=leave_req,
            review_notes="Insufficient team coverage during fiber rollout",
        )

        self.assertEqual(rejected_req.status, StaffLeaveRequest.Status.REJECTED)

        # Attendance must NOT be created
        att_count = StaffAttendance.objects.filter(
            organization=self.org_a,
            staff=self.profile_staff1,
            date__gte=start,
            date__lte=end,
        ).count()
        self.assertEqual(att_count, 0)

    def test_leave_approval_separation_of_duties(self):
        # Manager requests leave for themselves
        mgr_leave = create_leave_request(
            organization=self.org_a,
            actor=self.user_manager,
            staff=self.profile_manager,
            leave_type=StaffLeaveRequest.LeaveType.CASUAL,
            start_date=date(2026, 9, 25),
            end_date=date(2026, 9, 26),
            reason="Personal work",
        )

        # Manager cannot approve their own leave
        with self.assertRaises(HRDomainError) as ctx:
            approve_leave_request(
                organization=self.org_a,
                actor=self.user_manager,
                leave_request=mgr_leave,
            )
        self.assertIn("cannot approve or reject their own", str(ctx.exception))

        # Owner CAN approve manager's leave
        approved = approve_leave_request(
            organization=self.org_a,
            actor=self.user_owner,
            leave_request=mgr_leave,
            review_notes="Approved by owner",
        )
        self.assertEqual(approved.status, StaffLeaveRequest.Status.APPROVED)

    def test_approved_leave_sync_preserves_manual_override(self):
        override_date = date(2026, 9, 20)
        override_att = StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            date=override_date,
            status=StaffAttendance.Status.PRESENT,
            is_manual_override=True,
            override_reason="Special on-duty field inspection override",
        )

        leave_req = StaffLeaveRequest.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            leave_type=StaffLeaveRequest.LeaveType.CASUAL,
            start_date=date(2026, 9, 20),
            end_date=date(2026, 9, 21),
            total_days=Decimal("2"),
            reason="Urgent leave",
            status=StaffLeaveRequest.Status.APPROVED,
            reviewed_by=self.user_manager,
        )

        sync_approved_leave_attendance(
            organization=self.org_a,
            leave_request=leave_req,
            actor=self.user_manager,
        )

        override_att.refresh_from_db()
        # Status remains PRESENT due to manual override, note appended
        self.assertEqual(override_att.status, StaffAttendance.Status.PRESENT)
        self.assertTrue(override_att.is_manual_override)
        self.assertIn("Approved Leave (CASUAL)", override_att.notes)

    # --------------------------------------------------------------------------
    # SUMMARY & MATRIX TESTS
    # --------------------------------------------------------------------------

    def test_daily_attendance_summary(self):
        target_date = date(2026, 9, 16)

        # Staff 1: Present
        StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            date=target_date,
            status=StaffAttendance.Status.PRESENT,
            check_in=time(9, 0),
            check_out=time(18, 0),
        )

        # Staff 2: Late
        StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.profile_staff2,
            date=target_date,
            status=StaffAttendance.Status.LATE,
            check_in=time(9, 45),
            late_minutes=45,
        )

        summary = get_daily_attendance_summary(
            organization=self.org_a,
            target_date=target_date,
        )

        self.assertEqual(summary["date"], str(target_date))
        self.assertEqual(summary["present_count"], 1)
        self.assertEqual(summary["late_count"], 1)
        self.assertEqual(summary["total_late_minutes"], 45)
        self.assertGreaterEqual(summary["total_active_staff"], 4)

        # Test department filtering
        dept_summary = get_daily_attendance_summary(
            organization=self.org_a,
            target_date=target_date,
            department="Support",
        )
        self.assertEqual(dept_summary["total_active_staff"], 1)
        self.assertEqual(dept_summary["late_count"], 1)
        self.assertEqual(dept_summary["records"][0]["staff_code"], "ALPHA-STF-0002")

    def test_monthly_attendance_matrix(self):
        # Create records across different days of Sept 2026
        StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            date=date(2026, 9, 1),
            status=StaffAttendance.Status.PRESENT,
            check_in=time(9, 0),
            check_out=time(18, 0),
        )
        StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            date=date(2026, 9, 2),
            status=StaffAttendance.Status.LATE,
            check_in=time(9, 30),
            late_minutes=30,
        )

        matrix = get_monthly_attendance_matrix(
            organization=self.org_a,
            year=2026,
            month=9,
        )

        self.assertEqual(matrix["year"], 2026)
        self.assertEqual(matrix["month"], 9)
        self.assertEqual(matrix["total_days"], 30)

        staff1_row = next(
            r for r in matrix["matrix"] if r["staff_code"] == "ALPHA-STF-0001"
        )
        self.assertEqual(staff1_row["daily_attendance"][1]["status"], "PRESENT")
        self.assertEqual(staff1_row["daily_attendance"][2]["status"], "LATE")
        self.assertIsNone(staff1_row["daily_attendance"][3]["status"])
        self.assertEqual(staff1_row["summary"]["present"], 1)
        self.assertEqual(staff1_row["summary"]["late"], 1)
        self.assertEqual(staff1_row["summary"]["total_late_minutes"], 30)

    # --------------------------------------------------------------------------
    # TENANT ISOLATION & RBAC TESTS
    # --------------------------------------------------------------------------

    def test_tenant_isolation_enforced(self):
        target_date = date(2026, 9, 16)
        # Attempting check-in for Staff B under Org A
        tz = ZoneInfo("Asia/Karachi")
        punch_dt = datetime(2026, 9, 16, 9, 0, 0, tzinfo=tz)

        with self.assertRaises(HRDomainError) as ctx:
            check_in_staff(
                organization=self.org_a,
                staff=self.profile_b,
                actor=self.user_owner,
                timestamp=punch_dt,
            )
        self.assertIn("does not belong to this organization", str(ctx.exception))

    def test_regular_staff_cannot_check_in_for_colleague(self):
        tz = ZoneInfo("Asia/Karachi")
        punch_dt = datetime(2026, 9, 16, 9, 0, 0, tzinfo=tz)

        # Staff 1 attempts to check in Staff 2
        with self.assertRaises(HRDomainError) as ctx:
            check_in_staff(
                organization=self.org_a,
                staff=self.profile_staff2,
                actor=self.user_staff1,
                timestamp=punch_dt,
            )
        self.assertIn("Permission denied", str(ctx.exception))
