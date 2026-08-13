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