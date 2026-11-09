import re

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from tenancy.models import Organization, OrganizationMembership, StaffProfile
from tenancy.staff_services import get_or_create_staff_profile

OWNER_PW = "OwnerPass!2345"
STAFF_PW = "StaffPass!2345"
NEW_PW = "BrandNew!Pass987"


def make_member(org, email, password, role, profile_role=None):
    user = User.objects.create_user(username=email, email=email, password=password, first_name="Test")
    membership = OrganizationMembership.objects.create(organization=org, user=user, role=role, is_active=True)
    profile = get_or_create_staff_profile(membership)
    if profile_role:
        profile.role = profile_role
        profile.save()
    return user, membership


@override_settings(FRONTEND_BASE_URL="https://app.example.com")
class PasswordTests(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters are shared across tests
        self.client = APIClient()
        self.org = Organization.objects.create(name="Alpha Net", code="ALPHA", city="Lahore")
        self.owner, self.owner_m = make_member(self.org, "owner@alpha.test", OWNER_PW, "OWNER")
        self.admin, self.admin_m = make_member(self.org, "admin@alpha.test", STAFF_PW, "STAFF", StaffProfile.Role.ADMIN)
        self.operator, self.operator_m = make_member(self.org, "op@alpha.test", STAFF_PW, "STAFF", StaffProfile.Role.OPERATOR)

    def login(self, email, password):
        self.client.credentials()
        response = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": email, "password": password}, format="json")
        if response.status_code == 200:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    # -- change password -------------------------------------------------------

    def test_change_password_requires_current_password(self):
        self.login("op@alpha.test", STAFF_PW)
        wrong = self.client.post("/api/v1/auth/change-password/", {
            "current_password": "nope", "new_password": NEW_PW}, format="json")
        self.assertEqual(wrong.status_code, 400)
        ok = self.client.post("/api/v1/auth/change-password/", {
            "current_password": STAFF_PW, "new_password": NEW_PW}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.login("op@alpha.test", STAFF_PW).status_code, 400)
        self.assertEqual(self.login("op@alpha.test", NEW_PW).status_code, 200)

    def test_weak_new_password_is_refused(self):
        self.login("op@alpha.test", STAFF_PW)
        response = self.client.post("/api/v1/auth/change-password/", {
            "current_password": STAFF_PW, "new_password": "12345678"}, format="json")
        self.assertEqual(response.status_code, 400)

    # -- owner / admin resets a staff password ---------------------------------

    def reset(self, membership, password=NEW_PW):
        return self.client.post(
            f"/api/v1/tenant/staff/{membership.id}/reset-password/", {"new_password": password}, format="json")

    def test_owner_resets_staff_password(self):
        self.login("owner@alpha.test", OWNER_PW)
        self.assertEqual(self.reset(self.operator_m).status_code, 200)
        self.assertEqual(self.login("op@alpha.test", NEW_PW).status_code, 200)

    def test_operator_cannot_reset_passwords(self):
        self.login("op@alpha.test", STAFF_PW)
        self.assertEqual(self.reset(self.admin_m).status_code, 403)

    def test_admin_cannot_reset_owner_or_self(self):
        self.login("admin@alpha.test", STAFF_PW)
        self.assertEqual(self.reset(self.owner_m).status_code, 403)
        self.assertEqual(self.reset(self.admin_m).status_code, 403)
        self.assertEqual(self.reset(self.operator_m).status_code, 200)

    def test_only_owner_resets_an_admin(self):
        other_admin, other_m = make_member(self.org, "admin2@alpha.test", STAFF_PW, "STAFF", StaffProfile.Role.ADMIN)
        self.login("admin@alpha.test", STAFF_PW)
        self.assertEqual(self.reset(other_m).status_code, 403)
        self.login("owner@alpha.test", OWNER_PW)
        self.assertEqual(self.reset(other_m).status_code, 200)

    # -- forgot password -------------------------------------------------------

    def test_forgot_password_emails_a_working_link_once(self):
        response = self.client.post("/api/v1/auth/password-reset/", {"email": "OP@alpha.test"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("https://app.example.com/reset-password?uid=", body)
        uid, token = re.search(r"uid=([^&\s]+)&token=([^\s]+)", body).groups()

        confirm = self.client.post("/api/v1/auth/password-reset/confirm/", {
            "uid": uid, "token": token, "new_password": NEW_PW}, format="json")
        self.assertEqual(confirm.status_code, 200)
        self.assertEqual(self.login("op@alpha.test", NEW_PW).status_code, 200)

        # The same link cannot be used twice.
        again = self.client.post("/api/v1/auth/password-reset/confirm/", {
            "uid": uid, "token": token, "new_password": "Another!Pass654"}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_unknown_email_gets_same_answer_and_no_mail(self):
        known = self.client.post("/api/v1/auth/password-reset/", {"email": "op@alpha.test"}, format="json")
        unknown = self.client.post("/api/v1/auth/password-reset/", {"email": "ghost@alpha.test"}, format="json")
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_bad_token_is_refused(self):
        response = self.client.post("/api/v1/auth/password-reset/confirm/", {
            "uid": "MQ", "token": "bad-token", "new_password": NEW_PW}, format="json")
        self.assertEqual(response.status_code, 400)
