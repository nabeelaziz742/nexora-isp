from decimal import Decimal

from rest_framework import serializers

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
)


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "description",
            "amount",
            "created_at",
        ]


class PaymentAllocationSerializer(
    serializers.ModelSerializer
):
    payment_number = serializers.CharField(
        source="payment.payment_number",
        read_only=True,
    )
    payment_method = serializers.CharField(
        source="payment.payment_method",
        read_only=True,
    )
    payment_reference = serializers.CharField(
        source="payment.reference",
        read_only=True,
    )
    paid_at = serializers.DateTimeField(
        source="payment.paid_at",
        read_only=True,
    )

    class Meta:
        model = PaymentAllocation
        fields = [
            "id",
            "payment",
            "payment_number",
            "payment_method",
            "payment_reference",
            "amount",
            "paid_at",
            "created_at",
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    service_number = serializers.CharField(
        source="service_account.service_number",
        read_only=True,
    )
    customer_id = serializers.UUIDField(
        source="service_account.customer_id",
        read_only=True,
    )
    customer_number = serializers.CharField(
        source=(
            "service_account.customer.customer_number"
        ),
        read_only=True,
    )
    customer_name = serializers.CharField(
        source="service_account.customer.full_name",
        read_only=True,
    )
    package_name = serializers.CharField(
        source=(
            "service_account.internet_package.name"
        ),
        read_only=True,
    )
    total_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    paid_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    outstanding_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "service_account",
            "service_number",
            "customer_id",
            "customer_number",
            "customer_name",
            "package_name",
            "billing_period_start",
            "billing_period_end",
            "issue_date",
            "due_date",
            "status",
            "total_amount",
            "paid_amount",
            "outstanding_amount",
            "created_at",
            "updated_at",
        ]


class InvoiceDetailSerializer(InvoiceSerializer):
    lines = InvoiceLineSerializer(
        many=True,
        read_only=True,
    )
    allocations = PaymentAllocationSerializer(
        many=True,
        read_only=True,
    )

    class Meta(InvoiceSerializer.Meta):
        fields = InvoiceSerializer.Meta.fields + [
            "lines",
            "allocations",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    service_number = serializers.CharField(
        source="service_account.service_number",
        read_only=True,
    )
    customer_id = serializers.UUIDField(
        source="service_account.customer_id",
        read_only=True,
    )
    customer_number = serializers.CharField(
        source=(
            "service_account.customer.customer_number"
        ),
        read_only=True,
    )
    customer_name = serializers.CharField(
        source="service_account.customer.full_name",
        read_only=True,
    )
    received_by_email = serializers.EmailField(
        source="received_by.email",
        read_only=True,
        allow_null=True,
    )
    allocated_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    unallocated_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "payment_number",
            "service_account",
            "service_number",
            "customer_id",
            "customer_number",
            "customer_name",
            "amount",
            "allocated_amount",
            "unallocated_amount",
            "payment_method",
            "reference",
            "notes",
            "received_by_email",
            "paid_at",
            "created_at",
            "updated_at",
        ]


class RecordInvoicePaymentSerializer(
    serializers.Serializer
):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    payment_method = serializers.ChoiceField(
        choices=Payment.Method.choices,
    )
    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=150,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    paid_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )


class RevenueIntelligenceSerializer(
    serializers.Serializer
):
    currency = serializers.CharField()
    period = serializers.DictField()
    metrics = serializers.DictField()
    performance = serializers.ListField()
    risk_signals = serializers.ListField()
    opportunities = serializers.ListField()
    health_formula = serializers.DictField()

class GenerateInvoiceSerializer(serializers.Serializer):
    service_account_id = serializers.UUIDField()

    billing_year = serializers.IntegerField(
        min_value=2024,
        max_value=2100,
    )

    billing_month = serializers.IntegerField(
        min_value=1,
        max_value=12,
    )