import logging

from communications.dispatcher import (
    CommunicationDispatcher,
)

logger = logging.getLogger(__name__)


def process_pending_communications():
    """
    Process all pending communication queue items.

    Can be called by:
    - Cron Job
    - Celery Beat
    - Management Command
    - Background Scheduler
    """

    processed = 0

    while True:

        result = CommunicationDispatcher.dispatch_next()

        if result is None:
            break

        processed += 1

    logger.info(
        "Processed %s communication(s).",
        processed,
    )

    return processed