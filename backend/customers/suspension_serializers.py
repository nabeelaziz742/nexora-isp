from rest_framework import serializers

from customers.models import ServiceSuspensionLog, SuspensionPolicy


class SuspensionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SuspensionPolicy
        fields = [
            "id",
            "grace_period_days",
            "suspension_threshold_days",
            "minimum_outstanding_amount",
            "auto_suspension_enabled",
            "auto_restoration_enabled",
            "restore_on_partial_payment",
            "ptp_exemption_enabled",
            "warning_days_before_suspension",
            "send_suspension_warning",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SuspensionPolicyUpdateSerializer(serializers.Serializer):
    grace_period_days = serializers.IntegerField(required=False, min_value=0, max_value=90)
    suspension_threshold_days = serializers.IntegerField(required=False, min_value=0, max_value=90)
    minimum_outstanding_amount = serializers.DecimalField(
        required=False, max_digits=12, decimal_places=2, min_value=0
    )
    auto_suspension_enabled = serializers.BooleanField(required=False)
    auto_restoration_enabled = serializers.BooleanField(required=False)
    restore_on_partial_payment = serializers.BooleanField(required=False)
    ptp_exemption_enabled = serializers.BooleanField(required=False)
    warning_days_before_suspension = serializers.IntegerField(required=False, min_value=0, max_value=30)
    send_suspension_warning = serializers.BooleanField(required=False)


class ServiceSuspensionLogSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_number = serializers.CharField(source="customer.customer_number", read_only=True)
    service_number = serializers.CharField(source="service_account.service_number", read_only=True)
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceSuspensionLog
        fields = [
            "id",
            "service_account",
            "service_number",
            "customer",
            "customer_name",
            "customer_number",
            "event_type",
            "trigger_type",
            "previous_status",
            "new_status",
            "outstanding_amount",
            "reason",
            "actor",
            "actor_name",
            "invoices_snapshot",
            "linked_payment_id",
            "linked_promise_id",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj) -> str:
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return "System Automated"


class ManualSuspensionRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=3, max_length=500)
    force = serializers.BooleanField(required=False, default=False)


class ManualRestorationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=3, max_length=500)
    force = serializers.BooleanField(required=False, default=False)
