import logging

from communications.dispatcher import CommunicationDispatcher
from communications.scheduler import CommunicationScheduleService

logger = logging.getLogger(__name__)


def process_pending_communications():
    """Process ready communication queue items until the queue is drained."""
    processed = 0

    while True:
        result = CommunicationDispatcher.dispatch_next()
        if result is None:
            break
        processed += 1

    logger.info("Processed %s communication(s).", processed)
    return processed


def process_due_communication_schedules(*, limit=100):
    """Queue all due communication schedules for their tenant's active customers."""
    processed = CommunicationScheduleService.process_due(limit=limit)
    logger.info("Queued %s communication schedule(s).", processed)
    return processed
