from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from communications.models import (
    CommunicationQueue,
)

logger = logging.getLogger(__name__)


class CommunicationQueueService:
    """
    Queue management service.

    Responsible for:
    - enqueue messages
    - acquire jobs
    - retry failed jobs
    - mark sent
    - mark failed
    """

    @staticmethod
    def enqueue(
        *,
        organization,
        provider,
        recipient,
        customer=None,
        template=None,
        subject="",
        message="",
        priority=5,
        scheduled_at=None,
    ):
        """
        Add message into queue.
        """

        queue = CommunicationQueue.objects.create(
            organization=organization,
            customer=customer,
            template=template,
            provider=provider,
            recipient=recipient,
            rendered_subject=subject,
            rendered_body=message,
            priority=priority,
            scheduled_at=scheduled_at or timezone.now(),
            status=CommunicationQueue.STATUS_PENDING,
        )

        logger.info(
            "Queued communication %s",
            queue.id,
        )

        return queue

    @staticmethod
    @transaction.atomic
    def get_next_job():

        now = timezone.now()

        job = (
            CommunicationQueue.objects
            .select_for_update(skip_locked=True)
            .filter(
                status=CommunicationQueue.STATUS_PENDING,
            )
            .filter(
                Q(next_retry_at__isnull=True)
                | Q(next_retry_at__lte=now),
            )
            .order_by(
                "priority",
                "created_at",
            )
            .first()
        )

        if not job:
            return None

        job.status = CommunicationQueue.STATUS_PROCESSING
        job.processing_started_at = now

        job.save(
            update_fields=[
                "status",
                "processing_started_at",
            ]
        )

        return job

    @staticmethod
    def mark_sent(
        queue,
        provider_response=None,
    ):
        queue.status = CommunicationQueue.STATUS_SENT

        queue.processed_at = timezone.now()

        queue.provider_response = (
            provider_response or {}
        )

        queue.save(
            update_fields=[
                "status",
                "processed_at",
                "provider_response",
            ]
        )

    @staticmethod
    def mark_failed(
        queue,
        error,
    ):
        queue.attempts += 1

        queue.last_error = str(error)

        if queue.attempts >= queue.max_attempts:

            queue.status = (
                CommunicationQueue.STATUS_FAILED
            )

        else:

            queue.status = (
                CommunicationQueue.STATUS_PENDING
            )

            queue.next_retry_at = (
                timezone.now()
            )

        queue.save(
            update_fields=[
                "attempts",
                "status",
                "last_error",
                "next_retry_at",
            ]
        )