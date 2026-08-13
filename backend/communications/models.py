import uuid

from django.db import models

from tenancy.base_models import TenantScopedModel
from customers.models import Customer


class CommunicationProvider(TenantScopedModel):
    class ProviderType(models.TextChoices):
        WHATSAPP = "WHATSAPP", "WhatsApp"
        SMS = "SMS", "SMS"
        EMAIL = "EMAIL", "Email"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
    )

    provider_type = models.CharField(
        max_length=20,
        choices=ProviderType.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    business_id = models.CharField(
        max_length=255,
        blank=True,
    )

    phone_number_id = models.CharField(
        max_length=255,
        blank=True,
    )

    access_token = models.TextField(
        blank=True,
    )

    webhook_verify_token = models.CharField(
        max_length=255,
        blank=True,
    )

    api_url = models.URLField(
        blank=True,
    )

    sender_id = models.CharField(
        max_length=100,
        blank=True,
    )

    is_default = models.BooleanField(
        default=False,
    )

    last_health_check = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_connected = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "communications_provider"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_provider_name_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "provider_type"],
                name="comm_provider_type_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="comm_provider_status_idx",
            ),
        ]

    def __str__(self):
        return self.name
    
class CommunicationTemplate(TenantScopedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DRAFT = "DRAFT", "Draft"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
    )

    subject = models.CharField(
        max_length=255,
        blank=True,
    )

    body = models.TextField()

    variables = models.JSONField(
        default=list,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    communication_provider = models.ForeignKey(
        CommunicationProvider,
        on_delete=models.PROTECT,
        related_name="templates",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "communications_template"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_template_name_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "communication_provider"],
                name="comm_template_provider_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="comm_template_status_idx",
            ),
        ]

    def __str__(self):
        return self.name
    
class CommunicationAutomation(TenantScopedModel):
    class Trigger(models.TextChoices):
        CUSTOMER_CREATED = "CUSTOMER_CREATED", "Customer Created"
        INVOICE_GENERATED = "INVOICE_GENERATED", "Invoice Generated"
        PAYMENT_VERIFIED = "PAYMENT_VERIFIED", "Payment Verified"
        COMPLAINT_CREATED = "COMPLAINT_CREATED", "Complaint Created"
        COMPLAINT_CLOSED = "COMPLAINT_CLOSED", "Complaint Closed"
        SERVICE_SUSPENDED = "SERVICE_SUSPENDED", "Service Suspended"
        SERVICE_RESTORED = "SERVICE_RESTORED", "Service Restored"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    trigger = models.CharField(
        max_length=50,
        choices=Trigger.choices,
    )

    template = models.ForeignKey(
        CommunicationTemplate,
        on_delete=models.PROTECT,
        related_name="automations",
    )

    execution_order = models.PositiveIntegerField(
        default=1,
    )

    delay_minutes = models.PositiveIntegerField(
        default=0,
    )

    max_retry_attempts = models.PositiveSmallIntegerField(
        default=3,
    )

    last_executed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_execution_status = models.CharField(
        max_length=20,
        blank=True,
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "communications_automation"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_automation_name_per_org",
            ),
        ]

    def __str__(self):
        return self.name
    
class CommunicationSchedule(TenantScopedModel):
    class Frequency(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        ONCE = "ONCE", "One Time"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    automation = models.ForeignKey(
        CommunicationAutomation,
        on_delete=models.CASCADE,
        related_name="schedules",
    )

    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
    )

    next_run = models.DateTimeField()

    last_run = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "communications_schedule"
        ordering = ["next_run"]

    def __str__(self):
        return f"{self.automation.name}"
    
class CommunicationQueue(TenantScopedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    # Flat constants kept alongside the TextChoices class above so existing
    # code that references CommunicationQueue.Status.PENDING keeps working,
    # while also exposing the flat STATUS_* names that were requested.
    STATUS_PENDING = Status.PENDING
    STATUS_PROCESSING = Status.PROCESSING
    STATUS_SENT = Status.SENT
    STATUS_FAILED = Status.FAILED
    STATUS_CANCELLED = Status.CANCELLED

    STATUS_CHOICES = Status.choices

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="communication_queue",
    )

    template = models.ForeignKey(
        CommunicationTemplate,
        on_delete=models.PROTECT,
        related_name="queue_items",
    )

    provider = models.ForeignKey(
        CommunicationProvider,
        on_delete=models.PROTECT,
        related_name="queue_items",
    )

    recipient = models.CharField(
        max_length=50,
    )

    payload = models.JSONField(
        default=dict,
        blank=True,
    )

    rendered_subject = models.CharField(
        max_length=255,
        blank=True,
    )

    rendered_body = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    priority = models.PositiveSmallIntegerField(
        default=5,
        help_text="Lower value = higher priority",
    )

    scheduled_at = models.DateTimeField()

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    retry_count = models.PositiveIntegerField(
        default=0,
    )

    attempts = models.PositiveIntegerField(
        default=0,
    )

    max_attempts = models.PositiveIntegerField(
        default=3,
    )

    processing_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    last_error = models.TextField(
        blank=True,
    )

    provider_response = models.JSONField(
        default=dict,
        blank=True,
    )

    locked_by = models.CharField(
        max_length=100,
        blank=True,
    )

    lock_expires_at = models.DateTimeField(
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
        db_table = "communications_queue"
        ordering = (
            "priority",
            "created_at",
        )

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="comm_queue_status_idx",
            ),
            models.Index(
                fields=["organization", "scheduled_at"],
                name="comm_queue_schedule_idx",
            ),
            models.Index(
                fields=["status", "priority"],
                name="comm_queue_status_prio_idx",
            ),
            models.Index(
                fields=["next_retry_at"],
                name="comm_queue_next_retry_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.recipient} - "
            f"{self.status}"
        )

class CommunicationLog(TenantScopedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        DELIVERED = "DELIVERED", "Delivered"
        READ = "READ", "Read"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    queue = models.OneToOneField(
        CommunicationQueue,
        on_delete=models.CASCADE,
        related_name="log",
    )

    recipient = models.CharField(
        max_length=50,
    )

    subject = models.CharField(
    max_length=255,
    blank=True,
    )

    message = models.TextField(
    blank=True,
    )

    retry_count = models.PositiveIntegerField(
    default=0,
    )

    last_retry_at = models.DateTimeField(
    null=True,
    blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    provider_response = models.TextField(
        blank=True,
    )

    provider_response_code = models.CharField(
        max_length=100,
        blank=True,
    )

    provider_message_id = models.CharField(
        max_length=255,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "communications_log"
        ordering = ["-created_at"]