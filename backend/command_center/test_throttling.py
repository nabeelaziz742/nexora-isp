from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from command_center.throttles import CopilotRateThrottle
from command_center.views import OperationsCopilotAPIView


class CopilotRateThrottleTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()
        self.throttle = CopilotRateThrottle()
        self.view = OperationsCopilotAPIView()

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

        self.throttle.get_rate = lambda: "10/minute"
        allowed = [
            self.throttle.allow_request(request, self.view)
            for _ in range(10)
        ]

        self.assertEqual(allowed, [True] * 10)
        self.assertFalse(
            self.throttle.allow_request(request, self.view)
        )
