from rest_framework import serializers

from notifications.models import NotificationJob


class NotificationJobQueueSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()

    service_account_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    channel = serializers.ChoiceField(
        choices=NotificationJob.Channel.choices,
    )

    event_type = serializers.CharField(
        max_length=100,
    )

    subject = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )

    message = serializers.CharField()

    context = serializers.JSONField(
        required=False,
        default=dict,
    )


class StartNotificationProcessingSerializer(
    serializers.Serializer
):
    provider_name = serializers.CharField(
        max_length=100,
    )


class MarkNotificationSentSerializer(
    serializers.Serializer
):
    provider_message_id = serializers.CharField(
        max_length=255,
    )


class MarkNotificationFailedSerializer(
    serializers.Serializer
):
    failure_reason = serializers.CharField()


class NotificationJobSerializer(serializers.ModelSerializer):
    customer_id = serializers.UUIDField(
        source="customer.id",
        read_only=True,
    )

    customer_number = serializers.CharField(
        source="customer.customer_number",
        read_only=True,
    )

    customer_name = serializers.SerializerMethodField()

    service_account_id = serializers.UUIDField(
        source="service_account.id",
        read_only=True,
        allow_null=True,
    )

    service_number = serializers.CharField(
        source="service_account.service_number",
        read_only=True,
        allow_null=True,
    )

    service_status = serializers.CharField(
        source="service_account.status",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = NotificationJob
        fields = [
            "id",
            "channel",
            "status",
            "event_type",
            "recipient",
            "subject",
            "message",
            "context",
            "customer_id",
            "customer_number",
            "customer_name",
            "service_account_id",
            "service_number",
            "service_status",
            "provider_name",
            "provider_message_id",
            "failure_reason",
            "attempt_count",
            "processing_started_at",
            "sent_at",
            "failed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj):
        return (
            f"{obj.customer.first_name} "
            f"{obj.customer.last_name}"
        ).strip()


class NotificationSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    processing = serializers.IntegerField()
    sent = serializers.IntegerField()
    failed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    sms = serializers.IntegerField()
    whatsapp = serializers.IntegerField()