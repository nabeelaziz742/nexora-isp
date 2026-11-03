from rest_framework import serializers

from billing.models import Payment
from billing.recharge_services import MAX_RECHARGE_MONTHS
from customers.models import BillingProfile


class ServiceRechargeSerializer(serializers.Serializer):
    months = serializers.IntegerField(min_value=1, max_value=MAX_RECHARGE_MONTHS)
    payment_method = serializers.ChoiceField(choices=Payment.Method.choices)
    reference = serializers.CharField(required=False, allow_blank=True, default="", max_length=150)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class BillingModeSerializer(serializers.Serializer):
    billing_cycle = serializers.ChoiceField(choices=BillingProfile.BillingCycle.choices)
    expiry_date = serializers.DateField(required=False, allow_null=True)


class RechargeResultSerializer(serializers.Serializer):
    service_account_id = serializers.UUIDField(source="service_account.id")
    service_number = serializers.CharField(source="service_account.service_number")
    service_status = serializers.CharField(source="service_account.status")
    invoice_id = serializers.UUIDField(source="invoice.id")
    invoice_number = serializers.CharField(source="invoice.invoice_number")
    payment_id = serializers.UUIDField(source="payment.id", allow_null=True, default=None)
    payment_number = serializers.CharField(source="payment.payment_number", allow_null=True, default=None)
    months = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    previous_expiry_date = serializers.DateField(allow_null=True)
    new_expiry_date = serializers.DateField()
    restored = serializers.BooleanField()
