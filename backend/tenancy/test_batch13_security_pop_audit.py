from datetime import date
from decimal import Decimal
import json
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounting.models import Account, FinancialPeriod, JournalEntry
from accounting.services import close_financial_period, create_journal_entry, get_or_create_default_chart_of_accounts
from billing.models import Invoice, Payment
from billing.services import cancel_invoice, generate_custom_invoice, record_payment_with_allocations, reverse_payment
from customers.models import Area, City, Customer, ServiceAccount
from inventory.models import InventoryItem, PosSale
from inventory.services import create_pos_sale, record_stock_adjustment
from network.models import NetworkAssignment, NetworkNode, PointOfPresence
from network.services import create_pop_site, get_pop_statistics, update_pop_site
from tenancy.models import AuditLog, Organization, OrganizationMembership, StaffProfile
from tenancy.permissions import get_effective_role

User = get_user_model()


class Batch13SecurityPopAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Tenant 1 (Primary)
        self.org1 = Organization.objects.create(
            name="Nexora Alpha Telecom",
            code="NEXORA-ALPHA",
            currency="PKR",
            timezone="Asia/Karachi",
            is_active=True,
        )
        self.city1 = City.objects.create(organization=self.org1, name="Lahore")
        self.area1 = Area.objects.create(organization=self.org1, city=self.city1, name="Gulberg")

        # Tenant 2 (Isolation Check)
        self.org2 = Organization.objects.create(
            name="Beta FiberNet",
            code="BETA-FIBER",
            currency="PKR",
            timezone="Asia/Karachi",
            is_active=True,
        )
        self.city2 = City.objects.create(organization=self.org2, name="Karachi")
        self.area2 = Area.objects.create(organization=self.org2, city=self.city2, name="Clifton")

        # Users & Memberships for Org1
        self.owner_user = User.objects.create_user(username="owner_alpha", email="owner@alpha.com", password="password123", first_name="Owner", last_name="User")
        self.owner_membership = OrganizationMembership.objects.create(
            user=self.owner_user,
            organization=self.org1,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

        self.admin_user = User.objects.create_user(username="admin_alpha", email="admin@alpha.com", password="password123", first_name="Admin", last_name="User")
        self.admin_membership = OrganizationMembership.objects.create(
            user=self.admin_user,
            organization=self.org1,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.admin_profile = StaffProfile.objects.create(
            organization=self.org1,
            user=self.admin_user,
            membership=self.admin_membership,
            staff_code="STF-ADM-01",
            role=StaffProfile.Role.ADMIN,
        )

        self.accountant_user = User.objects.create_user(username="accountant_alpha", email="accountant@alpha.com", password="password123", first_name="Acc", last_name="User")
        self.accountant_membership = OrganizationMembership.objects.create(
            user=self.accountant_user,
            organization=self.org1,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.accountant_profile = StaffProfile.objects.create(
            organization=self.org1,
            user=self.accountant_user,
            membership=self.accountant_membership,
            staff_code="STF-ACC-01",
            role=StaffProfile.Role.ACCOUNTANT,
        )

        self.tech_user = User.objects.create_user(username="tech_alpha", email="tech@alpha.com", password="password123", first_name="Tech", last_name="User")
        self.tech_membership = OrganizationMembership.objects.create(
            user=self.tech_user,
            organization=self.org1,
            role=OrganizationMembership.Role.TECHNICIAN,
            is_active=True,
        )
        self.tech_profile = StaffProfile.objects.create(
            organization=self.org1,
            user=self.tech_user,
            membership=self.tech_membership,
            staff_code="STF-TCH-01",
            role=StaffProfile.Role.TECHNICIAN,
        )

        self.recovery_user = User.objects.create_user(username="recovery_alpha", email="recovery@alpha.com", password="password123", first_name="Recovery", last_name="User")
        self.recovery_membership = OrganizationMembership.objects.create(
            user=self.recovery_user,
            organization=self.org1,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.recovery_profile = StaffProfile.objects.create(
            organization=self.org1,
            user=self.recovery_user,
            membership=self.recovery_membership,
            staff_code="STF-REC-01",
            role=StaffProfile.Role.RECOVERY_OFFICER,
        )

        self.staff_user = User.objects.create_user(username="staff_alpha", email="staff@alpha.com", password="password123", first_name="Staff", last_name="User")
        self.staff_membership = OrganizationMembership.objects.create(
            user=self.staff_user,
            organization=self.org1,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        self.staff_profile = StaffProfile.objects.create(
            organization=self.org1,
            user=self.staff_user,
            membership=self.staff_membership,
            staff_code="STF-GEN-01",
            role=StaffProfile.Role.STAFF,
        )

        # Tenant 2 User
        self.org2_owner = User.objects.create_user(username="owner_beta", email="owner@beta.com", password="password123", first_name="Beta", last_name="Owner")
        self.org2_membership = OrganizationMembership.objects.create(
            user=self.org2_owner,
            organization=self.org2,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

    def _auth(self, user, org, membership):
        self.client.force_authenticate(user=None)
        if hasattr(self.client.handler, "_force_user"):
            self.client.handler._force_user = None
        res = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "password123", "organization_code": org.code},
            format="json",
        )
        if res.status_code == 200:
            token = res.data["access"]
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        else:
            self.client.credentials()

    # ==========================================================================
    # 1. POP CREATION, UNIQUENESS & VALIDATION
    # ==========================================================================
    def test_01_pop_creation_and_code_uniqueness(self):
        pop = create_pop_site(
            organization=self.org1,
            actor=self.owner_user,
            code="POP-GLB-01",
            name="Gulberg Central Tower",
            pop_type=PointOfPresence.PopType.CORE,
            area_id=self.area1.id,
            address="12 Main Boulevard, Gulberg, Lahore",
            latitude=Decimal("31.520370"),
            longitude=Decimal("74.358747"),
            rack_capacity_units=42,
            power_backup_type="SOLAR_UPS_GENERATOR",
            status=PointOfPresence.Status.ACTIVE,
        )
        self.assertEqual(pop.code, "POP-GLB-01")
        self.assertEqual(pop.rack_capacity_units, 42)
        self.assertEqual(pop.area, self.area1)

        # Reject duplicate code in same org
        from network.services import PopDomainError
        with self.assertRaises(PopDomainError):
            create_pop_site(
                organization=self.org1,
                actor=self.owner_user,
                code="POP-GLB-01",
                name="Duplicate Code POP",
            )

        # Allow same code in a different org
        pop_org2 = create_pop_site(
            organization=self.org2,
            actor=self.org2_owner,
            code="POP-GLB-01",
            name="Beta POP in Karachi",
            area_id=self.area2.id,
        )
        self.assertEqual(pop_org2.code, "POP-GLB-01")
        self.assertEqual(pop_org2.organization, self.org2)

    def test_02_pop_cross_tenant_area_rejected(self):
        from network.services import PopDomainError
        with self.assertRaises(PopDomainError):
            # Attempt to attach Org2 Area to Org1 POP
            create_pop_site(
                organization=self.org1,
                actor=self.owner_user,
                code="POP-ERR-01",
                name="Cross Area POP",
                area_id=self.area2.id,
            )

    def test_03_pop_node_association_and_stats(self):
        pop = create_pop_site(
            organization=self.org1,
            actor=self.owner_user,
            code="POP-GLB-02",
            name="Gulberg Switch Site",
        )
        node = NetworkNode.objects.create(
            organization=self.org1,
            name="Gulberg Core Switch 1",
            code="SW-GLB-01",
            node_type=NetworkNode.NodeType.SWITCH,
            pop_site=pop,
        )
        self.assertEqual(node.pop_site, pop)
        self.assertIn(node, pop.nodes.all())

        stats = get_pop_statistics(organization=self.org1, pop=pop)
        self.assertEqual(stats["nodes_count"], 1)
        self.assertEqual(stats["active_subscribers_count"], 0)

    # ==========================================================================
    # 2. RBAC ROLE RESOLUTION
    # ==========================================================================
    def test_04_effective_role_resolution(self):
        class DummyRequest:
            def __init__(self, membership, role):
                self.organization_membership = membership
                self.organization_role = role

        req_owner = DummyRequest(self.owner_membership, OrganizationMembership.Role.OWNER)
        self.assertEqual(get_effective_role(req_owner), StaffProfile.Role.OWNER)

        req_admin = DummyRequest(self.admin_membership, OrganizationMembership.Role.STAFF)
        self.assertEqual(get_effective_role(req_admin), StaffProfile.Role.ADMIN)

        req_acc = DummyRequest(self.accountant_membership, OrganizationMembership.Role.STAFF)
        self.assertEqual(get_effective_role(req_acc), StaffProfile.Role.ACCOUNTANT)

        req_tech = DummyRequest(self.tech_membership, OrganizationMembership.Role.TECHNICIAN)
        self.assertEqual(get_effective_role(req_tech), StaffProfile.Role.TECHNICIAN)

        req_staff = DummyRequest(self.staff_membership, OrganizationMembership.Role.STAFF)
        self.assertEqual(get_effective_role(req_staff), StaffProfile.Role.STAFF)

    # ==========================================================================
    # 3. RBAC DENIALS (ACCOUNTING / BILLING / INVENTORY / POS)
    # ==========================================================================
    def test_05_accountant_can_access_accounting_tech_and_staff_denied(self):
        # 1. Accountant accesses Accounting Overview -> 200 OK
        self._auth(self.accountant_user, self.org1, self.accountant_membership)
        res = self.client.get("/api/v1/accounting/overview/")
        self.assertEqual(res.status_code, 200)

        # 2. Technician tries to access Accounting Overview -> 403 FORBIDDEN
        self._auth(self.tech_user, self.org1, self.tech_membership)
        res = self.client.get("/api/v1/accounting/overview/")
        self.assertEqual(res.status_code, 403)

        # 3. Ordinary Staff tries to access Accounting Overview -> 403 FORBIDDEN
        self._auth(self.staff_user, self.org1, self.staff_membership)
        res = self.client.get("/api/v1/accounting/overview/")
        self.assertEqual(res.status_code, 403)

        # 4. Recovery Officer tries to access Accounting Overview -> 403 FORBIDDEN
        self._auth(self.recovery_user, self.org1, self.recovery_membership)
        res = self.client.get("/api/v1/accounting/overview/")
        self.assertEqual(res.status_code, 403)

    def test_06_period_close_restricted_from_technician_and_staff(self):
        period = FinancialPeriod.objects.create(
            organization=self.org1,
            name="March 2026",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            is_closed=False,
        )

        # Technician attempt -> 403
        self._auth(self.tech_user, self.org1, self.tech_membership)
        res = self.client.post(f"/api/v1/accounting/periods/{period.id}/close/")
        self.assertEqual(res.status_code, 403)

        # Ordinary Staff attempt -> 403
        self._auth(self.staff_user, self.org1, self.staff_membership)
        res = self.client.post(f"/api/v1/accounting/periods/{period.id}/close/")
        self.assertEqual(res.status_code, 403)

    def test_07_inventory_adjustment_restricted(self):
        item = InventoryItem.objects.create(
            organization=self.org1,
            code="FIBER-CABLE-100M",
            name="100m Drop Cable",
            category=InventoryItem.Category.CABLES_CONNECTORS,
            unit_of_measure=InventoryItem.Unit.METERS,
            quantity_on_hand=Decimal("500"),
            unit_cost_price=Decimal("15.00"),
        )

        # Ordinary staff attempt to adjust inventory -> 403
        self._auth(self.staff_user, self.org1, self.staff_membership)
        res = self.client.post(
            f"/api/v1/inventory/items/{item.id}/adjust/",
            {"new_quantity": "600", "reason": "Audit correction"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

        # Admin attempt -> 200
        self._auth(self.admin_user, self.org1, self.admin_membership)
        res = self.client.post(
            f"/api/v1/inventory/items/{item.id}/adjust/",
            {"new_quantity": "600", "reason": "Audit correction"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

    # ==========================================================================
    # 4. AUDIT LOG API & INVESTIGATION
    # ==========================================================================
    def test_08_audit_log_access_and_filtering(self):
        # Create an audit event
        AuditLog.objects.create(
            organization=self.org1,
            actor=self.owner_user,
            action="SPECIAL_TEST_ACTION",
            resource_type="TestResource",
            resource_id="12345",
            metadata={"detail": "Audit security test"},
        )
        # Create an audit event for Org 2
        AuditLog.objects.create(
            organization=self.org2,
            actor=self.org2_owner,
            action="BETA_ISOLATION_ACTION",
            resource_type="TestResource",
            resource_id="99999",
            metadata={"detail": "Tenant 2 private log"},
        )

        # 1. Staff and Technician denied from querying Audit Logs -> 403
        self._auth(self.staff_user, self.org1, self.staff_membership)
        res = self.client.get("/api/v1/tenant/audit-logs/")
        self.assertEqual(res.status_code, 403)

        self._auth(self.tech_user, self.org1, self.tech_membership)
        res = self.client.get("/api/v1/tenant/audit-logs/")
        self.assertEqual(res.status_code, 403)

        # 2. Owner & Admin permitted -> 200
        self._auth(self.owner_user, self.org1, self.owner_membership)
        res = self.client.get("/api/v1/tenant/audit-logs/")
        self.assertEqual(res.status_code, 200)
        actions = [log["action"] for log in res.data]
        self.assertIn("SPECIAL_TEST_ACTION", actions)
        # Verify Org2 audit log is NOT in Org1 results (Tenant Isolation)
        self.assertNotIn("BETA_ISOLATION_ACTION", actions)

        # 3. Filter by action
        res_filtered = self.client.get("/api/v1/tenant/audit-logs/?action=SPECIAL_TEST_ACTION")
        self.assertEqual(res_filtered.status_code, 200)
        self.assertEqual(len(res_filtered.data), 1)
        self.assertEqual(res_filtered.data[0]["action"], "SPECIAL_TEST_ACTION")

    def test_09_login_and_company_profile_auditing(self):
        # Login audit log test
        initial_log_count = AuditLog.objects.filter(organization=self.org1, action="USER_LOGIN_SUCCESS").count()
        self.client.post(
            "/api/v1/auth/login/",
            {"email": "owner@alpha.com", "password": "password123", "organization_code": "NEXORA-ALPHA"},
            format="json",
        )
        post_login_count = AuditLog.objects.filter(organization=self.org1, action="USER_LOGIN_SUCCESS").count()
        self.assertEqual(post_login_count, initial_log_count + 1)

        # Company profile update audit test
        self._auth(self.owner_user, self.org1, self.owner_membership)
        patch_res = self.client.patch(
            "/api/v1/tenant/profile/",
            {"phone": "+92-42-35710000", "city": "Lahore Cantt"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.org1,
                action="COMPANY_PROFILE_UPDATED",
            ).exists()
        )

    # ==========================================================================
    # 5. POP REST API ENDPOINTS & TENANT ISOLATION
    # ==========================================================================
    def test_10_pop_rest_api_crud_and_tenant_isolation(self):
        # Admin creates POP via REST
        self._auth(self.admin_user, self.org1, self.admin_membership)
        res = self.client.post(
            "/api/v1/network/pops/",
            {
                "code": "POP-REST-01",
                "name": "Rest Created POP",
                "pop_type": "CORE",
                "area": str(self.area1.id),
                "rack_capacity_units": 48,
                "power_backup_type": "SOLAR_HYBRID",
                "status": "ACTIVE",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        pop_id = res.data["id"]
        self.assertEqual(res.data["code"], "POP-REST-01")

        # Org2 Owner attempts to view Org1 POP -> 404
        self._auth(self.org2_owner, self.org2, self.org2_membership)
        res_cross = self.client.get(f"/api/v1/network/pops/{pop_id}/")
        self.assertEqual(res_cross.status_code, 404)

        # Org1 Admin updates POP status
        self._auth(self.admin_user, self.org1, self.admin_membership)
        patch_res = self.client.patch(
            f"/api/v1/network/pops/{pop_id}/",
            {"status": "MAINTENANCE", "notes": "Upgrading core switch"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.data["status"], "MAINTENANCE")

        # Audit log verified
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.org1,
                action="POP_SITE_STATUS_CHANGED",
                resource_id=pop_id,
            ).exists()
        )
