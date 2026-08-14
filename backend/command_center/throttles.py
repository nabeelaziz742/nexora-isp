from rest_framework.throttling import ScopedRateThrottle


class CopilotRateThrottle(ScopedRateThrottle):
    """Limit expensive AI Copilot requests per authenticated user."""

    scope = "copilot"

    def __init__(self):
        super().__init__()
        self.scope = "copilot"
