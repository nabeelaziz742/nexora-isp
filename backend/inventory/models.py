import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from customers.models import Customer, ServiceAccount
from tenancy.base_models import TenantScopedModel


class InventoryDevice(TenantScopedModel):
    class DeviceType(models.TextChoices):
        ONU = "ONU", "ONU"
        ONT = "ONT", "ONT"
        ROUTER = "ROUTER", "Router"
        MODEM = "MODEM", "Modem"
        ACCESS_POINT = "ACCESS_POINT", "Access Point"
        SWITCH = "SWITCH", "Switch"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ASSIGNED = "ASSIGNED", "Assigned"
        FAULTY = "FAULTY", "Faulty"
        IN_REPAIR = "IN_REPAIR", "In Repair"
        RETIRED = "RETIRED", "Retired"
        SOLD = "SOLD", "Sold"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    asset_tag = models.CharField(
        max_length=100,
    )

    device_type = models.CharField(
        max_length=30,
        choices=DeviceType.choices,
    )

    manufacturer = models.CharField(
        max_length=150,
        blank=True,
    )

    model_name = models.CharField(
        max_length=150,
        blank=True,
    )

    serial_number = models.CharField(
        max_length=150,
        blank=True,
    )

    mac_address = models.CharField(
        max_length=50,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "inventory_device"
        ordering = ["asset_tag"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "asset_tag"],
                name="unique_device_asset_tag_per_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "serial_number"],
                condition=~models.Q(serial_number=""),
                name="unique_device_serial_per_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "mac_address"],
                condition=~models.Q(mac_address=""),
                name="unique_device_mac_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="device_org_status_idx",
            ),
            models.Index(
                fields=["organization", "device_type"],
                name="device_org_type_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.asset_tag} - "
            f"{self.device_type} - "
            f"{self.status}"
        )


class DeviceAssignment(TenantScopedModel):
    class ReturnCondition(models.TextChoices):
        GOOD = "GOOD", "Good"
        DAMAGED = "DAMAGED", "Damaged"
        FAULTY = "FAULTY", "Faulty"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    device = models.ForeignKey(
        InventoryDevice,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.PROTECT,
        related_name="device_assignments",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_device_assignments",
    )

    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_device_returns",
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    returned_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    return_condition = models.CharField(
        max_length=20,
        choices=ReturnCondition.choices,
        blank=True,
    )

    assignment_notes = models.TextField(
        blank=True,
    )

    return_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "inventory_device_assignment"
        ordering = ["-assigned_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["device"],
                condition=models.Q(returned_at__isnull=True),
                name="unique_active_assignment_per_device",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "service_account"],
                name="device_assign_org_service_idx",
            ),
            models.Index(
                fields=["organization", "device"],
                name="device_assign_org_device_idx",
            ),
            models.Index(
                fields=["organization", "returned_at"],
                name="device_assign_org_return_idx",
            ),
        ]

    @property
    def is_active(self):
        return self.returned_at is None

    def __str__(self):
        return (
            f"{self.device.asset_tag} -> "
            f"{self.service_account.service_number}"
        )


class InventoryItem(TenantScopedModel):
    class Category(models.TextChoices):
        CABLES_CONNECTORS = "CABLES_CONNECTORS", "Cables & Connectors"
        OPTICAL_SPLITTERS = "OPTICAL_SPLITTERS", "Optical Splitters"
        ROUTERS_AP = "ROUTERS_AP", "Routers & Access Points"
        ONU_ONT = "ONU_ONT", "ONU / ONT Devices"
        POWER_ADAPTERS = "POWER_ADAPTERS", "Power Adapters"
        ACCESSORIES = "ACCESSORIES", "Hardware & Accessories"
        TOOLS_EQUIPMENT = "TOOLS_EQUIPMENT", "Tools & Field Equipment"
        OTHER = "OTHER", "Other"

    class Unit(models.TextChoices):
        PIECES = "PIECES", "Pieces (Pcs)"
        METERS = "METERS", "Meters (m)"
        ROLLS = "ROLLS", "Rolls"
        PACKS = "PACKS", "Packs"
        BOXES = "BOXES", "Boxes"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=200,
    )

    code = models.CharField(
        max_length=100,
    )

    category = models.CharField(
        max_length=40,
        choices=Category.choices,
        default=Category.ACCESSORIES,
    )

    unit_of_measure = models.CharField(
        max_length=30,
        choices=Unit.choices,
        default=Unit.PIECES,
    )

    unit_cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    unit_selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    quantity_on_hand = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    quantity_damaged = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    reorder_threshold = models.PositiveIntegerField(
        default=5,
    )

    is_serialized = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "inventory_item"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_item_code_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_on_hand__gte=0),
                name="item_quantity_on_hand_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_damaged__gte=0),
                name="item_quantity_damaged_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_cost_price__gte=0),
                name="item_unit_cost_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_selling_price__gte=0),
                name="item_unit_sell_non_negative",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "category"],
                name="inv_item_org_cat_idx",
            ),
            models.Index(
                fields=["organization", "is_active"],
                name="inv_item_org_active_idx",
            ),
        ]

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.reorder_threshold

    def __str__(self):
        return f"{self.name} ({self.code}) - In Stock: {self.quantity_on_hand}"


class StockMovement(TenantScopedModel):
    class MovementType(models.TextChoices):
        PURCHASE_RESTOCK = "PURCHASE_RESTOCK", "Purchase / Restock"
        SALE_DEDUCTION = "SALE_DEDUCTION", "POS Sale Deduction"
        SERVICE_ISSUANCE = "SERVICE_ISSUANCE", "Service / Field Issuance"
        SERVICE_RETURN = "SERVICE_RETURN", "Service Return"
        DAMAGE_TRANSFER = "DAMAGE_TRANSFER", "Transfer to Damaged"
        DAMAGE_DISPOSAL = "DAMAGE_DISPOSAL", "Disposal of Damaged Stock"
        MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT", "Manual Stock Adjustment"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="movements",
    )

    movement_type = models.CharField(
        max_length=40,
        choices=MovementType.choices,
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    previous_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    new_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    reference_type = models.CharField(
        max_length=50,
        blank=True,
    )

    reference_id = models.CharField(
        max_length=255,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_stock_movements",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = "inventory_stock_movement"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["organization", "item", "created_at"],
                name="inv_mvmt_org_item_idx",
            ),
            models.Index(
                fields=["organization", "movement_type"],
                name="inv_mvmt_org_type_idx",
            ),
        ]

    def __str__(self):
        return f"{self.item.code} | {self.movement_type} | Qty: {self.quantity}"


class PosSale(TenantScopedModel):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        CARD = "CARD", "Card"
        MOBILE_WALLET = "MOBILE_WALLET", "Mobile Wallet"

    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    sale_number = models.CharField(
        max_length=100,
    )

    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pos_sales",
    )

    walk_in_customer_name = models.CharField(
        max_length=200,
        blank=True,
    )

    walk_in_customer_phone = models.CharField(
        max_length=50,
        blank=True,
    )

    sale_date = models.DateField()

    subtotal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )

    payment_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.COMPLETED,
    )

    cancellation_reason = models.TextField(
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cancelled_pos_sales",
    )

    journal_entry = models.ForeignKey(
        "accounting.JournalEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pos_sale_records",
    )

    sold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_pos_sales",
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "inventory_pos_sale"
        ordering = ["-sale_date", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "sale_number"],
                name="unique_pos_sale_number_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(subtotal_amount__gte=0),
                name="pos_subtotal_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name="pos_total_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(paid_amount__gte=0),
                name="pos_paid_non_negative",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "sale_date"],
                name="pos_sale_org_date_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="pos_sale_org_status_idx",
            ),
            models.Index(
                fields=["organization", "customer"],
                name="pos_sale_org_cust_idx",
            ),
        ]

    def __str__(self):
        customer_label = (
            self.customer.full_name
            if self.customer
            else self.walk_in_customer_name or "Walk-in Customer"
        )
        return f"{self.sale_number} - {customer_label} ({self.total_amount})"


class PosSaleItem(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    sale = models.ForeignKey(
        PosSale,
        on_delete=models.CASCADE,
        related_name="items",
    )

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="sale_items",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1.00"),
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    line_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    device = models.ForeignKey(
        InventoryDevice,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sold_via_pos",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "inventory_pos_sale_item"
        ordering = ["created_at"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="pos_item_qty_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name="pos_item_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(line_total__gte=0),
                name="pos_item_total_non_negative",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "sale"],
                name="pos_item_org_sale_idx",
            ),
            models.Index(
                fields=["organization", "item"],
                name="pos_item_org_item_idx",
            ),
        ]

    def __str__(self):
        return f"{self.sale.sale_number} | {self.item.name} x {self.quantity} = {self.line_total}"