from decimal import Decimal
from rest_framework import serializers

from inventory.models import (
    DeviceAssignment,
    InventoryDevice,
    InventoryItem,
    PosSale,
    PosSaleItem,
    StockMovement,
)


# ==============================================================================
# SERIALIZED CPE DEVICE SERIALIZERS
# ==============================================================================

class InventoryDeviceSerializer(serializers.ModelSerializer):
    active_assignment_id = serializers.SerializerMethodField()
    assigned_service_number = serializers.SerializerMethodField()
    assigned_customer_number = serializers.SerializerMethodField()
    assigned_customer_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryDevice
        fields = [
            "id",
            "asset_tag",
            "device_type",
            "manufacturer",
            "model_name",
            "serial_number",
            "mac_address",
            "status",
            "notes",
            "active_assignment_id",
            "assigned_service_number",
            "assigned_customer_number",
            "assigned_customer_name",
            "created_at",
            "updated_at",
        ]

    def _get_active_assignment(self, obj):
        prefetched_assignments = getattr(
            obj,
            "active_assignments",
            None,
        )

        if prefetched_assignments is not None:
            return (
                prefetched_assignments[0]
                if prefetched_assignments
                else None
            )

        return (
            obj.assignments
            .filter(returned_at__isnull=True)
            .select_related(
                "service_account",
                "service_account__customer",
            )
            .first()
        )

    def get_active_assignment_id(self, obj):
        assignment = self._get_active_assignment(obj)
        return assignment.id if assignment else None

    def get_assigned_service_number(self, obj):
        assignment = self._get_active_assignment(obj)
        return assignment.service_account.service_number if assignment else None

    def get_assigned_customer_number(self, obj):
        assignment = self._get_active_assignment(obj)
        return assignment.service_account.customer.customer_number if assignment else None

    def get_assigned_customer_name(self, obj):
        assignment = self._get_active_assignment(obj)
        return assignment.service_account.customer.full_name if assignment else None


class DeviceAssignmentSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(
        source="device.asset_tag",
        read_only=True,
    )
    device_type = serializers.CharField(
        source="device.device_type",
        read_only=True,
    )
    device_status = serializers.CharField(
        source="device.status",
        read_only=True,
    )
    service_number = serializers.CharField(
        source="service_account.service_number",
        read_only=True,
    )
    customer_id = serializers.UUIDField(
        source="service_account.customer_id",
        read_only=True,
    )
    customer_number = serializers.CharField(
        source="service_account.customer.customer_number",
        read_only=True,
    )
    customer_name = serializers.CharField(
        source="service_account.customer.full_name",
        read_only=True,
    )
    assigned_by_email = serializers.EmailField(
        source="assigned_by.email",
        read_only=True,
        allow_null=True,
    )
    returned_by_email = serializers.EmailField(
        source="returned_by.email",
        read_only=True,
        allow_null=True,
    )
    is_active = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = DeviceAssignment
        fields = [
            "id",
            "device",
            "asset_tag",
            "device_type",
            "device_status",
            "service_account",
            "service_number",
            "customer_id",
            "customer_number",
            "customer_name",
            "assigned_by_email",
            "returned_by_email",
            "assigned_at",
            "returned_at",
            "return_condition",
            "assignment_notes",
            "return_notes",
            "is_active",
            "created_at",
            "updated_at",
        ]


class AssignDeviceSerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    service_account_id = serializers.UUIDField()
    assignment_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ReturnDeviceSerializer(serializers.Serializer):
    return_condition = serializers.ChoiceField(
        choices=DeviceAssignment.ReturnCondition.choices,
    )
    return_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


# ==============================================================================
# INVENTORY ITEM & STOCK SERIALIZERS
# ==============================================================================

class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "name",
            "code",
            "category",
            "unit_of_measure",
            "unit_cost_price",
            "unit_selling_price",
            "quantity_on_hand",
            "quantity_damaged",
            "reorder_threshold",
            "is_low_stock",
            "is_serialized",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_code = serializers.CharField(source="item.code", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name",
        read_only=True,
        default="System",
    )

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "item",
            "item_name",
            "item_code",
            "movement_type",
            "quantity",
            "previous_quantity",
            "new_quantity",
            "unit_cost",
            "reference_type",
            "reference_id",
            "notes",
            "created_by",
            "created_by_name",
            "created_at",
        ]


class RestockSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=Decimal("0.00"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class StockAdjustmentSerializer(serializers.Serializer):
    new_quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.00"))
    reason = serializers.CharField(required=False, allow_blank=True, default="Cycle Count / Audit")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class DamageStockSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class DisposeStockSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ==============================================================================
# POS & SALES SERIALIZERS
# ==============================================================================

class PosSaleItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_code = serializers.CharField(source="item.code", read_only=True)
    device_asset_tag = serializers.CharField(source="device.asset_tag", read_only=True, default="")

    class Meta:
        model = PosSaleItem
        fields = [
            "id",
            "item",
            "item_name",
            "item_code",
            "quantity",
            "unit_price",
            "unit_cost",
            "line_discount",
            "line_total",
            "device",
            "device_asset_tag",
            "created_at",
        ]


class PosSaleSerializer(serializers.ModelSerializer):
    items = PosSaleItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    sold_by_name = serializers.CharField(source="sold_by.get_full_name", read_only=True, default="Staff")
    cancelled_by_name = serializers.CharField(source="cancelled_by.get_full_name", read_only=True, default="")
    journal_entry_number = serializers.CharField(source="journal_entry.entry_number", read_only=True, default="")

    class Meta:
        model = PosSale
        fields = [
            "id",
            "sale_number",
            "customer",
            "customer_name",
            "customer_phone",
            "walk_in_customer_name",
            "walk_in_customer_phone",
            "sale_date",
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "paid_amount",
            "payment_method",
            "payment_reference",
            "status",
            "cancellation_reason",
            "cancelled_at",
            "cancelled_by",
            "cancelled_by_name",
            "journal_entry",
            "journal_entry_number",
            "sold_by",
            "sold_by_name",
            "notes",
            "items",
            "created_at",
            "updated_at",
        ]

    def get_customer_name(self, obj):
        if obj.customer:
            return obj.customer.full_name
        return obj.walk_in_customer_name or "Walk-in Customer"

    def get_customer_phone(self, obj):
        if obj.customer:
            return obj.customer.phone
        return obj.walk_in_customer_phone or ""


class CreatePosSaleItemInputSerializer(serializers.Serializer):
    item_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"), default=Decimal("1.00"))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=Decimal("0.00"))
    line_discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"), min_value=Decimal("0.00"))
    device_id = serializers.UUIDField(required=False, allow_null=True)


class CreatePosSaleSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    walk_in_customer_name = serializers.CharField(required=False, allow_blank=True, default="")
    walk_in_customer_phone = serializers.CharField(required=False, allow_blank=True, default="")
    sale_date = serializers.DateField(required=False)
    items = CreatePosSaleItemInputSerializer(many=True)
    payment_method = serializers.ChoiceField(choices=PosSale.PaymentMethod.choices, default=PosSale.PaymentMethod.CASH)
    payment_reference = serializers.CharField(required=False, allow_blank=True, default="")
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"), min_value=Decimal("0.00"))
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"), min_value=Decimal("0.00"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CancelPosSaleSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(required=True, min_length=3)