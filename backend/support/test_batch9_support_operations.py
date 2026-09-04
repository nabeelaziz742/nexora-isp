from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from communications.models import (
    CommunicationLog,
    CommunicationProvider,
)
from customers.models import (
    Customer,
    InternetPackage,
    NotificationPreference,
    ServiceAccount,
)
from field_operations.models import WorkOrder
from field_operations.services import create_work_order
from support.models import (
    Complaint,
    ComplaintInternalNote,
    ComplaintSLAPolicy,
    ComplaintTimeline,
    Incident,
)
from support.services import (
    SupportDomainError,
    add_internal_note,
    assign_complaint,
    calculate_complaint_sla,
    confirm_and_close_complaint,
    create_complaint,
    escalate_complaint,
    get_support_dashboard_metrics,
    reassign_complaint,
    resolve_complaint,
    transition_complaint_status,
)
from tenancy.models import AuditLog, Organization, OrganizationMembership

User = get_user_model()


class Batch9SupportOperationsTests(TestCase):
    def setUp(self):
        # Primary Organization
        self.org = Organization.objects.create(
            name="Nexora Fiber Lahore",
            code="NEX-LHR-B9",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
            is_active=True,
        )

        # Secondary Organization (Tenant Isolation Testing)
        self.other_org = Organization.objects.create(
            name="Nexora Fiber Karachi",
            code="NEX-KHI-B9",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
            is_active=True,
        )

        # Staff & Technician Users
        self.staff_user = User.objects.create_user(
            username="support_officer",
            email="support@nexora.test",
            password="Password123!",
            first_name="Support",
            last_name="Officer",
        )
        self.staff_membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.staff_user,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )

        self.tech_user = User.objects.create_user(
            username="field_technician_1",
            email="tech1@nexora.test",
            password="Password123!",
            first_name="Tariq",
            last_name="Technician",
        )
        self.tech_membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.tech_user,
            role=OrganizationMembership.Role.TECHNICIAN,
            is_active=True,
        )

        self.tech_user_2 = User.objects.create_user(
            username="field_technician_2",
            email="tech2@nexora.test",
            password="Password123!",
            first_name="Rashid",
            last_name="Field",
        )
        self.tech_membership_2 = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.tech_user_2,
            role=OrganizationMembership.Role.TECHNICIAN,
            is_active=True,
        )

        self.other_tech_user = User.objects.create_user(
            username="other_org_tech",
            email="other_tech@nexora.test",
            password="Password123!",
            first_name="Other",
            last_name="Tech",
        )
        self.other_tech_membership = OrganizationMembership.objects.create(
            organization=self.other_org,
            user=self.other_tech_user,
            role=OrganizationMembership.Role.TECHNICIAN,
            is_active=True,
        )

        # Customers & Services
        self.customer = Customer.objects.create(
            organization=self.org,
            customer_number="CUST-B9-001",
            first_name="Usman",
            last_name="Ali",
            phone="03001112233",
            email="usman@test.com",
            address_line="House 12, Street 4, Gulberg, Lahore",
            city="Lahore",
            is_active=True,
        )
        self.notif_pref = NotificationPreference.objects.create(
            organization=self.org,
            customer=self.customer,
            whatsapp_enabled=True,
            sms_enabled=True,
            email_enabled=True,
        )

        self.other_customer = Customer.objects.create(
            organization=self.other_org,
            customer_number="CUST-KHI-001",
            first_name="Ahmed",
            last_name="Raza",
            phone="03211112233",
            email="ahmed@test.com",
            address_line="DHA Karachi",
            city="Karachi",
            is_active=True,
        )

        self.package = InternetPackage.objects.create(
            organization=self.org,
            name="Super Fiber 100M",
            code="SF-100",
            download_speed_mbps=100,
            upload_speed_mbps=50,
            monthly_price="4500.00",
            is_active=True,
        )

        self.service = ServiceAccount.objects.create(
            organization=self.org,
            customer=self.customer,
            service_number="SRV-B9-1001",
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        # API Client Authentication
        self.client = APIClient()
        token = RefreshToken.for_user(self.staff_user)
        token["organization_id"] = str(self.org.id)
        self.auth_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {str(token.access_token)}",
        }

    # ==================== 1. COMPLAINT REGISTRATION & SLA ====================

    def test_complaint_creation_and_sla_calculation(self):
        """Test complaint registration, unique ticket number, and SLA calculation."""
        result = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            category=Complaint.Category.FIBER_CABLE_DAMAGE,
            priority=Complaint.Priority.CRITICAL,
            source=Complaint.Source.PHONE,
            subject="Fiber cut near gate",
            description="Construction crew cut the optical fiber drop cable.",
            created_by=self.staff_user,
        )

        complaint = result.complaint
        self.assertTrue(complaint.complaint_number.startswith("CMP-"))
        self.assertEqual(complaint.status, Complaint.Status.OPEN)
        self.assertEqual(complaint.priority, Complaint.Priority.CRITICAL)
        self.assertEqual(complaint.category, Complaint.Category.FIBER_CABLE_DAMAGE)
        self.assertEqual(complaint.source, Complaint.Source.PHONE)
        self.assertEqual(complaint.sla_status, Complaint.SLAStatus.ON_TRACK)
        self.assertIsNotNone(complaint.response_due_at)
        self.assertIsNotNone(complaint.resolution_due_at)

        # Verify initial timeline entry
        timeline = ComplaintTimeline.objects.filter(complaint=complaint)
        self.assertEqual(timeline.count(), 1)
        self.assertEqual(timeline.first().event_type, "CREATED")

        # Verify Audit Log
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.org,
                action="SUPPORT_COMPLAINT_CREATED",
                resource_id=complaint.id,
            ).exists()
        )

    def test_complaint_creation_with_direct_assignment(self):
        """Test complaint creation with initial technician assigned."""
        result = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            category=Complaint.Category.ROUTER_ISSUE,
            priority=Complaint.Priority.HIGH,
            subject="Router reboot loop",
            description="Customer router keeps rebooting constantly.",
            assigned_to_id=self.tech_user.id,
            created_by=self.staff_user,
        )

        complaint = result.complaint
        self.assertEqual(complaint.status, Complaint.Status.ASSIGNED)
        self.assertEqual(complaint.assigned_to, self.tech_user)
        self.assertEqual(complaint.assigned_by, self.staff_user)
        self.assertIsNotNone(complaint.assigned_at)

    def test_custom_sla_policy_applied_on_creation(self):
        """Test that per-tenant custom SLA policy overrides defaults."""
        ComplaintSLAPolicy.objects.create(
            organization=self.org,
            priority=Complaint.Priority.CRITICAL,
            response_target_minutes=10,
            resolution_target_hours=2,
            escalation_threshold_hours=1,
            is_active=True,
        )

        now = timezone.now()
        response_due, resolution_due = calculate_complaint_sla(self.org, Complaint.Priority.CRITICAL)

        self.assertAlmostEqual((response_due - now).total_seconds(), 600, delta=10)
        self.assertAlmostEqual((resolution_due - now).total_seconds(), 7200, delta=10)

    # ==================== 2. ASSIGNMENT & REASSIGNMENT ====================

    def test_assign_and_reassign_technician_workflow(self):
        """Test technician assignment and reassignment with mandatory reason and timeline."""
        result = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            category=Complaint.Category.SPEED,
            priority=Complaint.Priority.MEDIUM,
            subject="Speed lower than 100M",
            description="Getting 30 Mbps on speedtest.",
            created_by=self.staff_user,
        )
        complaint = result.complaint

        # Step 1: Assign to Tech 1
        assign_result = assign_complaint(
            organization=self.org,
            complaint_id=complaint.id,
            technician_id=self.tech_user.id,
            notes="Please visit customer premises.",
            actor=self.staff_user,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.ASSIGNED)
        self.assertEqual(complaint.assigned_to, self.tech_user)

        # Step 2: Reassign to Tech 2 with reason
        reassign_result = reassign_complaint(
            organization=self.org,
            complaint_id=complaint.id,
            technician_id=self.tech_user_2.id,
            reason="Tech 1 busy on emergency fiber splice.",
            notes="Reassigned to Rashid.",
            actor=self.staff_user,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.assigned_to, self.tech_user_2)
        self.assertEqual(complaint.reassignment_reason, "Tech 1 busy on emergency fiber splice.")

        # Verify Timeline entries
        events = ComplaintTimeline.objects.filter(complaint=complaint).values_list("event_type", flat=True)
        self.assertIn("CREATED", events)
        self.assertIn("ASSIGNED", events)
        self.assertIn("REASSIGNED", events)

    def test_reassignment_requires_reason(self):
        """Reassignment without a reason must be blocked."""
        complaint = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            category=Complaint.Category.OTHER,
            priority=Complaint.Priority.LOW,
            subject="General Inquiry",
            description="Testing reason requirement.",
            created_by=self.staff_user,
        ).complaint

        with self.assertRaises(SupportDomainError):
            reassign_complaint(
                organization=self.org,
                complaint_id=complaint.id,
                technician_id=self.tech_user_2.id,
                reason="",  # Empty reason
                actor=self.staff_user,
            )

    # ==================== 3. STATUS TRANSITIONS & SAFEGUARDS ====================

    def test_comprehensive_status_lifecycle(self):
        """Test valid state machine transitions from NEW to CLOSED."""
        complaint = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            category=Complaint.Category.CONNECTIVITY,
            priority=Complaint.Priority.HIGH,
            subject="No internet red light on ONU",
            description="Loss of signal.",
            created_by=self.staff_user,
        ).complaint

        # OPEN -> IN_PROGRESS
        transition_complaint_status(
            organization=self.org,
            complaint_id=complaint.id,
            target_status=Complaint.Status.IN_PROGRESS,
            notes="Technician testing optical power.",
            actor=self.tech_user,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.IN_PROGRESS)
        self.assertIsNotNone(complaint.first_response_at)

        # IN_PROGRESS -> WAITING_PARTS
        transition_complaint_status(
            organization=self.org,
            complaint_id=complaint.id,
            target_status=Complaint.Status.WAITING_PARTS,
            notes="Need replacement patch cord.",
            actor=self.tech_user,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.WAITING_PARTS)

        # WAITING_PARTS -> IN_PROGRESS
        transition_complaint_status(
            organization=self.org,
            complaint_id=complaint.id,
            target_status=Complaint.Status.IN_PROGRESS,
            notes="Parts received, continuing repair.",
            actor=self.tech_user,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.IN_PROGRESS)

    def test_terminal_state_protection(self):
        """Closed and cancelled complaints cannot transition to other states."""
        complaint = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            category=Complaint.Category.BILLING,
            priority=Complaint.Priority.LOW,
            subject="Billing question",
            description="Question resolved on phone.",
            created_by=self.staff_user,
        ).complaint

        # Resolve
        resolve_complaint(
            organization=self.org,
            complaint_id=complaint.id,
            diagnosis_category="Billing Explanation",
            resolution_summary="Explained billing cycle over call.",
            actor=self.staff_user,
        )

        # Close
        confirm_and_close_complaint(
            organization=self.org,
            complaint_id=complaint.id,
            confirmation=Complaint.CustomerConfirmation.CONFIRMED,
            feedback_rating=5,
            actor=self.staff_user,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.CLOSED)

        # Attempt transition from CLOSED -> OPEN must fail
        with self.assertRaises(SupportDomainError):
            transition_complaint_status(
                organization=self.org,
                complaint_id=complaint.id,
                target_status=Complaint.Status.IN_PROGRESS,
                actor=self.staff_user,
            )

    # ==================== 4. ESCALATION & INTERNAL NOTES ====================

    def test_ticket_escalation_workflow(self):
        """Test controlled escalation with reason, level increment, and audit."""
        complaint = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            category=Complaint.Category.CONNECTIVITY,
            priority=Complaint.Priority.MEDIUM,
            subject="Frequent disconnections",
            description="Disconnection every 10 mins.",
            created_by=self.staff_user,
        ).complaint

        escalate_complaint(
            organization=self.org,
            complaint_id=complaint.id,
            reason="Repeated customer complaint, line attenuation unstable.",
            escalated_to_id=self.staff_user.id,
            actor=self.tech_user,
        )
        complaint.refresh_from_db()
        self.assertTrue(complaint.is_escalated)
        self.assertEqual(complaint.escalation_level, 1)
        self.assertEqual(complaint.status, Complaint.Status.ESCALATED)
        self.assertEqual(complaint.escalated_to, self.staff_user)

    def test_internal_staff_notes(self):
        """Test adding internal staff notes without customer exposure."""
        complaint = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            category=Complaint.Category.DEVICE,
            priority=Complaint.Priority.MEDIUM,
            subject="ONU replacement check",
            description="Testing notes.",
            created_by=self.staff_user,
        ).complaint

        note = add_internal_note(
            organization=self.org,
            complaint_id=complaint.id,
            note="Suspect customer's private router is causing DHCP storm.",
            actor=self.staff_user,
        )

        self.assertTrue(note.is_internal)
        self.assertEqual(ComplaintInternalNote.objects.filter(complaint=complaint).count(), 1)

    # ==================== 5. WORK ORDER LINKAGE ====================

    def test_work_order_linkage_and_timeline(self):
        """Test creating a work order linked to a complaint updates complaint timeline."""
        complaint = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            category=Complaint.Category.FIBER_CABLE_DAMAGE,
            priority=Complaint.Priority.HIGH,
            subject="Drop fiber broken",
            description="Field team required.",
            created_by=self.staff_user,
        ).complaint

        wo_res = create_work_order(
            organization=self.org,
            work_type=WorkOrder.WorkType.REPAIR,
            priority=WorkOrder.Priority.HIGH,
            title="Splice Drop Fiber at House 12",
            description="Customer reported broken fiber cable.",
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            complaint_id=complaint.id,
            created_by=self.staff_user,
        )

        work_order = wo_res.work_order
        self.assertEqual(work_order.complaint, complaint)

        # Check timeline entry
        timeline_events = ComplaintTimeline.objects.filter(
            complaint=complaint,
            event_type="WORK_ORDER_LINKED",
        )
        self.assertEqual(timeline_events.count(), 1)
        self.assertIn(work_order.work_order_number, timeline_events.first().summary)

    # ==================== 6. DIAGNOSIS, RESOLUTION & CUSTOMER CONFIRMATION ====================

    def test_diagnosis_resolution_and_customer_confirmation(self):
        """Test structured diagnosis, resolution, and customer confirmation / closure."""
        complaint = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            category=Complaint.Category.ONU_ISSUE,
            priority=Complaint.Priority.HIGH,
            subject="Red LOS light on ONU",
            description="Optical power -32 dBm.",
            created_by=self.staff_user,
        ).complaint

        # Resolve complaint
        resolve_complaint(
            organization=self.org,
            complaint_id=complaint.id,
            diagnosis_category="Fiber Repaired",
            resolution_summary="Re-spliced optical joint at distribution box. Optical power restored to -19 dBm.",
            resolution_notes="Tested speed with customer on site.",
            actor=self.tech_user,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.RESOLVED)
        self.assertEqual(complaint.diagnosis_category, "Fiber Repaired")
        self.assertEqual(complaint.customer_confirmation, Complaint.CustomerConfirmation.PENDING)
        self.assertIsNotNone(complaint.resolved_at)

        # Customer Confirms
        confirm_and_close_complaint(
            organization=self.org,
            complaint_id=complaint.id,
            confirmation=Complaint.CustomerConfirmation.CONFIRMED,
            feedback_rating=5,
            feedback_notes="Speed is working perfectly now. Excellent service!",
            actor=self.staff_user,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.CLOSED)
        self.assertEqual(complaint.customer_confirmation, Complaint.CustomerConfirmation.CONFIRMED)
        self.assertEqual(complaint.customer_feedback_rating, 5)
        self.assertIsNotNone(complaint.closed_at)

    def test_customer_rejection_reopens_complaint(self):
        """Test customer rejection of resolution reopens ticket to IN_PROGRESS."""
        complaint = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            category=Complaint.Category.SPEED,
            priority=Complaint.Priority.MEDIUM,
            subject="Slow speed issue",
            description="Speed drops in evening.",
            created_by=self.staff_user,
        ).complaint

        resolve_complaint(
            organization=self.org,
            complaint_id=complaint.id,
            diagnosis_category="Configuration Corrected",
            resolution_summary="Refreshed speed profile on BRAS.",
            actor=self.staff_user,
        )

        confirm_and_close_complaint(
            organization=self.org,
            complaint_id=complaint.id,
            confirmation=Complaint.CustomerConfirmation.REJECTED,
            feedback_notes="Speed is still only 20 Mbps, issue not fixed.",
            actor=self.staff_user,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.IN_PROGRESS)
        self.assertEqual(complaint.customer_confirmation, Complaint.CustomerConfirmation.REJECTED)

    # ==================== 7. DASHBOARD METRICS & WORKLOAD ====================

    def test_support_dashboard_metrics(self):
        """Test aggregated KPI calculations and technician workloads."""
        create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            category=Complaint.Category.CONNECTIVITY,
            priority=Complaint.Priority.CRITICAL,
            subject="Down ticket 1",
            description="Critical outage.",
            assigned_to_id=self.tech_user.id,
            created_by=self.staff_user,
        )
        create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            category=Complaint.Category.SPEED,
            priority=Complaint.Priority.LOW,
            subject="Slow speed ticket 2",
            description="Unassigned ticket.",
            created_by=self.staff_user,
        )

        metrics = get_support_dashboard_metrics(self.org)
        self.assertEqual(metrics["total_complaints"], 2)
        self.assertEqual(metrics["open_complaints"], 2)
        self.assertEqual(metrics["critical_complaints"], 1)
        self.assertEqual(metrics["unassigned_complaints"], 1)

        # Verify technician workload structure
        tech1_entry = next((t for t in metrics["technician_workloads"] if t["technician_id"] == str(self.tech_user.id)), None)
        self.assertIsNotNone(tech1_entry)
        self.assertEqual(tech1_entry["open_tickets"], 1)

    # ==================== 8. MULTI-TENANCY & SECURITY ====================

    def test_cross_tenant_complaint_isolation(self):
        """Verify cross-tenant customer and ticket isolation."""
        # Cannot create complaint for another organization's customer
        with self.assertRaises(SupportDomainError):
            create_complaint(
                organization=self.org,
                customer_id=self.other_customer.id,
                category=Complaint.Category.CONNECTIVITY,
                priority=Complaint.Priority.HIGH,
                subject="Illegal Cross Tenant",
                description="Should fail.",
                created_by=self.staff_user,
            )

        # Cannot assign technician from another organization
        complaint = create_complaint(
            organization=self.org,
            customer_id=self.customer.id,
            category=Complaint.Category.BILLING,
            priority=Complaint.Priority.LOW,
            subject="Tenant Test",
            description="Test isolation.",
            created_by=self.staff_user,
        ).complaint

        with self.assertRaises(SupportDomainError):
            assign_complaint(
                organization=self.org,
                complaint_id=complaint.id,
                technician_id=self.other_tech_user.id,
                actor=self.staff_user,
            )

    # ==================== 9. REST API ENDPOINTS ====================

    def test_rest_api_complaint_crud_and_actions(self):
        """Test full REST API workflow: list, create, assign, escalate, notes, resolve, close."""
        # 1. POST /api/v1/support/complaints/
        create_payload = {
            "customer_id": str(self.customer.id),
            "service_account_id": str(self.service.id),
            "category": "CONNECTIVITY",
            "priority": "HIGH",
            "source": "WHATSAPP",
            "subject": "REST API Complaint Test",
            "description": "Registered via API test suite.",
        }
        res = self.client.post("/api/v1/support/complaints/", create_payload, format="json", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        complaint_id = res.data["id"]

        # 2. GET /api/v1/support/complaints/<id>/
        detail_res = self.client.get(f"/api/v1/support/complaints/{complaint_id}/", **self.auth_headers)
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.data["subject"], "REST API Complaint Test")

        # 3. POST /api/v1/support/complaints/<id>/assign/
        assign_res = self.client.post(
            f"/api/v1/support/complaints/{complaint_id}/assign/",
            {"technician_id": str(self.tech_user.id), "notes": "API assign"},
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(assign_res.status_code, status.HTTP_200_OK)
        self.assertEqual(assign_res.data["status"], "ASSIGNED")

        # 4. POST /api/v1/support/complaints/<id>/notes/
        note_res = self.client.post(
            f"/api/v1/support/complaints/{complaint_id}/notes/",
            {"note": "API Internal Note"},
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(note_res.status_code, status.HTTP_201_CREATED)

        # 5. POST /api/v1/support/complaints/<id>/resolve/
        resolve_res = self.client.post(
            f"/api/v1/support/complaints/{complaint_id}/resolve/",
            {
                "diagnosis_category": "Connector Replaced",
                "resolution_summary": "Replaced damaged RJ45 connector.",
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(resolve_res.status_code, status.HTTP_200_OK)
        self.assertEqual(resolve_res.data["status"], "RESOLVED")

        # 6. POST /api/v1/support/complaints/<id>/close/
        close_res = self.client.post(
            f"/api/v1/support/complaints/{complaint_id}/close/",
            {
                "confirmation": "CONFIRMED",
                "feedback_rating": 5,
                "feedback_notes": "Very fast fix.",
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(close_res.status_code, status.HTTP_200_OK)
        self.assertEqual(close_res.data["status"], "CLOSED")

        # 7. GET /api/v1/support/dashboard/metrics/
        metrics_res = self.client.get("/api/v1/support/dashboard/metrics/", **self.auth_headers)
        self.assertEqual(metrics_res.status_code, status.HTTP_200_OK)
        self.assertIn("total_complaints", metrics_res.data)

        # 8. GET & PUT /api/v1/support/sla-policies/
        sla_put_res = self.client.put(
            "/api/v1/support/sla-policies/",
            {
                "policies": [
                    {
                        "priority": "CRITICAL",
                        "response_target_minutes": 20,
                        "resolution_target_hours": 3,
                        "escalation_threshold_hours": 2,
                    }
                ]
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(sla_put_res.status_code, status.HTTP_200_OK)
