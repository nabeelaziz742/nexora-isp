from django.test import TestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from customers.models import (
    Customer,
    InternetPackage,
    ServiceAccount,
)
from network.models import NetworkNode
from support.models import (
    Complaint,
    Incident,
    IncidentAffectedService,
)
from support.services import (
    SupportDomainError,
    create_complaint,
    create_incident,
    transition_complaint_status,
    transition_incident_status,
)
from tenancy.models import AuditLog, Organization
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient

from tenancy.models import OrganizationMembership


class SupportDomainTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Support ISP",
            code="SUPPORT-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Support ISP",
            code="OTHER-SUPPORT",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="SUP-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03001230001",
            address_line="Support Street",
            city="Lahore",
        )

        self.other_customer_same_org = Customer.objects.create(
            organization=self.organization,
            customer_number="SUP-CUST-002",
            first_name="Ali",
            last_name="Khan",
            phone="03001230002",
            address_line="Other Support Street",
            city="Lahore",
        )

        self.other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-SUP-CUST",
            first_name="Other",
            last_name="Customer",
            phone="03001230003",
            address_line="Karachi Street",
            city="Karachi",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Support Fiber 50",
            code="SUP-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Other Fiber",
            code="OTHER-SUP-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="6000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="SUP-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.other_customer_service = (
            ServiceAccount.objects.create(
                organization=self.organization,
                service_number="SUP-SRV-002",
                customer=self.other_customer_same_org,
                internet_package=self.package,
                status=ServiceAccount.Status.ACTIVE,
            )
        )

        self.other_service = ServiceAccount.objects.create(
            organization=self.other_organization,
            service_number="OTHER-SUP-SRV",
            customer=self.other_customer,
            internet_package=self.other_package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.node = NetworkNode.objects.create(
            organization=self.organization,
            name="Support Core Router",
            code="SUP-RTR-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.50.0.1",
        )

        self.other_node = NetworkNode.objects.create(
            organization=self.other_organization,
            name="Other Support Router",
            code="OTHER-SUP-RTR",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.60.0.1",
        )

    def test_create_complaint_with_service(self):
        result = create_complaint(
            organization=self.organization,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            category=Complaint.Category.CONNECTIVITY,
            priority=Complaint.Priority.HIGH,
            subject="Internet disconnected",
            description="Customer has no connectivity.",
        )

        complaint = result.complaint

        self.assertEqual(
            complaint.status,
            Complaint.Status.OPEN,
        )
        self.assertEqual(
            complaint.customer,
            self.customer,
        )
        self.assertEqual(
            complaint.service_account,
            self.service,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="SUPPORT_COMPLAINT_CREATED",
            ).exists()
        )

    def test_complaint_service_must_belong_to_customer(self):
        with self.assertRaises(SupportDomainError):
            create_complaint(
                organization=self.organization,
                customer_id=self.customer.id,
                service_account_id=(
                    self.other_customer_service.id
                ),
                category=Complaint.Category.CONNECTIVITY,
                priority=Complaint.Priority.HIGH,
                subject="Wrong service",
                description="Invalid customer service relation.",
            )

        self.assertEqual(
            Complaint.objects.count(),
            0,
        )

    def test_complaint_blocks_cross_tenant_customer(self):
        with self.assertRaises(SupportDomainError):
            create_complaint(
                organization=self.organization,
                customer_id=self.other_customer.id,
                category=Complaint.Category.OTHER,
                priority=Complaint.Priority.MEDIUM,
                subject="Cross tenant",
                description="Must be blocked.",
            )

    def test_complaint_status_flow(self):
        complaint = create_complaint(
            organization=self.organization,
            customer_id=self.customer.id,
            category=Complaint.Category.SPEED,
            priority=Complaint.Priority.MEDIUM,
            subject="Slow speed",
            description="Speed is below expected.",
        ).complaint

        transition_complaint_status(
            organization=self.organization,
            complaint_id=complaint.id,
            target_status=Complaint.Status.IN_PROGRESS,
        )

        transition_complaint_status(
            organization=self.organization,
            complaint_id=complaint.id,
            target_status=Complaint.Status.RESOLVED,
            resolution_notes="Customer link was corrected.",
        )

        transition_complaint_status(
            organization=self.organization,
            complaint_id=complaint.id,
            target_status=Complaint.Status.CLOSED,
        )

        complaint.refresh_from_db()

        self.assertEqual(
            complaint.status,
            Complaint.Status.CLOSED,
        )
        self.assertIsNotNone(
            complaint.resolved_at,
        )
        self.assertIsNotNone(
            complaint.closed_at,
        )

    def test_complaint_cannot_jump_directly_to_closed(self):
        complaint = create_complaint(
            organization=self.organization,
            customer_id=self.customer.id,
            category=Complaint.Category.OTHER,
            priority=Complaint.Priority.LOW,
            subject="General complaint",
            description="General support request.",
        ).complaint

        with self.assertRaises(SupportDomainError):
            transition_complaint_status(
                organization=self.organization,
                complaint_id=complaint.id,
                target_status=Complaint.Status.CLOSED,
            )

        complaint.refresh_from_db()

        self.assertEqual(
            complaint.status,
            Complaint.Status.OPEN,
        )

    def test_create_incident_with_multiple_affected_services(self):
        result = create_incident(
            organization=self.organization,
            title="Core router degradation",
            description="Packet loss detected.",
            severity=Incident.Severity.MAJOR,
            started_at=timezone.now(),
            network_node_id=self.node.id,
            affected_service_ids=[
                self.service.id,
                self.other_customer_service.id,
            ],
        )

        incident = result.incident

        self.assertEqual(
            incident.status,
            Incident.Status.OPEN,
        )
        self.assertEqual(
            IncidentAffectedService.objects.filter(
                incident=incident
            ).count(),
            2,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="SUPPORT_INCIDENT_CREATED",
            ).exists()
        )

    def test_incident_blocks_cross_tenant_network_node(self):
        with self.assertRaises(SupportDomainError):
            create_incident(
                organization=self.organization,
                title="Invalid node incident",
                description="Cross tenant node.",
                severity=Incident.Severity.MAJOR,
                started_at=timezone.now(),
                network_node_id=self.other_node.id,
            )

        self.assertEqual(
            Incident.objects.count(),
            0,
        )

    def test_incident_blocks_cross_tenant_affected_service(self):
        with self.assertRaises(SupportDomainError):
            create_incident(
                organization=self.organization,
                title="Invalid affected service",
                description="Cross tenant service.",
                severity=Incident.Severity.CRITICAL,
                started_at=timezone.now(),
                affected_service_ids=[
                    self.service.id,
                    self.other_service.id,
                ],
            )

        self.assertEqual(
            Incident.objects.count(),
            0,
        )

    def test_incident_status_flow(self):
        incident = create_incident(
            organization=self.organization,
            title="OLT degradation",
            description="Multiple ONUs are offline.",
            severity=Incident.Severity.CRITICAL,
            started_at=timezone.now(),
            network_node_id=self.node.id,
        ).incident

        transition_incident_status(
            organization=self.organization,
            incident_id=incident.id,
            target_status=Incident.Status.INVESTIGATING,
        )

        transition_incident_status(
            organization=self.organization,
            incident_id=incident.id,
            target_status=Incident.Status.IDENTIFIED,
            root_cause="OLT uplink degradation.",
        )

        transition_incident_status(
            organization=self.organization,
            incident_id=incident.id,
            target_status=Incident.Status.MONITORING,
        )

        transition_incident_status(
            organization=self.organization,
            incident_id=incident.id,
            target_status=Incident.Status.RESOLVED,
            resolution_notes="Uplink stabilized and monitored.",
        )

        incident.refresh_from_db()

        self.assertEqual(
            incident.status,
            Incident.Status.RESOLVED,
        )
        self.assertEqual(
            incident.root_cause,
            "OLT uplink degradation.",
        )
        self.assertIsNotNone(
            incident.resolved_at,
        )

    def test_incident_cannot_resolve_directly_from_open(self):
        incident = create_incident(
            organization=self.organization,
            title="Access degradation",
            description="Access layer issue.",
            severity=Incident.Severity.MINOR,
            started_at=timezone.now(),
        ).incident

        with self.assertRaises(SupportDomainError):
            transition_incident_status(
                organization=self.organization,
                incident_id=incident.id,
                target_status=Incident.Status.RESOLVED,
                resolution_notes="Resolved.",
            )

        incident.refresh_from_db()

        self.assertEqual(
            incident.status,
            Incident.Status.OPEN,
        )


class SupportOperationalAPITests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA API Support ISP",
            code="API-SUPPORT-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other API Support ISP",
            code="OTHER-API-SUPPORT",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        User = get_user_model()

        self.user = User.objects.create_user(
            username="support-api-user",
            email="support-api@nexora.test",
            password="StrongPass123!",
        )

        self.other_user = User.objects.create_user(
            username="other-support-api-user",
            email="other-support-api@nexora.test",
            password="StrongPass123!",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMembership.Role.OWNER,
        )

        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_user,
            role=OrganizationMembership.Role.OWNER,
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="API-SUP-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03009990001",
            address_line="API Support Street",
            city="Lahore",
        )

        self.other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-API-SUP-CUST",
            first_name="Other",
            last_name="Customer",
            phone="03009990002",
            address_line="Other API Street",
            city="Karachi",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="API Support Fiber",
            code="API-SUP-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Other API Fiber",
            code="OTHER-API-SUP-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="6000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="API-SUP-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.other_service = ServiceAccount.objects.create(
            organization=self.other_organization,
            service_number="OTHER-API-SUP-SRV",
            customer=self.other_customer,
            internet_package=self.other_package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.node = NetworkNode.objects.create(
            organization=self.organization,
            name="API Support Core Router",
            code="API-SUP-RTR-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.70.0.1",
        )

        self.client = APIClient()

        access_token = AccessToken.for_user(self.user)
        access_token["organization_id"] = str(
            self.organization.id
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(access_token)}"
        )

    def test_create_complaint_api(self):
        response = self.client.post(
            "/api/v1/support/complaints/",
            {
                "customer_id": str(self.customer.id),
                "service_account_id": str(self.service.id),
                "category": Complaint.Category.CONNECTIVITY,
                "priority": Complaint.Priority.HIGH,
                "subject": "API connectivity complaint",
                "description": "Customer is offline.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["status"],
            Complaint.Status.OPEN,
        )
        self.assertEqual(
            response.data["customer_number"],
            self.customer.customer_number,
        )

        self.assertEqual(
            Complaint.objects.for_organization(
                self.organization
            ).count(),
            1,
        )

    def test_complaint_list_search_api(self):
        create_complaint(
            organization=self.organization,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            category=Complaint.Category.SPEED,
            priority=Complaint.Priority.MEDIUM,
            subject="Searchable slow speed",
            description="Speed degradation.",
            created_by=self.user,
        )

        response = self.client.get(
            "/api/v1/support/complaints/",
            {
                "search": "Nabeel",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_complaint_status_transition_api(self):
        complaint = create_complaint(
            organization=self.organization,
            customer_id=self.customer.id,
            category=Complaint.Category.BILLING,
            priority=Complaint.Priority.MEDIUM,
            subject="Billing review",
            description="Invoice requires review.",
            created_by=self.user,
        ).complaint

        response = self.client.post(
            (
                f"/api/v1/support/complaints/"
                f"{complaint.id}/status-transitions/"
            ),
            {
                "target_status": Complaint.Status.IN_PROGRESS,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"],
            Complaint.Status.IN_PROGRESS,
        )

    def test_cross_tenant_complaint_detail_returns_404(self):
        complaint = create_complaint(
            organization=self.other_organization,
            customer_id=self.other_customer.id,
            category=Complaint.Category.OTHER,
            priority=Complaint.Priority.LOW,
            subject="Other tenant complaint",
            description="Must remain isolated.",
            created_by=self.other_user,
        ).complaint

        response = self.client.get(
            (
                f"/api/v1/support/complaints/"
                f"{complaint.id}/"
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_create_incident_api(self):
        response = self.client.post(
            "/api/v1/support/incidents/",
            {
                "title": "API core degradation",
                "description": "Packet loss detected.",
                "severity": Incident.Severity.CRITICAL,
                "started_at": timezone.now().isoformat(),
                "network_node_id": str(self.node.id),
                "affected_service_ids": [
                    str(self.service.id),
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["status"],
            Incident.Status.OPEN,
        )
        self.assertEqual(
            len(response.data["affected_services"]),
            1,
        )

    def test_incident_search_returns_distinct_rows(self):
        incident = create_incident(
            organization=self.organization,
            title="Customer impact incident",
            description="Multiple impact matches.",
            severity=Incident.Severity.MAJOR,
            started_at=timezone.now(),
            affected_service_ids=[
                self.service.id,
            ],
            created_by=self.user,
        ).incident

        response = self.client.get(
            "/api/v1/support/incidents/",
            {
                "search": "Nabeel",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            str(incident.id),
        )

    def test_incident_status_transition_api(self):
        incident = create_incident(
            organization=self.organization,
            title="API incident transition",
            description="Transition test.",
            severity=Incident.Severity.MINOR,
            started_at=timezone.now(),
            created_by=self.user,
        ).incident

        response = self.client.post(
            (
                f"/api/v1/support/incidents/"
                f"{incident.id}/status-transitions/"
            ),
            {
                "target_status": Incident.Status.INVESTIGATING,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"],
            Incident.Status.INVESTIGATING,
        )

    def test_cross_tenant_incident_detail_returns_404(self):
        incident = create_incident(
            organization=self.other_organization,
            title="Other tenant incident",
            description="Must remain isolated.",
            severity=Incident.Severity.MAJOR,
            started_at=timezone.now(),
            affected_service_ids=[
                self.other_service.id,
            ],
            created_by=self.other_user,
        ).incident

        response = self.client.get(
            (
                f"/api/v1/support/incidents/"
                f"{incident.id}/"
            )
        )

        self.assertEqual(response.status_code, 404)