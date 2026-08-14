import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from communications.models import (
    CommunicationLog,
    CommunicationQueue,
)
from communications.providers.factory import ProviderFactory


logger = logging.getLogger(__name__)


class CommunicationDispatcher:
    """
    Processes pending communication queue items safely.

    Handles:
    - scheduled messages
    - retry timing
    - maximum retry attempts
    - stale PROCESSING jobs
    - provider failures
    """

    PROCESSING_TIMEOUT_MINUTES = 10
    RETRY_BACKOFF_MINUTES = 5

    @classmethod
    def dispatch_next(cls):
        """
        Pick the next communication that is ready to be processed.
        """

        now = timezone.now()

        with transaction.atomic():
            cls.recover_stale_processing(now)

            # First-time queue items:
            # next_retry_at is NULL.
            queue = (
                CommunicationQueue.objects
                .select_related("provider")
                .select_for_update(skip_locked=True)
                .filter(
                    status=CommunicationQueue.Status.PENDING,
                    scheduled_at__lte=now,
                    next_retry_at__isnull=True,
                )
                .order_by(
                    "priority",
                    "created_at",
                )
                .first()
            )

            # Retry items:
            # only process them after next_retry_at.
            if queue is None:
                queue = (
                    CommunicationQueue.objects
                    .select_related("provider")
                    .select_for_update(skip_locked=True)
                    .filter(
                        status=CommunicationQueue.Status.PENDING,
                        scheduled_at__lte=now,
                        next_retry_at__lte=now,
                    )
                    .order_by(
                        "priority",
                        "created_at",
                    )
                    .first()
                )

            if queue is None:
                return None

            queue.status = CommunicationQueue.Status.PROCESSING
            queue.processing_started_at = now

            queue.save(
                update_fields=[
                    "status",
                    "processing_started_at",
                ]
            )

        return cls.process(queue)

    @classmethod
    def recover_stale_processing(cls, now):
        """
        Recover queue items that have been stuck in PROCESSING.
        """

        cutoff = now - timedelta(
            minutes=cls.PROCESSING_TIMEOUT_MINUTES
        )

        stale_items = CommunicationQueue.objects.filter(
            status=CommunicationQueue.Status.PROCESSING,
            processing_started_at__lt=cutoff,
        )

        for queue in stale_items:
            queue.status = CommunicationQueue.Status.PENDING
            queue.processing_started_at = None
            queue.next_retry_at = now
            queue.last_error = (
                "Recovered stale processing queue item."
            )

            queue.save(
                update_fields=[
                    "status",
                    "processing_started_at",
                    "next_retry_at",
                    "last_error",
                ]
            )

    @classmethod
    def process(cls, queue):
        """
        Send one queue item through its configured provider.
        """

        try:
            provider = ProviderFactory.get(queue.provider)

            result = provider.send(
                recipient=queue.recipient,
                subject=queue.rendered_subject,
                message=queue.rendered_body,
                provider=queue.provider,
            )

        except Exception as exc:
            logger.exception(
                "Communication %s provider error.",
                queue.id,
            )

            result = {
                "success": False,
                "error": str(exc),
                "response": {},
            }

        if result.get("success"):
            return cls.mark_success(queue, result)

        return cls.mark_failure(queue, result)

    @classmethod
    def mark_success(cls, queue, result):
        """
        Mark communication as successfully delivered.
        """

        now = timezone.now()

        queue.status = CommunicationQueue.Status.SENT
        queue.sent_at = now
        queue.processed_at = now
        queue.processing_started_at = None
        queue.next_retry_at = None
        queue.provider_response = result.get(
            "response",
            {},
        )

        queue.save(
            update_fields=[
                "status",
                "sent_at",
                "processed_at",
                "processing_started_at",
                "next_retry_at",
                "provider_response",
            ]
        )

        CommunicationLog.objects.filter(
            queue=queue,
        ).update(
            status=CommunicationLog.Status.DELIVERED,
            delivered_at=now,
            provider_message_id=result.get(
                "provider_message_id",
                "",
            ),
            provider_response=str(
                result.get("response", {})
            ),
        )

        logger.info(
            "Communication %s delivered successfully.",
            queue.id,
        )

        return True

    @classmethod
    def mark_failure(cls, queue, result):
        """
        Record a failed attempt and schedule a retry
        when attempts remain.
        """

        now = timezone.now()

        queue.attempts += 1
        queue.retry_count = queue.attempts

        queue.last_error = result.get(
            "error",
            "Communication provider failed.",
        )

        queue.error_message = queue.last_error

        queue.provider_response = result.get(
            "response",
            {},
        )

        queue.processing_started_at = None

        if queue.attempts >= queue.max_attempts:
            queue.status = CommunicationQueue.Status.FAILED
            queue.next_retry_at = None

        else:
            queue.status = CommunicationQueue.Status.PENDING

            backoff_minutes = (
                cls.RETRY_BACKOFF_MINUTES
                * (2 ** max(queue.attempts - 1, 0))
            )

            queue.next_retry_at = (
                now + timedelta(
                    minutes=backoff_minutes
                )
            )

        queue.save(
            update_fields=[
                "attempts",
                "retry_count",
                "last_error",
                "error_message",
                "provider_response",
                "processing_started_at",
                "status",
                "next_retry_at",
            ]
        )

        CommunicationLog.objects.filter(
            queue=queue,
        ).update(
            status=CommunicationLog.Status.FAILED,
            retry_count=queue.attempts,
            last_retry_at=now,
            error_message=queue.last_error,
            provider_response=str(
                queue.provider_response
            ),
        )

        logger.error(
            "Communication %s failed: %s",
            queue.id,
            queue.last_error,
        )

        return False