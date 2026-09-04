from rest_framework import serializers

from billing.models import Invoice, PromiseToPay, RecoveryAllocation
from customers.models import Customer, ServiceAccount


class RecoveryAllocationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_number = serializers.CharField(source="customer.customer_number", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    customer_city = serializers.CharField(source="customer.city", read_only=True)
    customer_area = serializers.CharField(source="customer.area", read_only=True)
    internet_id = serializers.CharField(source="service_account.service_number", read_only=True, default=None)
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True, default=None)
    assigned_staff_name = serializers.SerializerMethodField()
    assigned_staff_email = serializers.CharField(source="assigned_staff.email", read_only=True)
    assigned_by_name = serializers.SerializerMethodField()
    reassigned_from_number = serializers.CharField(source="reassigned_from.allocation_number", read_only=True, default=None)
    linked_promise_number = serializers.CharField(source="linked_promise.promise_number", read_only=True, default=None)

    class Meta:
        model = RecoveryAllocation
        fields = [
            "id",
            "allocation_number",
            "customer",
            "customer_name",
            "customer_number",
            "customer_phone",
            "customer_city",
            "customer_area",
            "service_account",
            "internet_id",
            "invoice",
            "invoice_number",
            "outstanding_amount",
            "assigned_staff",
            "assigned_staff_name",
            "assigned_staff_email",
            "assigned_by",
            "assigned_by_name",
            "assigned_date",
            "due_date",
            "priority",
            "status",
            "notes",
            "reassigned_from",
            "reassigned_from_number",
            "reassignment_reason",
            "linked_promise",
            "linked_promise_number",
            "completed_date",
            "created_at",
            "updated_at",
        ]

    def get_assigned_staff_name(self, obj):
        if obj.assigned_staff:
            return obj.assigned_staff.get_full_name() or obj.assigned_staff.email
        return None

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return obj.assigned_by.get_full_name() or obj.assigned_by.email
        return None


class RecoveryAllocationCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    service_account_id = serializers.UUIDField(required=False, allow_null=True)
    invoice_id = serializers.UUIDField(required=False, allow_null=True)
    assigned_staff_id = serializers.UUIDField()
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=RecoveryAllocation.Priority.choices, default=RecoveryAllocation.Priority.NORMAL)
    notes = serializers.CharField(required=False, allow_blank=True)


class RecoveryAllocationReassignSerializer(serializers.Serializer):
    new_assigned_staff_id = serializers.UUIDField()
    reassignment_reason = serializers.CharField(max_length=255)
    due_date = serializers.DateField(required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=RecoveryAllocation.Priority.choices, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class RecoveryStatusTransitionSerializer(serializers.Serializer):
    new_status = serializers.ChoiceField(choices=RecoveryAllocation.Status.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
    linked_promise_id = serializers.UUIDField(required=False, allow_null=True)
