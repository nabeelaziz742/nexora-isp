import uuid
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from hr.models import StaffAttendance, StaffLeaveRequest
from tenancy.models import Organization, OrganizationMembership, StaffProfile

User = get_user_model()


class StaffAttendanceModelTestCase(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(
            name="Alpha Fiber Corp",
            code="ALPHA",
        )
        self.org_b = Organization.objects.create(
            name="Beta Networks",
            code="BETA",
        )

        self.user_a = User.objects.create_user(
            username="tech_a@alpha.test",
            email="tech_a@alpha.test",
            password="Password123!",
            first_name="Ali",
            last_name="Khan",
        )
        self.membership_a = OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.staff_a = StaffProfile.objects.create(
            organization=self.org_a,
            membership=self.membership_a,
            user=self.user_a,
            staff_code="ALPHA-STF-0001",
            role=StaffProfile.Role.TECHNICIAN,
            status=StaffProfile.Status.ACTIVE,
        )

        self.user_b = User.objects.create_user(
            username="tech_b@beta.test",
            email="tech_b@beta.test",
            password="Password123!",
            first_name="Bilal",
            last_name="Ahmed",
        )
        self.membership_b = OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.staff_b = StaffProfile.objects.create(
            organization=self.org_b,
            membership=self.membership_b,
            user=self.user_b,
            staff_code="BETA-STF-0001",
            role=StaffProfile.Role.TECHNICIAN,
            status=StaffProfile.Status.ACTIVE,
        )

    def test_attendance_creation_and_fields(self):
        today = date.today()
        record = StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.staff_a,
            date=today,
            status=StaffAttendance.Status.PRESENT,
            check_in=time(9, 5, 0),
            check_out=time(18, 0, 0),
            shift_type=StaffAttendance.ShiftType.REGULAR,
            late_minutes=5,
            overtime_minutes=0,
            notes="Morning punch",
        )

        self.assertIsNotNone(record.id)
        self.assertEqual(record.status, StaffAttendance.Status.PRESENT)
        self.assertEqual(record.late_minutes, 5)
        self.assertEqual(str(record), f"ALPHA-STF-0001 | {today} | PRESENT")

    def test_duplicate_attendance_prevented(self):
        today = date.today()
        StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.staff_a,
            date=today,
            status=StaffAttendance.Status.PRESENT,
        )

        # Duplicate for same org, staff, and date must violate unique constraint
        with self.assertRaises(IntegrityError):
            StaffAttendance.objects.create(
                organization=self.org_a,
                staff=self.staff_a,
                date=today,
                status=StaffAttendance.Status.LATE,
            )

    def test_tenant_scoping_and_cross_tenant_independence(self):
        today = date.today()
        rec_a = StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.staff_a,
            date=today,
            status=StaffAttendance.Status.PRESENT,
        )
        rec_b = StaffAttendance.objects.create(
            organization=self.org_b,
            staff=self.staff_b,
            date=today,
            status=StaffAttendance.Status.PRESENT,
        )

        org_a_records = StaffAttendance.objects.for_organization(self.org_a)
        self.assertIn(rec_a, org_a_records)
        self.assertNotIn(rec_b, org_a_records)

    def test_clean_validation_enforces_same_organization(self):
        today = date.today()
        # staff_b belongs to org_b, but trying to assign under org_a
        mismatched = StaffAttendance(
            organization=self.org_a,
            staff=self.staff_b,
            date=today,
            status=StaffAttendance.Status.PRESENT,
        )
        with self.assertRaises(ValidationError):
            mismatched.clean()

    def test_manual_override_requires_reason(self):
        today = date.today()
        override_record = StaffAttendance(
            organization=self.org_a,
            staff=self.staff_a,
            date=today,
            status=StaffAttendance.Status.PRESENT,
            is_manual_override=True,
            override_reason="",  # Empty reason must fail validation
        )
        with self.assertRaises(ValidationError):
            override_record.clean()


class StaffLeaveRequestModelTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Alpha Fiber Corp",
            code="ALPHA",
        )
        self.user = User.objects.create_user(
            username="staff1@alpha.test",
            email="staff1@alpha.test",
            password="Password123!",
            first_name="Tariq",
            last_name="Mahmood",
        )
        self.membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.staff = StaffProfile.objects.create(
            organization=self.org,
            membership=self.membership,
            user=self.user,
            staff_code="ALPHA-STF-0002",
            role=StaffProfile.Role.STAFF,
            status=StaffProfile.Status.ACTIVE,
        )

    def test_leave_request_creation(self):
        start = date.today() + timedelta(days=2)
        end = date.today() + timedelta(days=4)
        leave = StaffLeaveRequest.objects.create(
            organization=self.org,
            staff=self.staff,
            leave_type=StaffLeaveRequest.LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            total_days=Decimal("3.0"),
            reason="Family commitment",
            status=StaffLeaveRequest.Status.PENDING,
        )

        self.assertIsNotNone(leave.id)
        self.assertEqual(leave.status, StaffLeaveRequest.Status.PENDING)
        self.assertEqual(leave.total_days, Decimal("3.0"))

    def test_leave_date_validation(self):
        start = date.today() + timedelta(days=5)
        end = date.today() + timedelta(days=2)  # End date before start date
        invalid_leave = StaffLeaveRequest(
            organization=self.org,
            staff=self.staff,
            leave_type=StaffLeaveRequest.LeaveType.SICK,
            start_date=start,
            end_date=end,
            total_days=Decimal("1.0"),
            reason="Sick leave",
        )
        with self.assertRaises(ValidationError):
            invalid_leave.clean()


class BackfillMissingStaffProfilesMigrationTestCase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Gamma Fiber",
            code="GAMMA",
        )
        self.owner = User.objects.create_user(
            username="owner@gamma.test",
            email="owner@gamma.test",
            password="Password123!",
        )
        self.owner_membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        self.inactive_user = User.objects.create_user(
            username="former@gamma.test",
            email="former@gamma.test",
            password="Password123!",
        )
        self.inactive_membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.inactive_user,
            role=OrganizationMembership.Role.TECHNICIAN,
            is_active=False,
        )
        existing_user = User.objects.create_user(
            username="staff@gamma.test",
            email="staff@gamma.test",
            password="Password123!",
        )
        existing_membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=existing_user,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.existing_profile = StaffProfile.objects.create(
            organization=self.organization,
            membership=existing_membership,
            user=existing_user,
            staff_code="GAMMA-STF-0001",
            role=StaffProfile.Role.MANAGER,
            status=StaffProfile.Status.ACTIVE,
        )

    def _run_backfill(self):
        from importlib import import_module

        from django.apps import apps

        migration = import_module("hr.migrations.0002_backfill_missing_staff_profiles")
        migration.backfill_missing_staff_profiles(apps, None)

    def test_creates_profiles_only_for_memberships_without_one(self):
        self._run_backfill()

        owner_profile = StaffProfile.objects.get(membership=self.owner_membership)
        self.assertEqual(owner_profile.role, StaffProfile.Role.OWNER)
        self.assertEqual(owner_profile.status, StaffProfile.Status.ACTIVE)

        inactive_profile = StaffProfile.objects.get(membership=self.inactive_membership)
        self.assertEqual(inactive_profile.role, StaffProfile.Role.TECHNICIAN)
        self.assertEqual(inactive_profile.status, StaffProfile.Status.INACTIVE)

        self.existing_profile.refresh_from_db()
        self.assertEqual(self.existing_profile.role, StaffProfile.Role.MANAGER)
        self.assertEqual(
            sorted(StaffProfile.objects.filter(organization=self.organization).values_list("staff_code", flat=True)),
            ["GAMMA-STF-0001", "GAMMA-STF-0002", "GAMMA-STF-0003"],
        )

    def test_is_idempotent(self):
        self._run_backfill()
        self._run_backfill()
        self.assertEqual(StaffProfile.objects.filter(organization=self.organization).count(), 3)
