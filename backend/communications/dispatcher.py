import logging

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
    Processes pending communication queue items.
    """

    @classmethod
    def dispatch_next(cls):
        """
        Pick next pending queue item.
        """

        with transaction.atomic():

            queue = (
                CommunicationQueue.objects
                .select_related("provider")
                .select_for_update(skip_locked=True)
                .filter(
                    status=CommunicationQueue.Status.PENDING,
                    scheduled_at__lte=timezone.now(),
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
            queue.processing_started_at = timezone.now()

            queue.save(
                update_fields=[
                    "status",
                    "processing_started_at",
                ]
            )

        return cls.process(queue)

    @classmethod
    def process(cls, queue):

        provider = ProviderFactory.get(queue.provider)

        result = provider.send(
            recipient=queue.recipient,
            subject=queue.rendered_subject,
            message=queue.rendered_body,
            provider=queue.provider,
        )

        if result["success"]:

            queue.status = CommunicationQueue.Status.SENT
            queue.sent_at = timezone.now()
            queue.processed_at = timezone.now()
            queue.provider_response = result["response"]

            queue.save(
                update_fields=[
                    "status",
                    "sent_at",
                    "processed_at",
                    "provider_response",
                ]
            )

            CommunicationLog.objects.filter(
                queue=queue,
            ).update(
                status=CommunicationLog.Status.DELIVERED,
                delivered_at=timezone.now(),
                provider_message_id=result["provider_message_id"],
                provider_response=str(result["response"]),
            )

            logger.info(
                "Communication %s delivered successfully.",
                queue.id,
            )

            return True

        queue.attempts += 1
        queue.last_error = result["error"]
        queue.provider_response = result["response"]

        if queue.attempts >= queue.max_attempts:

            queue.status = CommunicationQueue.Status.FAILED

        else:

            queue.status = CommunicationQueue.Status.PENDING
            queue.next_retry_at = timezone.now()

        queue.save(
            update_fields=[
                "attempts",
                "last_error",
                "provider_response",
                "status",
                "next_retry_at",
            ]
        )

        CommunicationLog.objects.filter(
            queue=queue,
        ).update(
            status=CommunicationLog.Status.FAILED,
            retry_count=queue.attempts,
            last_retry_at=timezone.now(),
            error_message=result["error"],
            provider_response=str(result["response"]),
        )

        logger.error(
            "Communication %s failed: %s",
            queue.id,
            result["error"],
        )

        return False