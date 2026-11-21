from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.models import Organization, OrganizationMembership

User = get_user_model()
PASSWORD = "Sign-In!2345"


class EmailOnlyLoginTests(TestCase):
    """People sign in with email + password; the organization code is optional."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.org = Organization.objects.create(name="Alpha Net", code="ALPHA", city="Lahore")
        self.user = User.objects.create_user(username="owner@alpha.test", email="owner@alpha.test", password=PASSWORD)
        self.membership = OrganizationMembership.objects.create(
            organization=self.org, user=self.user, role=OrganizationMembership.Role.OWNER, is_active=True,
        )

    def tearDown(self):
        cache.clear()

    def login(self, **body):
        return self.client.post("/api/v1/auth/login/", {"email": "owner@alpha.test", "password": PASSWORD, **body},
                                format="json")

    def test_email_and_password_are_enough(self):
        response = self.login()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["organization"]["code"], "ALPHA")
        self.assertEqual(response.data["role"], "OWNER")

    def test_old_clients_sending_the_code_still_work(self):
        self.assertEqual(self.login(organization_code="ALPHA").status_code, 200)
        self.assertEqual(self.login(organization_code="alpha").status_code, 200)
        self.assertEqual(self.login(organization_code="OTHER").status_code, 400)

    def test_wrong_password_is_refused(self):
        self.assertEqual(self.login(password="wrong-password").status_code, 400)

    def test_inactive_membership_is_refused(self):
        self.membership.is_active = False
        self.membership.save(update_fields=["is_active"])
        self.assertEqual(self.login().status_code, 400)

    def test_email_in_two_isps_is_not_guessed(self):
        other = Organization.objects.create(name="Beta Net", code="BETA", city="Lahore")
        OrganizationMembership.objects.create(
            organization=other, user=self.user, role=OrganizationMembership.Role.STAFF, is_active=True,
        )
        response = self.login()
        self.assertEqual(response.status_code, 400)
        self.assertIn("more than one ISP", str(response.data))
        # With the code it is clear which one.
        self.assertEqual(self.login(organization_code="BETA").data["role"], "STAFF")
