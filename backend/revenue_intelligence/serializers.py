from rest_framework import serializers


class RevenueOverviewSerializer(serializers.Serializer):
    invoiced_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    collected_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    outstanding_receivables = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    recorded_payments = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    allocated_payments = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    unallocated_payments = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )


class CollectionsByPeriodSerializer(serializers.Serializer):
    period = serializers.DateTimeField()

    payment_intake_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    payment_count = serializers.IntegerField()

    allocated_collection_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    allocation_count = serializers.IntegerField()


class PaymentMethodMixSerializer(serializers.Serializer):
    payment_method = serializers.CharField()
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    payment_count = serializers.IntegerField()


class OutstandingReceivableSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField()
    invoice_number = serializers.CharField()

    service_account_id = serializers.UUIDField()
    service_number = serializers.CharField()

    customer_id = serializers.UUIDField()
    customer_number = serializers.CharField()
    customer_name = serializers.CharField()

    status = serializers.CharField()

    issue_date = serializers.DateField()
    due_date = serializers.DateField()

    total_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    paid_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    outstanding_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )