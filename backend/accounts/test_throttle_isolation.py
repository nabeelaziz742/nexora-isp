from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient


class LoginThrottleIsolationTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.payload = {
            "email": "unknown@example.com",
            "password": "invalid-password",
            "organization_code": "UNKNOWN",
        }

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_rejected_login_does_not_leak_throttle_state_to_next_test(self):
        for _ in range(5):
            response = self.client.post(
                "/api/v1/auth/login/",
                self.payload,
                format="json",
            )
            self.assertNotEqual(
                response.status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        rejected = self.client.post(
            "/api/v1/auth/login/",
            self.payload,
            format="json",
        )
        self.assertEqual(
            rejected.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

        cache.clear()

        next_test_request = self.client.post(
            "/api/v1/auth/login/",
            self.payload,
            format="json",
        )
        self.assertNotEqual(
            next_test_request.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
