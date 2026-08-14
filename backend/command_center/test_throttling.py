from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from command_center.throttles import CopilotRateThrottle


class CopilotRateThrottleTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()
        self.throttle = CopilotRateThrottle()
        self.throttle.rate = "10/minute"
        self.throttle.num_requests = 10
        self.throttle.duration = 60

    def tearDown(self):
        cache.clear()

    def test_copilot_throttle_allows_ten_and_rejects_eleventh(self):
        request = self.factory.post(
            "/api/v1/command-center/copilot/ask/",
            {"question": "What needs attention?"},
            format="json",
        )
        request.user = type(
            "AuthenticatedUser",
            (),
            {"pk": 12345, "is_authenticated": True},
        )()

        allowed = [
            self.throttle.allow_request(request, None)
            for _ in range(10)
        ]

        self.assertEqual(allowed, [True] * 10)
        self.assertFalse(
            self.throttle.allow_request(request, None)
        )
