import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounting.models import Account, JournalEntry
from accounting.services import (
    create_journal_entry,
    get_or_create_default_chart_of_accounts,
)
from customers.models import Customer, ServiceAccount
from inventory.models import (
    DeviceAssignment,
    InventoryDevice,
    InventoryItem,
    PosSale,
    PosSaleItem,
    StockMovement,
)
from tenancy.models import Organization
from tenancy.services import record_audit_log


User = get_user_model()


class InventoryCustodyError(Exception):
    pass


class InventoryDomainError(Exception):
    pass


class PosSaleError(Exception):
    pass


@dataclass(frozen=True)
class DeviceAssignmentResult:
    device: InventoryDevice
    assignment: DeviceAssignment


# ==============================================================================
# SERIALIZED CPE DEVICE WORKFLOWS (PRESERVED)
# ==============================================================================

@transaction.atomic
def assign_device_to_service(
    *,
    organization: Organization,
    actor: User,
    device_id,
    service_account_id,
    assignment_notes: str = "",
) -> DeviceAssignmentResult:
    try:
        device = (
            InventoryDevice.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=device_id)
        )
    except InventoryDevice.DoesNotExist as exc:
        raise InventoryCustodyError(
            "Device was not found for this organization."
        ) from exc

    try:
        service_account = (
            ServiceAccount.objects
            .for_organization(organization)
            .get(id=service_account_id)
        )
    except ServiceAccount.DoesNotExist as exc:
        raise InventoryCustodyError(
            "Service account was not found for this organization."
        ) from exc

    if device.status != InventoryDevice.Status.AVAILABLE:
        raise InventoryCustodyError(
            "Only an available device can be assigned."
        )

    active_assignment_exists = (
        DeviceAssignment.objects
        .for_organization(organization)
        .filter(
            device=device,
            returned_at__isnull=True,
        )
        .exists()
    )

    if active_assignment_exists:
        raise InventoryCustodyError(
            "Device already has an active assignment."
        )

    assignment = DeviceAssignment.objects.create(
        organization=organization,
        device=device,
        service_account=service_account,
        assigned_by=actor,
        assignment_notes=assignment_notes.strip(),
    )

    device.status = InventoryDevice.Status.ASSIGNED
    device.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="INVENTORY_DEVICE_ASSIGNED",
        resource_type="InventoryDevice",
        resource_id=device.id,
        metadata={
            "device_assignment_id": str(assignment.id),
            "asset_tag": device.asset_tag,
            "service_account_id": str(service_account.id),
            "service_number": service_account.service_number,
        },
    )

    return DeviceAssignmentResult(
        device=device,
        assignment=assignment,
    )


@transaction.atomic
def return_device_from_service(
    *,
    organization: Organization,
    actor: User,
    assignment_id,
    return_condition: str,
    return_notes: str = "",
) -> DeviceAssignmentResult:
    try:
        assignment = (
            DeviceAssignment.objects
            .select_for_update()
            .select_related(
                "device",
                "service_account",
            )
            .for_organization(organization)
            .get(
                id=assignment_id,
                returned_at__isnull=True,
            )
        )
    except DeviceAssignment.DoesNotExist as exc:
        raise InventoryCustodyError(
            "Active device assignment was not found for this organization."
        ) from exc

    valid_conditions = {
        choice
        for choice, _ in DeviceAssignment.ReturnCondition.choices
    }

    if return_condition not in valid_conditions:
        raise InventoryCustodyError(
            "Invalid device return condition."
        )

    device = InventoryDevice.objects.select_for_update().get(
        id=assignment.device_id,
        organization=organization,
    )

    assignment.returned_by = actor
    assignment.returned_at = timezone.now()
    assignment.return_condition = return_condition
    assignment.return_notes = return_notes.strip()
    assignment.save(
        update_fields=[
            "returned_by",
            "returned_at",
            "return_condition",
            "return_notes",
            "updated_at",
        ]
    )

    if return_condition == DeviceAssignment.ReturnCondition.GOOD:
        device.status = InventoryDevice.Status.AVAILABLE
    else:
        device.status = InventoryDevice.Status.FAULTY

    device.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="INVENTORY_DEVICE_RETURNED",
        resource_type="InventoryDevice",
        resource_id=device.id,
        metadata={
            "device_assignment_id": str(assignment.id),
            "asset_tag": device.asset_tag,
            "service_account_id": str(assignment.service_account_id),
            "service_number": assignment.service_account.service_number,
            "return_condition": return_condition,
        },
    )

    return DeviceAssignmentResult(
        device=device,
        assignment=assignment,
    )


# ==============================================================================
# QUANTITY-BASED STOCK OPERATIONS
# ==============================================================================

@transaction.atomic
def record_stock_restock(
    *,
    organization: Organization,
    actor: User,
    item_id,
    quantity: Decimal | float | int | str,
    unit_cost: Decimal | float | int | str | None = None,
    notes: str = "",
) -> InventoryItem:
    qty = Decimal(str(quantity))
    if qty <= Decimal("0.00"):
        raise InventoryDomainError("Restock quantity must be greater than zero.")

    try:
        item = (
            InventoryItem.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=item_id)
        )
    except InventoryItem.DoesNotExist as exc:
        raise InventoryDomainError("Inventory item was not found for this organization.") from exc

    cost = Decimal(str(unit_cost)) if unit_cost is not None else item.unit_cost_price
    if cost < Decimal("0.00"):
        raise InventoryDomainError("Unit cost price cannot be negative.")

    prev_qty = item.quantity_on_hand
    new_qty = prev_qty + qty

    item.quantity_on_hand = new_qty
    if unit_cost is not None:
        item.unit_cost_price = cost
    item.save(update_fields=["quantity_on_hand", "unit_cost_price", "updated_at"])

    movement = StockMovement.objects.create(
        organization=organization,
        item=item,
        movement_type=StockMovement.MovementType.PURCHASE_RESTOCK,
        quantity=qty,
        previous_quantity=prev_qty,
        new_quantity=new_qty,
        unit_cost=cost,
        reference_type="RESTOCK",
        notes=notes.strip(),
        created_by=actor,
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="INVENTORY_STOCK_RESTOCKED",
        resource_type="InventoryItem",
        resource_id=item.id,
        metadata={
            "item_code": item.code,
            "item_name": item.name,
            "quantity_added": str(qty),
            "new_quantity_on_hand": str(new_qty),
            "stock_movement_id": str(movement.id),
        },
    )

    return item


@transaction.atomic
def record_stock_adjustment(
    *,
    organization: Organization,
    actor: User,
    item_id,
    new_quantity: Decimal | float | int | str,
    reason: str = "",
    notes: str = "",
) -> InventoryItem:
    target_qty = Decimal(str(new_quantity))
    if target_qty < Decimal("0.00"):
        raise InventoryDomainError("Stock quantity cannot be adjusted to a negative value.")

    try:
        item = (
            InventoryItem.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=item_id)
        )
    except InventoryItem.DoesNotExist as exc:
        raise InventoryDomainError("Inventory item was not found for this organization.") from exc

    prev_qty = item.quantity_on_hand
    diff_qty = abs(target_qty - prev_qty)

    item.quantity_on_hand = target_qty
    item.save(update_fields=["quantity_on_hand", "updated_at"])

    movement = StockMovement.objects.create(
        organization=organization,
        item=item,
        movement_type=StockMovement.MovementType.MANUAL_ADJUSTMENT,
        quantity=diff_qty,
        previous_quantity=prev_qty,
        new_quantity=target_qty,
        unit_cost=item.unit_cost_price,
        reference_type="MANUAL_ADJUSTMENT",
        notes=f"Reason: {reason.strip()}. {notes.strip()}".strip(),
        created_by=actor,
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="INVENTORY_STOCK_ADJUSTED",
        resource_type="InventoryItem",
        resource_id=item.id,
        metadata={
            "item_code": item.code,
            "previous_quantity": str(prev_qty),
            "new_quantity": str(target_qty),
            "reason": reason,
            "stock_movement_id": str(movement.id),
        },
    )

    return item


@transaction.atomic
def mark_stock_as_damaged(
    *,
    organization: Organization,
    actor: User,
    item_id,
    quantity: Decimal | float | int | str,
    notes: str = "",
) -> InventoryItem:
    qty = Decimal(str(quantity))
    if qty <= Decimal("0.00"):
        raise InventoryDomainError("Damaged quantity must be greater than zero.")

    try:
        item = (
            InventoryItem.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=item_id)
        )
    except InventoryItem.DoesNotExist as exc:
        raise InventoryDomainError("Inventory item was not found for this organization.") from exc

    if item.quantity_on_hand < qty:
        raise InventoryDomainError(
            f"Cannot mark {qty} items as damaged. Only {item.quantity_on_hand} available on hand."
        )

    prev_on_hand = item.quantity_on_hand
    new_on_hand = prev_on_hand - qty
    new_damaged = item.quantity_damaged + qty

    item.quantity_on_hand = new_on_hand
    item.quantity_damaged = new_damaged
    item.save(update_fields=["quantity_on_hand", "quantity_damaged", "updated_at"])

    movement = StockMovement.objects.create(
        organization=organization,
        item=item,
        movement_type=StockMovement.MovementType.DAMAGE_TRANSFER,
        quantity=qty,
        previous_quantity=prev_on_hand,
        new_quantity=new_on_hand,
        unit_cost=item.unit_cost_price,
        reference_type="DAMAGE_TRANSFER",
        notes=notes.strip(),
        created_by=actor,
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="INVENTORY_STOCK_DAMAGED",
        resource_type="InventoryItem",
        resource_id=item.id,
        metadata={
            "item_code": item.code,
            "damaged_transferred": str(qty),
            "quantity_on_hand": str(new_on_hand),
            "total_damaged": str(new_damaged),
            "stock_movement_id": str(movement.id),
        },
    )

    return item


@transaction.atomic
def dispose_damaged_stock(
    *,
    organization: Organization,
    actor: User,
    item_id,
    quantity: Decimal | float | int | str,
    notes: str = "",
) -> InventoryItem:
    qty = Decimal(str(quantity))
    if qty <= Decimal("0.00"):
        raise InventoryDomainError("Disposal quantity must be greater than zero.")

    try:
        item = (
            InventoryItem.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=item_id)
        )
    except InventoryItem.DoesNotExist as exc:
        raise InventoryDomainError("Inventory item was not found for this organization.") from exc

    if item.quantity_damaged < qty:
        raise InventoryDomainError(
            f"Cannot dispose {qty} items. Only {item.quantity_damaged} recorded in damaged stock."
        )

    prev_damaged = item.quantity_damaged
    new_damaged = prev_damaged - qty

    item.quantity_damaged = new_damaged
    item.save(update_fields=["quantity_damaged", "updated_at"])

    movement = StockMovement.objects.create(
        organization=organization,
        item=item,
        movement_type=StockMovement.MovementType.DAMAGE_DISPOSAL,
        quantity=qty,
        previous_quantity=prev_damaged,
        new_quantity=new_damaged,
        unit_cost=item.unit_cost_price,
        reference_type="DAMAGE_DISPOSAL",
        notes=notes.strip(),
        created_by=actor,
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="INVENTORY_STOCK_DISPOSED",
        resource_type="InventoryItem",
        resource_id=item.id,
        metadata={
            "item_code": item.code,
            "disposed_quantity": str(qty),
            "remaining_damaged": str(new_damaged),
            "stock_movement_id": str(movement.id),
        },
    )

    return item


# ==============================================================================
# POS & HARDWARE SALES WORKFLOW
# ==============================================================================

def post_pos_sale_journal_entry(
    *,
    organization: Organization,
    actor: User,
    sale: PosSale,
) -> JournalEntry | None:
    """
    Posts double-entry GL journal entry for a completed POS Sale:
    Debit: Payment Account (Cash 1000 / Bank 1010 / Wallet 1020)
    Credit: Revenue Account (4020 Equipment Sales Revenue)
    """
    existing_entry = (
        JournalEntry.objects
        .for_organization(organization)
        .filter(
            reference_type=JournalEntry.ReferenceType.POS_SALE,
            reference_id=str(sale.id),
        )
        .first()
    )
    if existing_entry:
        return existing_entry

    get_or_create_default_chart_of_accounts(organization=organization)

    # 1. Resolve Asset / Payment Account
    if sale.payment_method == PosSale.PaymentMethod.CASH:
        payment_acc = Account.objects.for_organization(organization).filter(code="1000").first()
    elif sale.payment_method == PosSale.PaymentMethod.MOBILE_WALLET:
        payment_acc = Account.objects.for_organization(organization).filter(code="1020").first()
    else:  # BANK_TRANSFER or CARD
        payment_acc = Account.objects.for_organization(organization).filter(code="1010").first()

    if not payment_acc:
        payment_acc = (
            Account.objects
            .for_organization(organization)
            .filter(category=Account.Category.ASSET, account_type=Account.AccountType.CURRENT_ASSET)
            .first()
        )

    # 2. Resolve Revenue Account
    revenue_acc = Account.objects.for_organization(organization).filter(code="4020").first()
    if not revenue_acc:
        revenue_acc = Account.objects.for_organization(organization).filter(code="4090").first()
    if not revenue_acc:
        revenue_acc = Account.objects.for_organization(organization).filter(category=Account.Category.REVENUE).first()

    if not payment_acc or not revenue_acc or sale.total_amount <= Decimal("0.00"):
        return None

    lines = [
        {
            "account_id": payment_acc.id,
            "debit": sale.total_amount,
            "credit": Decimal("0.00"),
            "description": f"POS Sale #{sale.sale_number} receipt ({sale.payment_method})",
        },
        {
            "account_id": revenue_acc.id,
            "debit": Decimal("0.00"),
            "credit": sale.total_amount,
            "description": f"Hardware & Equipment Sales Revenue ({sale.sale_number})",
        },
    ]

    customer_label = (
        sale.customer.full_name
        if sale.customer
        else sale.walk_in_customer_name or "Counter Customer"
    )

    return create_journal_entry(
        organization=organization,
        actor=actor,
        txn_date=sale.sale_date,
        narration=f"POS Hardware Sale #{sale.sale_number} - {customer_label}",
        lines=lines,
        reference_type=JournalEntry.ReferenceType.POS_SALE,
        reference_id=str(sale.id),
        record_audit=True,
    )


def post_pos_sale_cancellation_journal_entry(
    *,
    organization: Organization,
    actor: User,
    sale: PosSale,
) -> JournalEntry | None:
    """
    Reverses the double-entry GL journal entry upon POS Sale cancellation:
    Debit: Revenue Account (4020)
    Credit: Payment Account (1000/1010/1020)
    """
    existing_entry = (
        JournalEntry.objects
        .for_organization(organization)
        .filter(
            reference_type=JournalEntry.ReferenceType.POS_SALE_REVERSAL,
            reference_id=str(sale.id),
        )
        .first()
    )
    if existing_entry:
        return existing_entry

    if not sale.journal_entry:
        return None

    orig_lines = sale.journal_entry.lines.all()
    lines = []
    for orig in orig_lines:
        lines.append({
            "account_id": orig.account_id,
            "debit": orig.credit,  # Swap debits and credits
            "credit": orig.debit,
            "description": f"Reversal for cancelled POS Sale {sale.sale_number}: {orig.description}",
        })

    return create_journal_entry(
        organization=organization,
        actor=actor,
        txn_date=timezone.now().date(),
        narration=f"Reversal of POS Sale #{sale.sale_number} due to cancellation ({sale.cancellation_reason or 'Voided'})",
        lines=lines,
        reference_type=JournalEntry.ReferenceType.POS_SALE_REVERSAL,
        reference_id=str(sale.id),
        record_audit=True,
    )


@transaction.atomic
def create_pos_sale(
    *,
    organization: Organization,
    actor: User,
    customer_id=None,
    walk_in_customer_name: str = "",
    walk_in_customer_phone: str = "",
    sale_date=None,
    items: list[dict],
    payment_method: str = PosSale.PaymentMethod.CASH,
    payment_reference: str = "",
    discount_amount: Decimal | float | int | str = Decimal("0.00"),
    tax_amount: Decimal | float | int | str = Decimal("0.00"),
    notes: str = "",
) -> PosSale:
    if not items:
        raise PosSaleError("A POS sale must contain at least one line item.")

    discount = Decimal(str(discount_amount or 0))
    tax = Decimal(str(tax_amount or 0))

    if discount < Decimal("0.00"):
        raise PosSaleError("Discount amount cannot be negative.")
    if tax < Decimal("0.00"):
        raise PosSaleError("Tax amount cannot be negative.")

    # 1. Resolve Customer (if registered)
    customer = None
    if customer_id:
        try:
            customer = Customer.objects.for_organization(organization).get(id=customer_id)
        except Customer.DoesNotExist as exc:
            raise PosSaleError("Selected customer does not exist in this organization.") from exc
    elif not walk_in_customer_name.strip():
        walk_in_customer_name = "Walk-in Customer"

    date_of_sale = sale_date or timezone.now().date()
    if isinstance(date_of_sale, str):
        from datetime import datetime
        date_of_sale = datetime.strptime(date_of_sale, "%Y-%m-%d").date()

    # 2. Lock & Validate All Items and Stock
    item_ids = [entry.get("item_id") for entry in items]
    db_items = {
        str(it.id): it
        for it in (
            InventoryItem.objects
            .select_for_update()
            .for_organization(organization)
            .filter(id__in=item_ids)
        )
    }

    if len(db_items) != len(set(item_ids)):
        raise PosSaleError("One or more selected inventory items could not be found.")

    # Generate sequential unique sale number
    count = PosSale.objects.for_organization(organization).count() + 1
    sale_number = f"SALE-{organization.code.upper()}-{count:06d}"
    while PosSale.objects.for_organization(organization).filter(sale_number=sale_number).exists():
        count += 1
        sale_number = f"SALE-{organization.code.upper()}-{count:06d}"

    # Calculate Subtotal & Line Items Server-side
    subtotal = Decimal("0.00")
    prepared_lines = []

    for idx, raw in enumerate(items, start=1):
        item_obj = db_items.get(str(raw.get("item_id")))
        qty = Decimal(str(raw.get("quantity", 1)))
        unit_price = (
            Decimal(str(raw.get("unit_price")))
            if raw.get("unit_price") is not None
            else item_obj.unit_selling_price
        )
        line_discount = Decimal(str(raw.get("line_discount", 0) or 0))

        if qty <= Decimal("0.00"):
            raise PosSaleError(f"Line {idx} ({item_obj.name}): Quantity must be greater than zero.")
        if unit_price < Decimal("0.00"):
            raise PosSaleError(f"Line {idx} ({item_obj.name}): Unit price cannot be negative.")
        if line_discount < Decimal("0.00"):
            raise PosSaleError(f"Line {idx} ({item_obj.name}): Line discount cannot be negative.")

        line_gross = qty * unit_price
        if line_discount > line_gross:
            raise PosSaleError(f"Line {idx} ({item_obj.name}): Line discount exceeds gross line total.")

        line_net = line_gross - line_discount
        subtotal += line_net

        # Stock availability check
        if item_obj.quantity_on_hand < qty:
            raise PosSaleError(
                f"Insufficient stock for '{item_obj.name}'. Requested: {qty}, Available: {item_obj.quantity_on_hand}."
            )

        # Serialized device validation if attached
        device_obj = None
        device_id = raw.get("device_id")
        if device_id:
            try:
                device_obj = (
                    InventoryDevice.objects
                    .select_for_update()
                    .for_organization(organization)
                    .get(id=device_id)
                )
            except InventoryDevice.DoesNotExist as exc:
                raise PosSaleError(f"Device for line {idx} was not found.") from exc

            if device_obj.status != InventoryDevice.Status.AVAILABLE:
                raise PosSaleError(
                    f"Device '{device_obj.asset_tag}' is not available for sale (status: {device_obj.status})."
                )

        prepared_lines.append({
            "item": item_obj,
            "quantity": qty,
            "unit_price": unit_price,
            "unit_cost": item_obj.unit_cost_price,
            "line_discount": line_discount,
            "line_total": line_net,
            "device": device_obj,
        })

    if discount > subtotal:
        raise PosSaleError("Total discount cannot exceed subtotal amount.")

    total_amount = (subtotal - discount) + tax

    # 3. Create Master PosSale
    sale = PosSale.objects.create(
        organization=organization,
        sale_number=sale_number,
        customer=customer,
        walk_in_customer_name=walk_in_customer_name.strip(),
        walk_in_customer_phone=walk_in_customer_phone.strip(),
        sale_date=date_of_sale,
        subtotal_amount=subtotal,
        discount_amount=discount,
        tax_amount=tax,
        total_amount=total_amount,
        paid_amount=total_amount,  # Immediate payment required
        payment_method=payment_method,
        payment_reference=payment_reference.strip(),
        status=PosSale.Status.COMPLETED,
        sold_by=actor,
        notes=notes.strip(),
    )

    # 4. Create Line Items, Deduct Stock, and Record StockMovements
    for line_data in prepared_lines:
        item_obj = line_data["item"]
        qty = line_data["quantity"]

        PosSaleItem.objects.create(
            organization=organization,
            sale=sale,
            item=item_obj,
            quantity=qty,
            unit_price=line_data["unit_price"],
            unit_cost=line_data["unit_cost"],
            line_discount=line_data["line_discount"],
            line_total=line_data["line_total"],
            device=line_data["device"],
        )

        prev_qty = item_obj.quantity_on_hand
        new_qty = prev_qty - qty
        item_obj.quantity_on_hand = new_qty
        item_obj.save(update_fields=["quantity_on_hand", "updated_at"])

        StockMovement.objects.create(
            organization=organization,
            item=item_obj,
            movement_type=StockMovement.MovementType.SALE_DEDUCTION,
            quantity=qty,
            previous_quantity=prev_qty,
            new_quantity=new_qty,
            unit_cost=line_data["unit_cost"],
            reference_type="POS_SALE",
            reference_id=str(sale.id),
            notes=f"Sold via POS Sale #{sale.sale_number}",
            created_by=actor,
        )

        if line_data["device"]:
            dev = line_data["device"]
            dev.status = InventoryDevice.Status.SOLD
            dev.notes = f"{dev.notes}\nSold via POS Sale #{sale.sale_number} on {date_of_sale}".strip()
            dev.save(update_fields=["status", "notes", "updated_at"])

    # 5. Post Accounting Journal Entry
    journal_entry = post_pos_sale_journal_entry(
        organization=organization,
        actor=actor,
        sale=sale,
    )
    if journal_entry:
        sale.journal_entry = journal_entry
        sale.save(update_fields=["journal_entry", "updated_at"])

    # 6. Audit Log
    record_audit_log(
        organization=organization,
        actor=actor,
        action="POS_SALE_COMPLETED",
        resource_type="PosSale",
        resource_id=sale.id,
        metadata={
            "sale_number": sale.sale_number,
            "total_amount": str(total_amount),
            "payment_method": payment_method,
            "items_count": len(prepared_lines),
            "journal_entry_id": str(journal_entry.id) if journal_entry else None,
        },
    )

    return sale


@transaction.atomic
def cancel_pos_sale(
    *,
    organization: Organization,
    actor: User,
    sale_id,
    cancellation_reason: str,
) -> PosSale:
    if not cancellation_reason.strip():
        raise PosSaleError("Cancellation reason is mandatory.")

    try:
        sale = (
            PosSale.objects
            .select_for_update()
            .prefetch_related("items", "items__item", "items__device")
            .for_organization(organization)
            .get(id=sale_id)
        )
    except PosSale.DoesNotExist as exc:
        raise PosSaleError("POS Sale was not found for this organization.") from exc

    if sale.status == PosSale.Status.CANCELLED:
        return sale  # Idempotent return

    # 1. Restore Inventory Stock for each line item
    for line in sale.items.all():
        item_obj = (
            InventoryItem.objects
            .select_for_update()
            .for_organization(organization)
            .get(id=line.item_id)
        )
        prev_qty = item_obj.quantity_on_hand
        new_qty = prev_qty + line.quantity
        item_obj.quantity_on_hand = new_qty
        item_obj.save(update_fields=["quantity_on_hand", "updated_at"])

        StockMovement.objects.create(
            organization=organization,
            item=item_obj,
            movement_type=StockMovement.MovementType.SERVICE_RETURN,
            quantity=line.quantity,
            previous_quantity=prev_qty,
            new_quantity=new_qty,
            unit_cost=line.unit_cost,
            reference_type="POS_SALE_CANCEL",
            reference_id=str(sale.id),
            notes=f"Stock restored from cancelled POS Sale #{sale.sale_number}: {cancellation_reason.strip()}",
            created_by=actor,
        )

        if line.device:
            dev = InventoryDevice.objects.select_for_update().get(id=line.device_id)
            dev.status = InventoryDevice.Status.AVAILABLE
            dev.notes = f"{dev.notes}\nRestored from cancelled POS Sale #{sale.sale_number}".strip()
            dev.save(update_fields=["status", "notes", "updated_at"])

    # 2. Reverse Accounting Journal Entry
    reversal_entry = post_pos_sale_cancellation_journal_entry(
        organization=organization,
        actor=actor,
        sale=sale,
    )

    # 3. Mark Sale as Cancelled
    sale.status = PosSale.Status.CANCELLED
    sale.cancellation_reason = cancellation_reason.strip()
    sale.cancelled_at = timezone.now()
    sale.cancelled_by = actor
    sale.save(update_fields=["status", "cancellation_reason", "cancelled_at", "cancelled_by", "updated_at"])

    # 4. Record Audit Log
    record_audit_log(
        organization=organization,
        actor=actor,
        action="POS_SALE_CANCELLED",
        resource_type="PosSale",
        resource_id=sale.id,
        metadata={
            "sale_number": sale.sale_number,
            "cancellation_reason": cancellation_reason,
            "reversal_journal_entry_id": str(reversal_entry.id) if reversal_entry else None,
        },
    )

    return sale