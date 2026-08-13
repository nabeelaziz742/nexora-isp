import uuid

from django.db import models

from customers.models import Customer, ServiceAccount
from tenancy.base_models import TenantScopedModel


class NotificationJob(TenantScopedModel):
    class Channel(models.TextChoices):
        SMS = "SMS", "SMS"
        WHATSAPP = "WHATSAPP", "WhatsApp"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="notification_jobs",
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="notification_jobs",
    )

    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    event_type = models.CharField(
        max_length=100,
    )

    recipient = models.CharField(
        max_length=255,
    )

    subject = models.CharField(
        max_length=255,
        blank=True,
    )

    message = models.TextField()

    context = models.JSONField(
        default=dict,
        blank=True,
    )

    provider_name = models.CharField(
        max_length=100,
        blank=True,
    )

    provider_message_id = models.CharField(
        max_length=255,
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
    )

    attempt_count = models.PositiveIntegerField(
        default=0,
    )

    processing_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "notifications_notification_job"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="notif_job_org_status_idx",
            ),
            models.Index(
                fields=["organization", "channel"],
                name="notif_job_org_channel_idx",
            ),
            models.Index(
                fields=["organization", "event_type"],
                name="notif_job_org_event_idx",
            ),
            models.Index(
                fields=["organization", "customer"],
                name="notif_job_org_customer_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.event_type} - "
            f"{self.channel} - "
            f"{self.status}"
        )