from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from customers.models import (
    Customer,
    InternetPackage,
    ServiceAccount,
)
from field_operations.models import WorkOrder
from field_operations.services import (
    FieldOperationsDomainError,
    assign_work_order_technician,
    complete_work_order,
    create_work_order,
    dispatch_work_order,
    mark_work_order_onsite,
)
from network.models import NetworkNode
from support.models import Complaint, Incident
from tenancy.models import (
    AuditLog,
    Organization,
    OrganizationMembership,
)


class FieldOperationsDomainTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Field ISP",
            code="FIELD-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Field ISP",
            code="OTHER-FIELD",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        User = get_user_model()

        self.owner = User.objects.create_user(
            username="field-owner",
            email="field-owner@nexora.test",
            password="StrongPass123!",
            first_name="Field",
            last_name="Owner",
        )

        self.technician = User.objects.create_user(
            username="field-technician",
            email="field-technician@nexora.test",
            password="StrongPass123!",
            first_name="Field",
            last_name="Technician",
        )

        self.staff_user = User.objects.create_user(
            username="field-staff",
            email="field-staff@nexora.test",
            password="StrongPass123!",
            first_name="Field",
            last_name="Staff",
        )

        self.other_technician = User.objects.create_user(
            username="other-field-technician",
            email="other-field-tech@nexora.test",
            password="StrongPass123!",
            first_name="Other",
            last_name="Technician",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.technician,
            role=OrganizationMembership.Role.TECHNICIAN,
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.staff_user,
            role=OrganizationMembership.Role.STAFF,
        )

        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_technician,
            role=OrganizationMembership.Role.TECHNICIAN,
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="FIELD-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03008880001",
            address_line="Field Street",
            city="Lahore",
        )

        self.other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-FIELD-CUST",
            first_name="Other",
            last_name="Customer",
            phone="03008880002",
            address_line="Other Field Street",
            city="Karachi",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Field Fiber 50",
            code="FIELD-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Other Field Fiber",
            code="OTHER-FIELD-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="6000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="FIELD-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.other_service = ServiceAccount.objects.create(
            organization=self.other_organization,
            service_number="OTHER-FIELD-SRV",
            customer=self.other_customer,
            internet_package=self.other_package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.node = NetworkNode.objects.create(
            organization=self.organization,
            name="Field Core Router",
            code="FIELD-RTR-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.80.0.1",
        )

        self.other_node = NetworkNode.objects.create(
            organization=self.other_organization,
            name="Other Field Router",
            code="OTHER-FIELD-RTR",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.90.0.1",
        )

        self.complaint = Complaint.objects.create(
            organization=self.organization,
            complaint_number="FIELD-CMP-001",
            customer=self.customer,
            service_account=self.service,
            category=Complaint.Category.CONNECTIVITY,
            priority=Complaint.Priority.HIGH,
            status=Complaint.Status.OPEN,
            subject="No connectivity",
            description="Customer requires field visit.",
            created_by=self.owner,
        )

        self.incident = Incident.objects.create(
            organization=self.organization,
            incident_number="FIELD-INC-001",
            network_node=self.node,
            title="Access degradation",
            description="Field inspection required.",
            severity=Incident.Severity.MAJOR,
            status=Incident.Status.OPEN,
            started_at=__import__(
                "django.utils.timezone",
                fromlist=["now"],
            ).now(),
            created_by=self.owner,
        )

    def test_create_work_order_with_operational_context(self):
        result = create_work_order(
            organization=self.organization,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            network_node_id=self.node.id,
            complaint_id=self.complaint.id,
            incident_id=self.incident.id,
            work_type=WorkOrder.WorkType.REPAIR,
            priority=WorkOrder.Priority.HIGH,
            title="Restore customer connectivity",
            description="Technician field visit required.",
            created_by=self.owner,
        )

        work_order = result.work_order

        self.assertEqual(
            work_order.status,
            WorkOrder.Status.CREATED,
        )
        self.assertEqual(
            work_order.customer,
            self.customer,
        )
        self.assertEqual(
            work_order.service_account,
            self.service,
        )
        self.assertEqual(
            work_order.complaint,
            self.complaint,
        )
        self.assertEqual(
            work_order.incident,
            self.incident,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                action="FIELD_WORK_ORDER_CREATED",
            ).exists()
        )

    def test_service_infers_customer(self):
        work_order = create_work_order(
            organization=self.organization,
            service_account_id=self.service.id,
            work_type=WorkOrder.WorkType.SITE_VISIT,
            priority=WorkOrder.Priority.MEDIUM,
            title="Service inspection",
            description="Inspect customer service.",
        ).work_order

        self.assertEqual(
            work_order.customer,
            self.customer,
        )

    def test_cross_tenant_service_is_blocked(self):
        with self.assertRaises(
            FieldOperationsDomainError
        ):
            create_work_order(
                organization=self.organization,
                service_account_id=self.other_service.id,
                work_type=WorkOrder.WorkType.REPAIR,
                priority=WorkOrder.Priority.HIGH,
                title="Invalid service",
                description="Cross tenant service.",
            )

        self.assertEqual(
            WorkOrder.objects.count(),
            0,
        )

    def test_cross_tenant_network_node_is_blocked(self):
        with self.assertRaises(
            FieldOperationsDomainError
        ):
            create_work_order(
                organization=self.organization,
                network_node_id=self.other_node.id,
                work_type=(
                    WorkOrder.WorkType.NETWORK_MAINTENANCE
                ),
                priority=WorkOrder.Priority.HIGH,
                title="Invalid node",
                description="Cross tenant node.",
            )

    def test_non_technician_cannot_be_assigned(self):
        work_order = create_work_order(
            organization=self.organization,
            customer_id=self.customer.id,
            work_type=WorkOrder.WorkType.SITE_VISIT,
            priority=WorkOrder.Priority.MEDIUM,
            title="Customer visit",
            description="Field visit required.",
        ).work_order

        with self.assertRaises(
            FieldOperationsDomainError
        ):
            assign_work_order_technician(
                organization=self.organization,
                work_order_id=work_order.id,
                technician_id=self.staff_user.id,
                actor=self.owner,
            )

        work_order.refresh_from_db()

        self.assertEqual(
            work_order.status,
            WorkOrder.Status.CREATED,
        )

    def test_cross_tenant_technician_is_blocked(self):
        work_order = create_work_order(
            organization=self.organization,
            work_type=WorkOrder.WorkType.SITE_VISIT,
            priority=WorkOrder.Priority.LOW,
            title="General field visit",
            description="Visit required.",
        ).work_order

        with self.assertRaises(
            FieldOperationsDomainError
        ):
            assign_work_order_technician(
                organization=self.organization,
                work_order_id=work_order.id,
                technician_id=self.other_technician.id,
            )

    def test_complete_work_order_lifecycle(self):
        work_order = create_work_order(
            organization=self.organization,
            customer_id=self.customer.id,
            service_account_id=self.service.id,
            work_type=WorkOrder.WorkType.REPAIR,
            priority=WorkOrder.Priority.CRITICAL,
            title="Critical connectivity repair",
            description="Restore customer service.",
            created_by=self.owner,
        ).work_order

        assign_work_order_technician(
            organization=self.organization,
            work_order_id=work_order.id,
            technician_id=self.technician.id,
            actor=self.owner,
        )

        dispatch_work_order(
            organization=self.organization,
            work_order_id=work_order.id,
            dispatch_notes="Technician dispatched.",
            actor=self.owner,
        )

        mark_work_order_onsite(
            organization=self.organization,
            work_order_id=work_order.id,
            onsite_notes="Technician reached customer site.",
            actor=self.technician,
        )

        complete_work_order(
            organization=self.organization,
            work_order_id=work_order.id,
            completion_notes=(
                "Fiber connector replaced and "
                "service restored."
            ),
            actor=self.technician,
        )

        work_order.refresh_from_db()

        self.assertEqual(
            work_order.status,
            WorkOrder.Status.COMPLETED,
        )
        self.assertIsNotNone(
            work_order.assigned_at,
        )
        self.assertIsNotNone(
            work_order.dispatched_at,
        )
        self.assertIsNotNone(
            work_order.onsite_at,
        )
        self.assertIsNotNone(
            work_order.completed_at,
        )

        self.assertEqual(
            AuditLog.objects.filter(
                organization=self.organization,
                resource_type="WorkOrder",
            ).count(),
            5,
        )

    def test_work_order_cannot_complete_from_created(self):
        work_order = create_work_order(
            organization=self.organization,
            work_type=WorkOrder.WorkType.OTHER,
            priority=WorkOrder.Priority.LOW,
            title="Lifecycle test",
            description="Must follow lifecycle.",
        ).work_order

        with self.assertRaises(
            FieldOperationsDomainError
        ):
            complete_work_order(
                organization=self.organization,
                work_order_id=work_order.id,
                completion_notes="Invalid completion.",
            )

        work_order.refresh_from_db()

        self.assertEqual(
            work_order.status,
            WorkOrder.Status.CREATED,
        )

    def test_completion_notes_are_required(self):
        work_order = create_work_order(
            organization=self.organization,
            work_type=WorkOrder.WorkType.REPAIR,
            priority=WorkOrder.Priority.HIGH,
            title="Repair work",
            description="Repair required.",
        ).work_order

        assign_work_order_technician(
            organization=self.organization,
            work_order_id=work_order.id,
            technician_id=self.technician.id,
        )

        dispatch_work_order(
            organization=self.organization,
            work_order_id=work_order.id,
        )

        mark_work_order_onsite(
            organization=self.organization,
            work_order_id=work_order.id,
        )

        with self.assertRaises(
            FieldOperationsDomainError
        ):
            complete_work_order(
                organization=self.organization,
                work_order_id=work_order.id,
                completion_notes="   ",
            )

        work_order.refresh_from_db()

        self.assertEqual(
            work_order.status,
            WorkOrder.Status.ONSITE,
        )


class FieldOperationsOperationalAPITests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="NEXORA Field API ISP",
            code="FIELD-API-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.other_organization = Organization.objects.create(
            name="Other Field API ISP",
            code="OTHER-FIELD-API",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        User = get_user_model()

        self.owner = User.objects.create_user(
            username="field-api-owner",
            email="field-api-owner@nexora.test",
            password="StrongPass123!",
            first_name="Field",
            last_name="Owner",
        )

        self.technician = User.objects.create_user(
            username="field-api-technician",
            email="field-api-tech@nexora.test",
            password="StrongPass123!",
            first_name="API",
            last_name="Technician",
        )

        self.other_owner = User.objects.create_user(
            username="other-field-api-owner",
            email="other-field-api-owner@nexora.test",
            password="StrongPass123!",
            first_name="Other",
            last_name="Owner",
        )

        self.other_technician = User.objects.create_user(
            username="other-field-api-technician",
            email="other-field-api-tech@nexora.test",
            password="StrongPass123!",
            first_name="Other",
            last_name="Technician",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.technician,
            role=OrganizationMembership.Role.TECHNICIAN,
        )

        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_owner,
            role=OrganizationMembership.Role.OWNER,
        )

        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.other_technician,
            role=OrganizationMembership.Role.TECHNICIAN,
        )

        self.customer = Customer.objects.create(
            organization=self.organization,
            customer_number="FIELD-API-CUST-001",
            first_name="Muhammad",
            last_name="Nabeel",
            phone="03007770001",
            address_line="API Field Street",
            city="Lahore",
        )

        self.other_customer = Customer.objects.create(
            organization=self.other_organization,
            customer_number="OTHER-API-CUST-001",
            first_name="Other",
            last_name="Customer",
            phone="03007770002",
            address_line="Other API Street",
            city="Karachi",
        )

        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Field API Fiber 50",
            code="FIELD-API-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="5000.00",
        )

        self.other_package = InternetPackage.objects.create(
            organization=self.other_organization,
            name="Other API Fiber",
            code="OTHER-API-50",
            download_speed_mbps=50,
            upload_speed_mbps=25,
            monthly_price="6000.00",
        )

        self.service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="FIELD-API-SRV-001",
            customer=self.customer,
            internet_package=self.package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.other_service = ServiceAccount.objects.create(
            organization=self.other_organization,
            service_number="OTHER-API-SRV-001",
            customer=self.other_customer,
            internet_package=self.other_package,
            status=ServiceAccount.Status.ACTIVE,
        )

        self.node = NetworkNode.objects.create(
            organization=self.organization,
            name="Field API Core Router",
            code="FIELD-API-RTR-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.100.0.1",
        )

        self.other_node = NetworkNode.objects.create(
            organization=self.other_organization,
            name="Other API Router",
            code="OTHER-API-RTR-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.110.0.1",
        )

        self.complaint = Complaint.objects.create(
            organization=self.organization,
            complaint_number="FIELD-API-CMP-001",
            customer=self.customer,
            service_account=self.service,
            category=Complaint.Category.CONNECTIVITY,
            priority=Complaint.Priority.HIGH,
            status=Complaint.Status.OPEN,
            subject="API connectivity complaint",
            description="Field API visit required.",
            created_by=self.owner,
        )

        self.incident = Incident.objects.create(
            organization=self.organization,
            incident_number="FIELD-API-INC-001",
            network_node=self.node,
            title="API network degradation",
            description="Field API inspection required.",
            severity=Incident.Severity.MAJOR,
            status=Incident.Status.OPEN,
            started_at=__import__(
                "django.utils.timezone",
                fromlist=["now"],
            ).now(),
            created_by=self.owner,
        )

        self.client = APIClient()

        access_token = AccessToken.for_user(self.owner)
        access_token["organization_id"] = str(
            self.organization.id
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {str(access_token)}"
            )
        )

        self.other_client = APIClient()

        other_access_token = AccessToken.for_user(
            self.other_owner
        )
        other_access_token["organization_id"] = str(
            self.other_organization.id
        )

        self.other_client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {str(other_access_token)}"
            )
        )

    def create_api_work_order(
        self,
        *,
        title="Restore API customer connectivity",
        priority=WorkOrder.Priority.HIGH,
    ):
        response = self.client.post(
            "/api/v1/field-operations/work-orders/",
            {
                "customer_id": str(self.customer.id),
                "service_account_id": str(self.service.id),
                "network_node_id": str(self.node.id),
                "complaint_id": str(self.complaint.id),
                "incident_id": str(self.incident.id),
                "work_type": WorkOrder.WorkType.REPAIR,
                "priority": priority,
                "title": title,
                "description": (
                    "Operational API field visit required."
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        return response

    def test_create_work_order_api(self):
        response = self.create_api_work_order()

        self.assertEqual(
            response.data["status"],
            WorkOrder.Status.CREATED,
        )
        self.assertEqual(
            response.data["customer_id"],
            str(self.customer.id),
        )
        self.assertEqual(
            response.data["service_account_id"],
            str(self.service.id),
        )
        self.assertEqual(
            response.data["network_node_id"],
            str(self.node.id),
        )
        self.assertEqual(
            response.data["complaint_id"],
            str(self.complaint.id),
        )
        self.assertEqual(
            response.data["incident_id"],
            str(self.incident.id),
        )
        self.assertEqual(
            response.data["created_by_email"],
            self.owner.email,
        )

        self.assertEqual(
            WorkOrder.objects.for_organization(
                self.organization
            ).count(),
            1,
        )

    def test_work_order_list_search_api(self):
        self.create_api_work_order(
            title="Unique Fiber Repair Alpha",
        )

        create_work_order(
            organization=self.organization,
            work_type=WorkOrder.WorkType.SITE_VISIT,
            priority=WorkOrder.Priority.LOW,
            title="General unrelated visit",
            description="General field inspection.",
            created_by=self.owner,
        )

        response = self.client.get(
            (
                "/api/v1/field-operations/work-orders/"
                "?search=Alpha"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["title"],
            "Unique Fiber Repair Alpha",
        )

    def test_work_order_status_filter_api(self):
        created_work_order = create_work_order(
            organization=self.organization,
            work_type=WorkOrder.WorkType.SITE_VISIT,
            priority=WorkOrder.Priority.MEDIUM,
            title="Created work order",
            description="Created status test.",
            created_by=self.owner,
        ).work_order

        assigned_work_order = create_work_order(
            organization=self.organization,
            work_type=WorkOrder.WorkType.REPAIR,
            priority=WorkOrder.Priority.HIGH,
            title="Assigned work order",
            description="Assigned status test.",
            created_by=self.owner,
        ).work_order

        assign_work_order_technician(
            organization=self.organization,
            work_order_id=assigned_work_order.id,
            technician_id=self.technician.id,
            actor=self.owner,
        )

        response = self.client.get(
            (
                "/api/v1/field-operations/work-orders/"
                "?status=ASSIGNED"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            str(assigned_work_order.id),
        )
        self.assertNotEqual(
            response.data[0]["id"],
            str(created_work_order.id),
        )

    def test_complete_work_order_api_lifecycle(self):
        create_response = self.create_api_work_order()

        work_order_id = create_response.data["id"]

        assignment_response = self.client.post(
            (
                "/api/v1/field-operations/work-orders/"
                f"{work_order_id}/assignments/"
            ),
            {
                "technician_id": str(self.technician.id),
            },
            format="json",
        )

        self.assertEqual(
            assignment_response.status_code,
            status.HTTP_200_OK,
            assignment_response.data,
        )
        self.assertEqual(
            assignment_response.data["status"],
            WorkOrder.Status.ASSIGNED,
        )

        dispatch_response = self.client.post(
            (
                "/api/v1/field-operations/work-orders/"
                f"{work_order_id}/dispatches/"
            ),
            {
                "dispatch_notes": (
                    "Technician dispatched through API."
                ),
            },
            format="json",
        )

        self.assertEqual(
            dispatch_response.status_code,
            status.HTTP_200_OK,
            dispatch_response.data,
        )
        self.assertEqual(
            dispatch_response.data["status"],
            WorkOrder.Status.DISPATCHED,
        )

        onsite_response = self.client.post(
            (
                "/api/v1/field-operations/work-orders/"
                f"{work_order_id}/onsite-transitions/"
            ),
            {
                "onsite_notes": (
                    "Technician reached site through API."
                ),
            },
            format="json",
        )

        self.assertEqual(
            onsite_response.status_code,
            status.HTTP_200_OK,
            onsite_response.data,
        )
        self.assertEqual(
            onsite_response.data["status"],
            WorkOrder.Status.ONSITE,
        )

        completion_response = self.client.post(
            (
                "/api/v1/field-operations/work-orders/"
                f"{work_order_id}/completions/"
            ),
            {
                "completion_notes": (
                    "Fiber connector replaced through API."
                ),
            },
            format="json",
        )

        self.assertEqual(
            completion_response.status_code,
            status.HTTP_200_OK,
            completion_response.data,
        )
        self.assertEqual(
            completion_response.data["status"],
            WorkOrder.Status.COMPLETED,
        )
        self.assertIsNotNone(
            completion_response.data["assigned_at"],
        )
        self.assertIsNotNone(
            completion_response.data["dispatched_at"],
        )
        self.assertIsNotNone(
            completion_response.data["onsite_at"],
        )
        self.assertIsNotNone(
            completion_response.data["completed_at"],
        )

        self.assertEqual(
            AuditLog.objects.filter(
                organization=self.organization,
                resource_type="WorkOrder",
            ).count(),
            5,
        )

    def test_invalid_api_lifecycle_transition_is_blocked(self):
        create_response = self.create_api_work_order()

        work_order_id = create_response.data["id"]

        response = self.client.post(
            (
                "/api/v1/field-operations/work-orders/"
                f"{work_order_id}/completions/"
            ),
            {
                "completion_notes": "Invalid direct completion.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.data,
        )
        self.assertIn(
            "Only an onsite work order",
            response.data["detail"],
        )

        work_order = WorkOrder.objects.get(
            id=work_order_id,
        )

        self.assertEqual(
            work_order.status,
            WorkOrder.Status.CREATED,
        )

    def test_cross_tenant_work_order_detail_returns_404(self):
        other_work_order = create_work_order(
            organization=self.other_organization,
            customer_id=self.other_customer.id,
            service_account_id=self.other_service.id,
            network_node_id=self.other_node.id,
            work_type=WorkOrder.WorkType.REPAIR,
            priority=WorkOrder.Priority.HIGH,
            title="Other tenant work order",
            description="Other tenant field work.",
            created_by=self.other_owner,
        ).work_order

        response = self.client.get(
            (
                "/api/v1/field-operations/work-orders/"
                f"{other_work_order.id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            response.data,
        )

    def test_cross_tenant_technician_assignment_is_blocked(self):
        create_response = self.create_api_work_order()

        work_order_id = create_response.data["id"]

        response = self.client.post(
            (
                "/api/v1/field-operations/work-orders/"
                f"{work_order_id}/assignments/"
            ),
            {
                "technician_id": str(
                    self.other_technician.id
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.data,
        )
        self.assertIn(
            "Active technician membership was not found",
            response.data["detail"],
        )

        work_order = WorkOrder.objects.get(
            id=work_order_id,
        )

        self.assertEqual(
            work_order.status,
            WorkOrder.Status.CREATED,
        )
        self.assertIsNone(
            work_order.assigned_technician_id,
        )

    def test_unauthenticated_work_order_api_is_blocked(self):
        client = APIClient()

        response = client.get(
            "/api/v1/field-operations/work-orders/"
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )