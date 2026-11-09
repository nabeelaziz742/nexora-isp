import logging

from celery import shared_task

from onboarding.platform_services import enforce_subscription_expiry

logger = logging.getLogger(__name__)


@shared_task
def enforce_isp_subscriptions_task():
    """Daily: lock ISPs whose subscription is unpaid past the grace period."""
    result = enforce_subscription_expiry()
    if result["locked_count"]:
        logger.warning("Locked ISPs for unpaid subscription: %s", ", ".join(result["locked"]))
    return result
