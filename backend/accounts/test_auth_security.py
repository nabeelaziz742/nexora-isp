from django.core.cache import cache
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch


class LoginThrottleTests(TestCase):
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

    def test_login_endpoint_is_rate_limited(self):
        with patch("rest_framework.throttling.ScopedRateThrottle.get_rate", return_value="5/minute"):
            responses = [
                self.client.post(
                    "/api/v1/auth/login/",
                    self.payload,
                    format="json",
                )
                for _ in range(6)
            ]

        self.assertTrue(
            all(
                response.status_code != status.HTTP_429_TOO_MANY_REQUESTS
                for response in responses[:5]
            )
        )
        self.assertEqual(
            responses[5].status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
