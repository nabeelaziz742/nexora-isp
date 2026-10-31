from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from hr.models import StaffAttendance, StaffLeaveRequest
from tenancy.models import AuditLog, Organization, OrganizationMembership, StaffProfile

User = get_user_model()


class AttendanceAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Organization A
        self.org_a = Organization.objects.create(
            name="Alpha Fiber Corp",
            code="ALPHA",
            timezone="Asia/Karachi",
            is_active=True,
        )

        # Organization B (Tenant Isolation Testing)
        self.org_b = Organization.objects.create(
            name="Beta Networks",
            code="BETA",
            timezone="Asia/Karachi",
            is_active=True,
        )

        # 1. Owner Org A
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

        # 2. Manager Org A
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

        # 3. Staff 1 Org A (Field Tech)
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
            designation="Field Technician",
            status=StaffProfile.Status.ACTIVE,
        )

        # 4. Staff 2 Org A (Support Officer)
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

        # 5. Staff Org B
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

    def _get_auth_header(self, user: User, org: Organization) -> dict[str, str]:
        token = RefreshToken.for_user(user)
        token["organization_id"] = str(org.id)
        return {"HTTP_AUTHORIZATION": f"Bearer {str(token.access_token)}"}

    # --------------------------------------------------------------------------
    # 1. AUTHENTICATED SELF CHECK-IN
    # --------------------------------------------------------------------------

    def test_authenticated_self_check_in(self):
        auth_header = self._get_auth_header(self.user_staff1, self.org_a)
        payload = {
            "shift_type": "REGULAR",
            "notes": "Self punch from mobile",
            "location_coordinates": "31.5204,74.3587",
        }

        response = self.client.post(
            "/api/v1/hr/attendance/check-in/",
            payload,
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["staff"]["staff_code"], "ALPHA-STF-0001")
        self.assertIsNotNone(response.data["check_in"])
        self.assertEqual(response.data["location_coordinates"], "31.5204,74.3587")

        # Verify audit event
        audit = AuditLog.objects.filter(
            organization=self.org_a,
            action="STAFF_ATTENDANCE_CHECK_IN",
            actor=self.user_staff1,
        ).first()
        self.assertIsNotNone(audit)

    # --------------------------------------------------------------------------
    # 2. AUTHENTICATED SELF CHECK-OUT
    # --------------------------------------------------------------------------

    def test_authenticated_self_check_out(self):
        # First check in
        auth_header = self._get_auth_header(self.user_staff1, self.org_a)
        self.client.post(
            "/api/v1/hr/attendance/check-in/",
            {"shift_type": "REGULAR"},
            format="json",
            **auth_header,
        )

        # Now check out
        response = self.client.post(
            "/api/v1/hr/attendance/check-out/",
            {"notes": "Ending duty"},
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["check_out"])

        audit = AuditLog.objects.filter(
            organization=self.org_a,
            action="STAFF_ATTENDANCE_CHECK_OUT",
            actor=self.user_staff1,
        ).first()
        self.assertIsNotNone(audit)

    # --------------------------------------------------------------------------
    # 3. STAFF CANNOT CHECK IN ANOTHER STAFF MEMBER
    # --------------------------------------------------------------------------

    def test_staff_cannot_check_in_another_staff(self):
        auth_header = self._get_auth_header(self.user_staff1, self.org_a)
        payload = {
            "staff_id": str(self.profile_staff2.id),
            "shift_type": "REGULAR",
        }

        response = self.client.post(
            "/api/v1/hr/attendance/check-in/",
            payload,
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("permission", response.data["detail"].lower())

    # --------------------------------------------------------------------------
    # 4. MANAGER/ADMIN/OWNER ATTENDANCE MANAGEMENT
    # --------------------------------------------------------------------------

    def test_manager_can_check_in_staff_member(self):
        auth_header = self._get_auth_header(self.user_manager, self.org_a)
        payload = {
            "staff_id": str(self.profile_staff1.id),
            "shift_type": "REGULAR",
            "notes": "Manager manual check-in entry",
        }

        response = self.client.post(
            "/api/v1/hr/attendance/check-in/",
            payload,
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["staff"]["staff_code"], "ALPHA-STF-0001")

    def test_manager_attendance_override_and_audit(self):
        auth_header = self._get_auth_header(self.user_manager, self.org_a)
        today = date.today()

        payload = {
            "staff_id": str(self.profile_staff1.id),
            "date": str(today),
            "override_reason": "Device malfunction; verified by on-site CCTV",
            "status": "PRESENT",
            "check_in": "09:00:00",
            "check_out": "18:00:00",
            "late_minutes": 0,
            "overtime_minutes": 0,
        }

        response = self.client.post(
            "/api/v1/hr/attendance/override/",
            payload,
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_manual_override"])
        self.assertEqual(
            response.data["override_reason"],
            "Device malfunction; verified by on-site CCTV",
        )

        # Verify audit log
        audit = AuditLog.objects.filter(
            organization=self.org_a,
            action="STAFF_ATTENDANCE_OVERRIDE",
            actor=self.user_manager,
        ).first()
        self.assertIsNotNone(audit)

    def test_manager_bulk_mark_attendance(self):
        auth_header = self._get_auth_header(self.user_manager, self.org_a)
        today = date.today()

        payload = {
            "date": str(today),
            "status": "ABSENT",
            "notes": "Office closed for maintenance",
        }

        response = self.client.post(
            "/api/v1/hr/attendance/bulk-mark/",
            payload,
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["created"], 1)

    # --------------------------------------------------------------------------
    # 5. UNAUTHORIZED ROLE REJECTION
    # --------------------------------------------------------------------------

    def test_unauthorized_role_rejected_from_bulk_marking(self):
        auth_header = self._get_auth_header(self.user_staff1, self.org_a)
        payload = {
            "date": str(date.today()),
            "status": "PRESENT",
        }

        response = self.client.post(
            "/api/v1/hr/attendance/bulk-mark/",
            payload,
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthorized_role_rejected_from_override(self):
        auth_header = self._get_auth_header(self.user_staff1, self.org_a)
        payload = {
            "staff_id": str(self.profile_staff2.id),
            "date": str(date.today()),
            "override_reason": "Unauthorized attempt",
            "status": "PRESENT",
        }

        response = self.client.post(
            "/api/v1/hr/attendance/override/",
            payload,
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --------------------------------------------------------------------------
    # 6. LEAVE CREATION
    # --------------------------------------------------------------------------

    def test_authenticated_leave_creation(self):
        auth_header = self._get_auth_header(self.user_staff1, self.org_a)
        start = date.today() + timedelta(days=5)
        end = date.today() + timedelta(days=7)

        payload = {
            "leave_type": "CASUAL",
            "start_date": str(start),
            "end_date": str(end),
            "reason": "Family function",
        }

        response = self.client.post(
            "/api/v1/hr/attendance/leaves/",
            payload,
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(response.data["total_days"], "3.0")
        self.assertEqual(response.data["staff"]["staff_code"], "ALPHA-STF-0001")

        audit = AuditLog.objects.filter(
            organization=self.org_a,
            action="STAFF_LEAVE_REQUESTED",
            actor=self.user_staff1,
        ).first()
        self.assertIsNotNone(audit)

    # --------------------------------------------------------------------------
    # 7. LEAVE LISTING ISOLATION (STAFF vs MANAGER)
    # --------------------------------------------------------------------------

    def test_leave_listing_scoping(self):
        # Staff 1 creates a leave
        StaffLeaveRequest.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            leave_type=StaffLeaveRequest.LeaveType.CASUAL,
            start_date=date(2026, 9, 20),
            end_date=date(2026, 9, 21),
            total_days=Decimal("2"),
            reason="Staff 1 leave",
        )
        # Staff 2 creates a leave
        StaffLeaveRequest.objects.create(
            organization=self.org_a,
            staff=self.profile_staff2,
            leave_type=StaffLeaveRequest.LeaveType.SICK,
            start_date=date(2026, 9, 22),
            end_date=date(2026, 9, 23),
            total_days=Decimal("2"),
            reason="Staff 2 sick",
        )

        # Staff 1 lists leaves -> only see Staff 1's leave
        auth_staff1 = self._get_auth_header(self.user_staff1, self.org_a)
        res_staff1 = self.client.get(
            "/api/v1/hr/attendance/leaves/",
            **auth_staff1,
        )
        self.assertEqual(res_staff1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_staff1.data), 1)
        self.assertEqual(res_staff1.data[0]["staff"]["staff_code"], "ALPHA-STF-0001")

        # Manager lists leaves -> sees all organization leaves
        auth_manager = self._get_auth_header(self.user_manager, self.org_a)
        res_mgr = self.client.get(
            "/api/v1/hr/attendance/leaves/",
            **auth_manager,
        )
        self.assertEqual(res_mgr.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_mgr.data), 2)

    # --------------------------------------------------------------------------
    # 8. LEAVE APPROVAL & REJECTION RBAC
    # --------------------------------------------------------------------------

    def test_manager_can_approve_leave_request(self):
        leave_req = StaffLeaveRequest.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            leave_type=StaffLeaveRequest.LeaveType.ANNUAL,
            start_date=date(2026, 9, 25),
            end_date=date(2026, 9, 27),
            total_days=Decimal("3"),
            reason="Annual trip",
        )

        auth_header = self._get_auth_header(self.user_manager, self.org_a)
        payload = {
            "action": "APPROVE",
            "review_notes": "Approved by Operations Manager",
        }

        response = self.client.post(
            f"/api/v1/hr/attendance/leaves/{leave_req.id}/review/",
            payload,
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "APPROVED")
        self.assertEqual(response.data["reviewed_by_name"], "Majid Manager")

        # Verify attendance synchronization
        synced_count = StaffAttendance.objects.filter(
            organization=self.org_a,
            staff=self.profile_staff1,
            status=StaffAttendance.Status.ON_LEAVE,
        ).count()
        self.assertEqual(synced_count, 3)

    def test_regular_staff_cannot_review_leave(self):
        leave_req = StaffLeaveRequest.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            leave_type=StaffLeaveRequest.LeaveType.CASUAL,
            start_date=date(2026, 9, 25),
            end_date=date(2026, 9, 26),
            total_days=Decimal("2"),
            reason="Leave",
        )

        auth_header = self._get_auth_header(self.user_staff2, self.org_a)
        response = self.client.post(
            f"/api/v1/hr/attendance/leaves/{leave_req.id}/review/",
            {"action": "APPROVE"},
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --------------------------------------------------------------------------
    # 9. SELF-APPROVAL PREVENTION
    # --------------------------------------------------------------------------

    def test_manager_cannot_approve_own_leave(self):
        mgr_leave = StaffLeaveRequest.objects.create(
            organization=self.org_a,
            staff=self.profile_manager,
            leave_type=StaffLeaveRequest.LeaveType.CASUAL,
            start_date=date(2026, 9, 28),
            end_date=date(2026, 9, 29),
            total_days=Decimal("2"),
            reason="Manager vacation",
        )

        auth_header = self._get_auth_header(self.user_manager, self.org_a)
        response = self.client.post(
            f"/api/v1/hr/attendance/leaves/{mgr_leave.id}/review/",
            {"action": "APPROVE"},
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot approve or reject their own", response.data["detail"])

    # --------------------------------------------------------------------------
    # 10. CROSS-TENANT ACCESS REJECTION
    # --------------------------------------------------------------------------

    def test_cross_tenant_access_rejected(self):
        # Leave request in Org B
        leave_b = StaffLeaveRequest.objects.create(
            organization=self.org_b,
            staff=self.profile_b,
            leave_type=StaffLeaveRequest.LeaveType.CASUAL,
            start_date=date(2026, 9, 28),
            end_date=date(2026, 9, 29),
            total_days=Decimal("2"),
            reason="Org B leave",
        )

        # Manager from Org A attempts to review leave in Org B
        auth_header = self._get_auth_header(self.user_manager, self.org_a)
        response = self.client.post(
            f"/api/v1/hr/attendance/leaves/{leave_b.id}/review/",
            {"action": "APPROVE"},
            format="json",
            **auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --------------------------------------------------------------------------
    # 11. SUMMARY & MATRIX APIS
    # --------------------------------------------------------------------------

    def test_daily_summary_and_monthly_matrix_apis(self):
        today = date.today()
        # Create an attendance record
        StaffAttendance.objects.create(
            organization=self.org_a,
            staff=self.profile_staff1,
            date=today,
            status=StaffAttendance.Status.PRESENT,
            check_in=time(9, 0),
            check_out=time(18, 0),
        )

        # 1. Daily summary
        auth_mgr = self._get_auth_header(self.user_manager, self.org_a)
        res_summary = self.client.get(
            f"/api/v1/hr/attendance/daily/?date={str(today)}",
            **auth_mgr,
        )
        self.assertEqual(res_summary.status_code, status.HTTP_200_OK)
        self.assertEqual(res_summary.data["present_count"], 1)

        # 2. Monthly matrix
        res_matrix = self.client.get(
            f"/api/v1/hr/attendance/monthly-matrix/?year={today.year}&month={today.month}",
            **auth_mgr,
        )
        self.assertEqual(res_matrix.status_code, status.HTTP_200_OK)
        self.assertEqual(res_matrix.data["year"], today.year)
        self.assertEqual(res_matrix.data["month"], today.month)

    # --------------------------------------------------------------------------
    # 12. VALIDATION ERRORS & STATUS CODES
    # --------------------------------------------------------------------------

    def test_validation_errors(self):
        auth_header = self._get_auth_header(self.user_staff1, self.org_a)

        # Invalid leave dates: end before start
        invalid_payload = {
            "leave_type": "CASUAL",
            "start_date": "2026-09-25",
            "end_date": "2026-09-20",
            "reason": "Test",
        }
        res = self.client.post(
            "/api/v1/hr/attendance/leaves/",
            invalid_payload,
            format="json",
            **auth_header,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", res.data)
