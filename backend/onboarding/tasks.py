import logging

from celery import shared_task

from onboarding.platform_services import enforce_subscription_expiry, send_subscription_reminders

logger = logging.getLogger(__name__)


@shared_task
def enforce_isp_subscriptions_task():
    """Daily: email fee reminders, then lock ISPs unpaid past the grace period."""
    reminders = send_subscription_reminders()
    if reminders["failed"]:
        logger.warning("Subscription reminder email failed for: %s", ", ".join(reminders["failed"]))
    result = enforce_subscription_expiry()
    if result["locked_count"]:
        logger.warning("Locked ISPs for unpaid subscription: %s", ", ".join(result["locked"]))
    return {"reminders": reminders, **result}
