from rest_framework import serializers


class CommandCenterSummarySerializer(serializers.Serializer):
    total_customers = serializers.IntegerField()
    active_customers = serializers.IntegerField()

    total_services = serializers.IntegerField()
    active_services = serializers.IntegerField()
    grace_period_services = serializers.IntegerField()
    suspension_pending_services = serializers.IntegerField()
    suspended_services = serializers.IntegerField()
    restore_pending_services = serializers.IntegerField()

    total_network_nodes = serializers.IntegerField()
    active_network_nodes = serializers.IntegerField()

    pending_provisioning_requests = serializers.IntegerField()
    processing_provisioning_requests = serializers.IntegerField()
    failed_provisioning_requests = serializers.IntegerField()

    total_inventory_devices = serializers.IntegerField()
    available_devices = serializers.IntegerField()
    assigned_devices = serializers.IntegerField()
    faulty_devices = serializers.IntegerField()
    in_repair_devices = serializers.IntegerField()

    total_invoices = serializers.IntegerField()
    unpaid_invoices = serializers.IntegerField()
    partially_paid_invoices = serializers.IntegerField()
    paid_invoices = serializers.IntegerField()

    invoiced_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    collected_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    outstanding_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    open_complaints = serializers.IntegerField()
    in_progress_complaints = serializers.IntegerField()
    critical_complaints = serializers.IntegerField()

    active_incidents = serializers.IntegerField()
    critical_incidents = serializers.IntegerField()

    open_work_orders = serializers.IntegerField()
    critical_work_orders = serializers.IntegerField()

    pending_notifications = serializers.IntegerField()
    processing_notifications = serializers.IntegerField()
    failed_notifications = serializers.IntegerField()

    operational_health_score = serializers.IntegerField()


class OperationalAlertSerializer(serializers.Serializer):
    alert_type = serializers.CharField()
    severity = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    resource_type = serializers.CharField()
    resource_id = serializers.CharField()
    occurred_at = serializers.DateTimeField()
    context = serializers.JSONField()


class PriorityQueueItemSerializer(serializers.Serializer):
    resource_id = serializers.CharField()
    status = serializers.CharField(required=False)
    action = serializers.CharField(required=False)
    priority = serializers.CharField(required=False)
    severity = serializers.CharField(required=False)
    work_order_type = serializers.CharField(required=False)
    channel = serializers.CharField(required=False)
    event_type = serializers.CharField(required=False)
    asset_tag = serializers.CharField(required=False)
    device_type = serializers.CharField(required=False)
    queued_at = serializers.DateTimeField()


class PriorityQueuesSerializer(serializers.Serializer):
    pending_provisioning = PriorityQueueItemSerializer(
        many=True,
    )
    critical_complaints = PriorityQueueItemSerializer(
        many=True,
    )
    critical_incidents = PriorityQueueItemSerializer(
        many=True,
    )
    critical_work_orders = PriorityQueueItemSerializer(
        many=True,
    )
    failed_notifications = PriorityQueueItemSerializer(
        many=True,
    )
    inventory_attention = PriorityQueueItemSerializer(
        many=True,
    )


class OperationalActivityActorSerializer(
    serializers.Serializer
):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class OperationalActivitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action = serializers.CharField()
    resource_type = serializers.CharField()
    resource_id = serializers.CharField()
    actor = OperationalActivityActorSerializer(
        allow_null=True,
    )
    metadata = serializers.JSONField()
    created_at = serializers.DateTimeField()


class OperationsCopilotRequestSerializer(serializers.Serializer):
    question = serializers.CharField(
        max_length=2000,
        allow_blank=False,
        trim_whitespace=True,
    )


class OperationsCopilotResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    generated_at = serializers.DateTimeField()
    provider = serializers.CharField()
    model = serializers.CharField()