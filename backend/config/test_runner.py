from copy import deepcopy

from django.conf import settings
from django.test.utils import override_settings
from django.test.runner import DiscoverRunner


class NexoraTestRunner(DiscoverRunner):
    """Keep production throttling strict without coupling unrelated tests."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        rest_framework = deepcopy(settings.REST_FRAMEWORK)
        rest_framework["DEFAULT_THROTTLE_RATES"] = {
            **rest_framework.get("DEFAULT_THROTTLE_RATES", {}),
            "login": "1000/minute",
            "copilot": "1000/minute",
        }
        self._throttle_test_settings = override_settings(
            REST_FRAMEWORK=rest_framework,
        )
        self._throttle_test_settings.enable()

    def teardown_test_environment(self, **kwargs):
        if hasattr(self, "_throttle_test_settings"):
            self._throttle_test_settings.disable()
            del self._throttle_test_settings
        super().teardown_test_environment(**kwargs)
