import logging
from celery import shared_task
from django.utils import timezone

from communications.dispatcher import CommunicationDispatcher
from communications.scheduler import CommunicationScheduleService

logger = logging.getLogger(__name__)


@shared_task
def dispatch_communication_queue_task(batch_size: int = 50):
    """
    Process ready communication queue items asynchronously up to batch_size.
    Uses select_for_update(skip_locked=True) internally to prevent duplicate dispatch.
    """
    processed = 0

    while processed < batch_size:
        result = CommunicationDispatcher.dispatch_next()
        if result is None:
            break
        processed += 1

    logger.info("Asynchronously dispatched %s communication(s).", processed)
    return {"dispatched_count": processed}


@shared_task
def recover_stale_processing_task(timeout_minutes: int = 15):
    """
    Recovers communication queue items stuck in PROCESSING status beyond timeout.
    """
    now = timezone.now()
    CommunicationDispatcher.recover_stale_processing(now)
    logger.info("Completed scheduled recovery of stale PROCESSING communication items.")
    return {"status": "recovered"}


@shared_task
def process_due_communication_schedules_task(limit: int = 100):
    """Queue all due communication schedules for their tenant's active customers."""
    processed = CommunicationScheduleService.process_due(limit=limit)
    logger.info("Queued %s communication schedule(s).", processed)
    return {"queued_schedules_count": processed}


def process_pending_communications():
    """Synchronous entry point maintained for backward compatibility."""
    return dispatch_communication_queue_task(batch_size=500)["dispatched_count"]


def process_due_communication_schedules(*, limit=100):
    """Synchronous entry point maintained for backward compatibility."""
    return process_due_communication_schedules_task(limit=limit)["queued_schedules_count"]

