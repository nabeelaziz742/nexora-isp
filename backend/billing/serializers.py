from decimal import Decimal

from rest_framework import serializers

from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
    PromiseToPay,
)


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "description",
            "quantity",
            "unit_price",
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
            "cancelled_at",
            "cancellation_reason",
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
            "is_reversed",
            "reversed_at",
            "reversal_reason",
            "reversal_reference",
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


class PromiseToPaySerializer(serializers.ModelSerializer):
    customer_number = serializers.CharField(
        source="customer.customer_number",
        read_only=True,
    )
    customer_name = serializers.CharField(
        source="customer.full_name",
        read_only=True,
    )
    service_number = serializers.CharField(
        source="service_account.service_number",
        read_only=True,
    )
    invoice_number = serializers.CharField(
        source="invoice.invoice_number",
        read_only=True,
        default=None,
    )
    created_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PromiseToPay
        fields = [
            "id",
            "promise_number",
            "customer",
            "customer_number",
            "customer_name",
            "service_account",
            "service_number",
            "invoice",
            "invoice_number",
            "outstanding_amount",
            "promised_amount",
            "promise_date",
            "deadline",
            "status",
            "notes",
            "failure_reason",
            "created_by_name",
            "approved_by_name",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "promise_number",
            "outstanding_amount",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return None


class PromiseToPayCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    service_account_id = serializers.UUIDField()
    invoice_id = serializers.UUIDField(required=False, allow_null=True)
    promised_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    promise_date = serializers.DateField()
    deadline = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=[PromiseToPay.Status.PENDING, PromiseToPay.Status.ACTIVE],
        default=PromiseToPay.Status.PENDING,
    )

    def validate(self, attrs):
        if attrs["deadline"] < attrs["promise_date"]:
            raise serializers.ValidationError({"deadline": "Deadline cannot be earlier than the promise date."})
        return attrs


class PromiseToPayStatusTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PromiseToPay.Status.choices)
    failure_reason = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CancelInvoiceSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(required=True, min_length=3)


class InvoiceLineItemInputSerializer(serializers.Serializer):
    description = serializers.CharField(required=True, max_length=255)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    quantity = serializers.IntegerField(required=False, default=1, min_value=1)
    unit_price = serializers.DecimalField(required=False, allow_null=True, max_digits=12, decimal_places=2)


class CustomInvoiceCreateSerializer(serializers.Serializer):
    service_account_id = serializers.UUIDField()
    billing_period_start = serializers.DateField()
    billing_period_end = serializers.DateField()
    issue_date = serializers.DateField()
    due_date = serializers.DateField()
    line_items = InvoiceLineItemInputSerializer(many=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["billing_period_end"] < attrs["billing_period_start"]:
            raise serializers.ValidationError({"billing_period_end": "Billing period end cannot be before start."})
        if attrs["due_date"] < attrs["issue_date"]:
            raise serializers.ValidationError({"due_date": "Due date cannot be before issue date."})
        if not attrs.get("line_items"):
            raise serializers.ValidationError({"line_items": "At least one line item is required."})
        return attrs


class PaymentAllocationInputSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class RecordPaymentWithAllocationsSerializer(serializers.Serializer):
    service_account_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    payment_method = serializers.ChoiceField(choices=Payment.Method.choices)
    reference = serializers.CharField(required=False, allow_blank=True, default="", max_length=150)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    allocations = PaymentAllocationInputSerializer(many=True, required=False, allow_null=True)
    paid_at = serializers.DateTimeField(required=False, allow_null=True)


class PaymentReversalSerializer(serializers.Serializer):
    reversal_reason = serializers.CharField(required=True, min_length=3)
    reversal_reference = serializers.CharField(required=False, allow_blank=True, default="", max_length=150)


class MonthlyBillingRunSerializer(serializers.Serializer):
    billing_year = serializers.IntegerField(min_value=2024, max_value=2100)
    billing_month = serializers.IntegerField(min_value=1, max_value=12)


class FinancialLedgerEntrySerializer(serializers.Serializer):
    type = serializers.CharField()
    date = serializers.CharField()
    timestamp = serializers.DateTimeField()
    reference = serializers.CharField()
    description = serializers.CharField()
    debit = serializers.DecimalField(max_digits=12, decimal_places=2)
    credit = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    service_number = serializers.CharField()
    customer_name = serializers.CharField()
    customer_id = serializers.CharField()
    service_account_id = serializers.CharField()
    object_id = serializers.CharField()


class FinancialLedgerSerializer(serializers.Serializer):
    currency = serializers.CharField()
    total_debit = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_credit = serializers.DecimalField(max_digits=12, decimal_places=2)
    closing_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    entries = FinancialLedgerEntrySerializer(many=True)


class PaymentReceiptSerializer(serializers.Serializer):
    organization_name = serializers.CharField()
    organization_code = serializers.CharField()
    currency = serializers.CharField()
    payment_number = serializers.CharField()
    payment_id = serializers.CharField()
    payment_date = serializers.CharField()
    payment_method = serializers.CharField()
    reference = serializers.CharField(allow_blank=True)
    amount = serializers.CharField()
    is_reversed = serializers.BooleanField()
    reversed_at = serializers.CharField(allow_null=True)
    reversal_reason = serializers.CharField(allow_blank=True)
    notes = serializers.CharField(allow_blank=True)
    received_by_name = serializers.CharField()
    customer = serializers.DictField()
    service_number = serializers.CharField()
    allocations = serializers.ListField()
    customer_remaining_balance = serializers.CharField()
