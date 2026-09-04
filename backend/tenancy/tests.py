from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from tenancy.base_models import TenantScopedQuerySet
from tenancy.models import Organization, OrganizationMembership
from tenancy.models import AuditLog
from tenancy.services import record_audit_log


User = get_user_model()


class TenantRolePermissionTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Security Test ISP",
            code="SECURITY-TEST",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.owner = User.objects.create_user(
            username="security-owner",
            email="security-owner@nexora.local",
            password="StrongTestPassword123!",
        )

        self.staff = User.objects.create_user(
            username="security-staff",
            email="security-staff@nexora.local",
            password="StrongTestPassword123!",
        )

        self.technician = User.objects.create_user(
            username="security-technician",
            email="security-technician@nexora.local",
            password="StrongTestPassword123!",
        )

        self.owner_membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )

        self.staff_membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.staff,
            role=OrganizationMembership.Role.STAFF,
        )

        self.technician_membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.technician,
            role=OrganizationMembership.Role.TECHNICIAN,
        )

        self.login_url = reverse("tenant-login")
        self.owner_check_url = reverse("owner-security-check")

    def login(self, email):
        response = self.client.post(
            self.login_url,
            {
                "email": email,
                "password": "StrongTestPassword123!",
                "organization_code": self.organization.code,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        return response.data["access"]

    def test_owner_can_access_owner_only_endpoint(self):
        access_token = self.login(self.owner.email)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.get(self.owner_check_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["detail"],
            "OWNER ACCESS GRANTED",
        )

        self.assertEqual(
            response.data["role"],
            OrganizationMembership.Role.OWNER,
        )

    def test_staff_cannot_access_owner_only_endpoint(self):
        access_token = self.login(self.staff.email)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.get(self.owner_check_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_technician_cannot_access_tenant_administration(self):
        access_token = self.login(self.technician.email)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.get(self.owner_check_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_deactivated_membership_invalidates_issued_jwt(self):
        access_token = self.login(self.owner.email)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        initial_response = self.client.get(self.owner_check_url)

        self.assertEqual(
            initial_response.status_code,
            status.HTTP_200_OK,
        )

        self.owner_membership.is_active = False
        self.owner_membership.save(
            update_fields=["is_active"]
        )

        response = self.client.get(self.owner_check_url)

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )

    def test_deactivated_organization_invalidates_tenant_access(self):
        access_token = self.login(self.owner.email)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        initial_response = self.client.get(self.owner_check_url)

        self.assertEqual(
            initial_response.status_code,
            status.HTTP_200_OK,
        )

        self.organization.is_active = False
        self.organization.save(
            update_fields=["is_active"]
        )

        response = self.client.get(self.owner_check_url)

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )


class TenantQuerysetIsolationTests(APITestCase):
    def setUp(self):
        self.organization_a = Organization.objects.create(
            name="ISP A",
            code="ISP-A",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.organization_b = Organization.objects.create(
            name="ISP B",
            code="ISP-B",
            city="Karachi",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.user_a = User.objects.create_user(
            username="isp-a-owner",
            email="owner@ispa.local",
            password="StrongTestPassword123!",
        )

        self.user_b = User.objects.create_user(
            username="isp-b-owner",
            email="owner@ispb.local",
            password="StrongTestPassword123!",
        )

        self.record_a = OrganizationMembership.objects.create(
            organization=self.organization_a,
            user=self.user_a,
            role=OrganizationMembership.Role.OWNER,
        )

        self.record_b = OrganizationMembership.objects.create(
            organization=self.organization_b,
            user=self.user_b,
            role=OrganizationMembership.Role.OWNER,
        )

    def tenant_queryset(self):
        return TenantScopedQuerySet(
            model=OrganizationMembership,
            using="default",
        )

    def test_tenant_scoped_queryset_returns_only_supplied_organization(self):
        isp_a_records = self.tenant_queryset().for_organization(
            self.organization_a
        )

        isp_b_records = self.tenant_queryset().for_organization(
            self.organization_b
        )

        self.assertEqual(isp_a_records.count(), 1)
        self.assertEqual(isp_b_records.count(), 1)

        self.assertEqual(
            isp_a_records.first().organization,
            self.organization_a,
        )

        self.assertEqual(
            isp_b_records.first().organization,
            self.organization_b,
        )

    def test_isp_a_cannot_query_isp_b_record_through_tenant_scope(self):
        isp_a_records = self.tenant_queryset().for_organization(
            self.organization_a
        )

        self.assertTrue(
            isp_a_records.filter(pk=self.record_a.pk).exists()
        )

        self.assertFalse(
            isp_a_records.filter(pk=self.record_b.pk).exists()
        )

        


class AuditLogServiceTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Audit Test ISP",
            code="AUDIT-TEST",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.actor = User.objects.create_user(
            username="audit-owner",
            email="audit-owner@nexora.local",
            password="StrongTestPassword123!",
        )

    def test_record_audit_log_creates_tenant_audit_record(self):
        audit_log = record_audit_log(
            organization=self.organization,
            actor=self.actor,
            action="TENANT_SECURITY_TEST",
            resource_type="Organization",
            resource_id=self.organization.id,
            metadata={
                "source": "automated-test",
            },
        )

        self.assertEqual(AuditLog.objects.count(), 1)

        self.assertEqual(
            audit_log.organization,
            self.organization,
        )

        self.assertEqual(
            audit_log.actor,
            self.actor,
        )

        self.assertEqual(
            audit_log.action,
            "TENANT_SECURITY_TEST",
        )

        self.assertEqual(
            audit_log.resource_type,
            "Organization",
        )

        self.assertEqual(
            audit_log.resource_id,
            str(self.organization.id),
        )

        self.assertEqual(
            audit_log.metadata["source"],
            "automated-test",
        )

    def test_record_audit_log_requires_action(self):
        with self.assertRaises(ValueError):
            record_audit_log(
                organization=self.organization,
                actor=self.actor,
                action="   ",
                resource_type="Organization",
            )

    def test_record_audit_log_requires_resource_type(self):
        with self.assertRaises(ValueError):
            record_audit_log(
                organization=self.organization,
                actor=self.actor,
                action="TENANT_SECURITY_TEST",
                resource_type="   ",
            )


class Batch3CompanyProfileTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Prime Broadband",
            code="PRIME-BB",
            city="Rawalpindi",
            timezone="Asia/Karachi",
            currency="PKR",
            phone="+923001234567",
            email="contact@prime.local",
            address="Building 4, Commercial Market",
        )
        self.owner = User.objects.create_user(
            username="prime-owner@nexora.local",
            email="prime-owner@nexora.local",
            password="StrongPassword123!",
        )
        self.staff = User.objects.create_user(
            username="prime-staff@nexora.local",
            email="prime-staff@nexora.local",
            password="StrongPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.staff,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )

    def auth(self, user):
        login_res = self.client.post(
            reverse("tenant-login"),
            {
                "organization_code": self.organization.code,
                "email": user.email,
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_owner_and_staff_can_view_company_profile(self):
        self.auth(self.staff)
        res = self.client.get(reverse("organization-profile"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Prime Broadband")
        self.assertEqual(res.data["code"], "PRIME-BB")
        self.assertEqual(res.data["phone"], "+923001234567")
        self.assertEqual(res.data["email"], "contact@prime.local")

    def test_owner_can_update_company_profile(self):
        self.auth(self.owner)
        res = self.client.patch(
            reverse("organization-profile"),
            {
                "name": "Prime Fiber Broadband",
                "phone": "+923009876543",
                "address": "Plaza 12, Civic Center",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Prime Fiber Broadband")
        self.assertEqual(res.data["phone"], "+923009876543")

    def test_staff_cannot_update_company_profile(self):
        self.auth(self.staff)
        res = self.client.patch(
            reverse("organization-profile"),
            {"name": "Hacked Name"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class StaffAndOperatorManagementTests(APITestCase):
    def setUp(self):
        self.org1 = Organization.objects.create(
            name="Alpha Telecom",
            code="ALPHA",
            currency="PKR",
        )
        self.org2 = Organization.objects.create(
            name="Beta Net",
            code="BETA",
            currency="PKR",
        )
        self.owner1 = User.objects.create_user(
            username="owner@alpha.local",
            email="owner@alpha.local",
            password="StrongPassword123!",
            first_name="Alpha",
            last_name="Owner",
        )
        self.membership1 = OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.owner1,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        self.owner2 = User.objects.create_user(
            username="owner@beta.local",
            email="owner@beta.local",
            password="StrongPassword123!",
            first_name="Beta",
            last_name="Owner",
        )
        self.membership2 = OrganizationMembership.objects.create(
            organization=self.org2,
            user=self.owner2,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

    def auth(self, org, user):
        login_res = self.client.post(
            reverse("tenant-login"),
            {
                "organization_code": org.code,
                "email": user.email,
                "password": "StrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_create_staff_member_with_full_profile(self):
        self.auth(self.org1, self.owner1)
        res = self.client.post(
            reverse("organization-staff-list-create"),
            {
                "first_name": "Tariq",
                "last_name": "Mahmood",
                "email": "tariq.recovery@alpha.local",
                "password": "RecoveryPass123!",
                "role": "RECOVERY_OFFICER",
                "phone": "+923001112233",
                "cnic": "35201-1111111-1",
                "department": "Recovery & Collections",
                "designation": "Field Recovery Officer",
                "notes": "Allocated to Gulberg sector",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["full_name"], "Tariq Mahmood")
        self.assertEqual(res.data["operational_role"], "RECOVERY_OFFICER")
        self.assertEqual(res.data["department"], "Recovery & Collections")
        self.assertEqual(res.data["phone"], "+923001112233")
        self.assertTrue(res.data["staff_code"].startswith("ALPHA-STF-"))

    def test_update_staff_profile(self):
        self.auth(self.org1, self.owner1)
        create_res = self.client.post(
            reverse("organization-staff-list-create"),
            {
                "first_name": "Zaid",
                "last_name": "Ali",
                "email": "zaid@alpha.local",
                "password": "Password123!",
                "role": "OPERATOR",
                "phone": "+923002223344",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        membership_id = create_res.data["id"]

        update_res = self.client.patch(
            reverse("organization-staff-detail", kwargs={"membership_id": membership_id}),
            {
                "first_name": "Zaid Ahmed",
                "designation": "Senior Desk Operator",
                "department": "Operations",
            },
            format="json",
        )
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        self.assertEqual(update_res.data["full_name"], "Zaid Ahmed Ali")
        self.assertEqual(update_res.data["designation"], "Senior Desk Operator")
        self.assertEqual(update_res.data["department"], "Operations")

    def test_staff_status_transitions(self):
        self.auth(self.org1, self.owner1)
        create_res = self.client.post(
            reverse("organization-staff-list-create"),
            {
                "first_name": "Hamza",
                "last_name": "Khan",
                "email": "hamza@alpha.local",
                "password": "Password123!",
                "role": "TECHNICIAN",
            },
            format="json",
        )
        membership_id = create_res.data["id"]

        # Suspend staff
        res_suspend = self.client.patch(
            reverse("organization-staff-status", kwargs={"membership_id": membership_id}),
            {"status": "SUSPENDED"},
            format="json",
        )
        self.assertEqual(res_suspend.status_code, status.HTTP_200_OK)
        self.assertEqual(res_suspend.data["status"], "SUSPENDED")
        self.assertFalse(res_suspend.data["is_active"])

        # Reactivate staff
        res_active = self.client.patch(
            reverse("organization-staff-status", kwargs={"membership_id": membership_id}),
            {"status": "ACTIVE"},
            format="json",
        )
        self.assertEqual(res_active.status_code, status.HTTP_200_OK)
        self.assertEqual(res_active.data["status"], "ACTIVE")
        self.assertTrue(res_active.data["is_active"])

    def test_operator_list_and_workload(self):
        self.auth(self.org1, self.owner1)
        create_res = self.client.post(
            reverse("organization-staff-list-create"),
            {
                "first_name": "Usman",
                "last_name": "Recovery",
                "email": "usman.rec@alpha.local",
                "password": "Password123!",
                "role": "RECOVERY_OFFICER",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        user_id = create_res.data["user_id"]

        # Check operator list
        op_list_res = self.client.get(reverse("operator-list"))
        self.assertEqual(op_list_res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(op_list_res.data) >= 2)

        # Check workload detail
        workload_res = self.client.get(reverse("operator-workload-detail", kwargs={"user_id": user_id}))
        self.assertEqual(workload_res.status_code, status.HTTP_200_OK)
        self.assertEqual(workload_res.data["workload"]["total_assigned"], 0)
        self.assertEqual(workload_res.data["workload"]["outstanding_assigned_amount"], "0.00")

    def test_cross_tenant_staff_isolation(self):
        # Create staff in Org 1
        self.auth(self.org1, self.owner1)
        create_res = self.client.post(
            reverse("organization-staff-list-create"),
            {
                "first_name": "Private",
                "last_name": "Staff",
                "email": "private@alpha.local",
                "password": "Password123!",
                "role": "STAFF",
            },
            format="json",
        )
        membership_id = create_res.data["id"]

        # Org 2 attempts to access Org 1 staff
        self.auth(self.org2, self.owner2)
        get_res = self.client.get(reverse("organization-staff-detail", kwargs={"membership_id": membership_id}))
        self.assertEqual(get_res.status_code, status.HTTP_404_NOT_FOUND)
