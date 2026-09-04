from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounting.models import Account, JournalEntry
from accounting.services import get_or_create_default_chart_of_accounts
from customers.models import Customer
from inventory.models import (
    DeviceAssignment,
    InventoryDevice,
    InventoryItem,
    PosSale,
    PosSaleItem,
    StockMovement,
)
from inventory.services import (
    InventoryDomainError,
    PosSaleError,
    cancel_pos_sale,
    create_pos_sale,
    dispose_damaged_stock,
    mark_stock_as_damaged,
    record_stock_adjustment,
    record_stock_restock,
)
from tenancy.models import Organization, OrganizationMembership


User = get_user_model()


class Batch12InventoryPosTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="Nexora Prime", code="NXP")
        self.org_b = Organization.objects.create(name="Other Net", code="OTH")

        self.user_a = User.objects.create_user(
            username="staff_a",
            email="staff_a@nexora.com",
            password="StrongPassword123!",
            first_name="Alice",
            last_name="Staff",
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )

        self.user_b = User.objects.create_user(
            username="staff_b",
            email="staff_b@other.com",
            password="StrongPassword123!",
            first_name="Bob",
            last_name="Other",
        )
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )

        get_or_create_default_chart_of_accounts(organization=self.org_a)
        get_or_create_default_chart_of_accounts(organization=self.org_b)

        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            customer_number="CUST-001",
            first_name="John",
            last_name="Doe",
            phone="03001234567",
            address_line="Street 10, Block B",
            city="Lahore",
        )

        self.item_router = InventoryItem.objects.create(
            organization=self.org_a,
            name="Dual Band Gigabit Router",
            code="RTR-GIG-01",
            category=InventoryItem.Category.ROUTERS_AP,
            unit_of_measure=InventoryItem.Unit.PIECES,
            unit_cost_price=Decimal("4500.00"),
            unit_selling_price=Decimal("6500.00"),
            quantity_on_hand=Decimal("15.00"),
            quantity_damaged=Decimal("0.00"),
            reorder_threshold=5,
        )

        self.item_patch_cord = InventoryItem.objects.create(
            organization=self.org_a,
            name="Fiber Patch Cord 3m SC-UPC",
            code="CBL-PC-3M",
            category=InventoryItem.Category.CABLES_CONNECTORS,
            unit_of_measure=InventoryItem.Unit.PIECES,
            unit_cost_price=Decimal("150.00"),
            unit_selling_price=Decimal("300.00"),
            quantity_on_hand=Decimal("50.00"),
            quantity_damaged=Decimal("2.00"),
            reorder_threshold=10,
        )

        from rest_framework_simplejwt.tokens import RefreshToken

        token_a = RefreshToken.for_user(self.user_a)
        token_a["organization_id"] = str(self.org_a.id)
        self.client_a = APIClient()
        self.client_a.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token_a.access_token)}")

        token_b = RefreshToken.for_user(self.user_b)
        token_b["organization_id"] = str(self.org_b.id)
        self.client_b = APIClient()
        self.client_b.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token_b.access_token)}")

    # --------------------------------------------------------------------------
    # 1. INVENTORY & STOCK WORKFLOW TESTS
    # --------------------------------------------------------------------------

    def test_inventory_item_creation_and_tenant_sku_uniqueness(self):
        """SKU codes must be unique per organization but can be repeated in another org."""
        res_a = self.client_a.post("/api/v1/inventory/items/", {
            "name": "Cat6 UTP Cable 305m",
            "code": "CBL-CAT6-305",
            "category": InventoryItem.Category.CABLES_CONNECTORS,
            "unit_of_measure": InventoryItem.Unit.ROLLS,
            "unit_cost_price": "8500.00",
            "unit_selling_price": "12000.00",
            "quantity_on_hand": "10.00",
            "reorder_threshold": 2,
        }, format="json")
        self.assertEqual(res_a.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_a.data["code"], "CBL-CAT6-305")

        # Duplicate in Org A should fail
        dup_a = self.client_a.post("/api/v1/inventory/items/", {
            "name": "Cat6 Cable Duplicate",
            "code": "CBL-CAT6-305",
            "category": InventoryItem.Category.CABLES_CONNECTORS,
        }, format="json")
        self.assertEqual(dup_a.status_code, status.HTTP_400_BAD_REQUEST)

        # Same code in Org B should succeed
        res_b = self.client_b.post("/api/v1/inventory/items/", {
            "name": "Cat6 Cable Org B",
            "code": "CBL-CAT6-305",
            "category": InventoryItem.Category.CABLES_CONNECTORS,
        }, format="json")
        self.assertEqual(res_b.status_code, status.HTTP_201_CREATED)

    def test_stock_restock_service_and_movement_ledger(self):
        """Restocking increases quantity_on_hand and creates auditable StockMovement."""
        item = record_stock_restock(
            organization=self.org_a,
            actor=self.user_a,
            item_id=self.item_router.id,
            quantity=Decimal("10.00"),
            unit_cost=Decimal("4600.00"),
            notes="New shipment from supplier",
        )
        self.assertEqual(item.quantity_on_hand, Decimal("25.00"))
        self.assertEqual(item.unit_cost_price, Decimal("4600.00"))

        movement = StockMovement.objects.filter(item=self.item_router).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.movement_type, StockMovement.MovementType.PURCHASE_RESTOCK)
        self.assertEqual(movement.quantity, Decimal("10.00"))
        self.assertEqual(movement.previous_quantity, Decimal("15.00"))
        self.assertEqual(movement.new_quantity, Decimal("25.00"))

    def test_stock_adjustment_service(self):
        """Stock adjustment sets exact stock count and logs old/new quantities."""
        item = record_stock_adjustment(
            organization=self.org_a,
            actor=self.user_a,
            item_id=self.item_patch_cord.id,
            new_quantity=Decimal("42.00"),
            reason="Monthly physical count",
            notes="8 patch cords unaccounted for",
        )
        self.assertEqual(item.quantity_on_hand, Decimal("42.00"))

        movement = StockMovement.objects.filter(item=self.item_patch_cord, movement_type=StockMovement.MovementType.MANUAL_ADJUSTMENT).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.previous_quantity, Decimal("50.00"))
        self.assertEqual(movement.new_quantity, Decimal("42.00"))

    def test_damage_and_disposal_workflow(self):
        """Marking items as damaged decreases sellable stock and increases damaged stock."""
        item = mark_stock_as_damaged(
            organization=self.org_a,
            actor=self.user_a,
            item_id=self.item_router.id,
            quantity=Decimal("3.00"),
            notes="Water damage in warehouse",
        )
        self.assertEqual(item.quantity_on_hand, Decimal("12.00"))
        self.assertEqual(item.quantity_damaged, Decimal("3.00"))

        # Cannot mark more as damaged than available on hand
        with self.assertRaises(InventoryDomainError):
            mark_stock_as_damaged(
                organization=self.org_a,
                actor=self.user_a,
                item_id=self.item_router.id,
                quantity=Decimal("20.00"),
            )

        # Dispose damaged stock
        disposed_item = dispose_damaged_stock(
            organization=self.org_a,
            actor=self.user_a,
            item_id=self.item_router.id,
            quantity=Decimal("2.00"),
            notes="Scrapped and written off",
        )
        self.assertEqual(disposed_item.quantity_damaged, Decimal("1.00"))
        self.assertEqual(disposed_item.quantity_on_hand, Decimal("12.00"))

    # --------------------------------------------------------------------------
    # 2. POS SALES & CHECKOUT WORKFLOW TESTS
    # --------------------------------------------------------------------------

    def test_pos_sale_single_item_cash_and_gl_journal(self):
        """Single item walk-in cash sale creates sale, deducts stock, and posts balanced GL journal."""
        initial_stock = self.item_router.quantity_on_hand

        sale = create_pos_sale(
            organization=self.org_a,
            actor=self.user_a,
            walk_in_customer_name="Walk-in Subscriber",
            walk_in_customer_phone="03009998877",
            items=[
                {
                    "item_id": str(self.item_router.id),
                    "quantity": "2",
                    "unit_price": "6500.00",
                }
            ],
            payment_method=PosSale.PaymentMethod.CASH,
            discount_amount="500.00",
            tax_amount="0.00",
            notes="Counter sale with cash receipt",
        )

        self.assertEqual(sale.status, PosSale.Status.COMPLETED)
        self.assertEqual(sale.subtotal_amount, Decimal("13000.00"))
        self.assertEqual(sale.discount_amount, Decimal("500.00"))
        self.assertEqual(sale.total_amount, Decimal("12500.00"))
        self.assertEqual(sale.paid_amount, Decimal("12500.00"))

        # Verify stock deducted
        self.item_router.refresh_from_db()
        self.assertEqual(self.item_router.quantity_on_hand, initial_stock - Decimal("2.00"))

        # Verify stock movement
        movement = StockMovement.objects.filter(reference_id=str(sale.id)).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.movement_type, StockMovement.MovementType.SALE_DEDUCTION)
        self.assertEqual(movement.quantity, Decimal("2.00"))

        # Verify Accounting Journal Entry
        self.assertIsNotNone(sale.journal_entry)
        entry = sale.journal_entry
        self.assertEqual(entry.reference_type, JournalEntry.ReferenceType.POS_SALE)
        self.assertEqual(entry.reference_id, str(sale.id))

        lines = entry.lines.all()
        self.assertEqual(lines.count(), 2)

        dr_cash = lines.get(account__code="1000")
        cr_rev = lines.get(account__code="4020")
        self.assertEqual(dr_cash.debit, Decimal("12500.00"))
        self.assertEqual(dr_cash.credit, Decimal("0.00"))
        self.assertEqual(cr_rev.credit, Decimal("12500.00"))
        self.assertEqual(cr_rev.debit, Decimal("0.00"))

    def test_pos_sale_registered_customer_bank_transfer_and_device(self):
        """Multi-item sale to registered customer with serialized device attached."""
        cpe_device = InventoryDevice.objects.create(
            organization=self.org_a,
            asset_tag="DEV-RTR-9001",
            device_type=InventoryDevice.DeviceType.ROUTER,
            manufacturer="TP-Link",
            model_name="Archer C6",
            serial_number="SN9988776655",
            mac_address="AA:BB:CC:DD:EE:01",
            status=InventoryDevice.Status.AVAILABLE,
        )

        sale = create_pos_sale(
            organization=self.org_a,
            actor=self.user_a,
            customer_id=self.customer_a.id,
            items=[
                {
                    "item_id": str(self.item_router.id),
                    "quantity": "1",
                    "unit_price": "6500.00",
                    "device_id": str(cpe_device.id),
                },
                {
                    "item_id": str(self.item_patch_cord.id),
                    "quantity": "3",
                    "unit_price": "300.00",
                }
            ],
            payment_method=PosSale.PaymentMethod.BANK_TRANSFER,
            payment_reference="MEZN-TXN-987654",
        )

        self.assertEqual(sale.customer, self.customer_a)
        self.assertEqual(sale.total_amount, Decimal("7400.00"))
        self.assertEqual(sale.payment_method, PosSale.PaymentMethod.BANK_TRANSFER)

        cpe_device.refresh_from_db()
        self.assertEqual(cpe_device.status, InventoryDevice.Status.SOLD)

        # Verify Bank account debited
        entry = sale.journal_entry
        dr_bank = entry.lines.get(account__code="1010")
        self.assertEqual(dr_bank.debit, Decimal("7400.00"))

    def test_pos_sale_insufficient_stock_rejection(self):
        """Attempting to sell more stock than available must fail atomically."""
        with self.assertRaises(PosSaleError):
            create_pos_sale(
                organization=self.org_a,
                actor=self.user_a,
                walk_in_customer_name="Greedy Buyer",
                items=[
                    {
                        "item_id": str(self.item_router.id),
                        "quantity": "100",  # Only 15 in stock
                        "unit_price": "6500.00",
                    }
                ],
            )

        # Stock remains untouched
        self.item_router.refresh_from_db()
        self.assertEqual(self.item_router.quantity_on_hand, Decimal("15.00"))
        self.assertEqual(PosSale.objects.filter(organization=self.org_a).count(), 0)

    # --------------------------------------------------------------------------
    # 3. SALE CANCELLATION & STOCK / GL REVERSAL
    # --------------------------------------------------------------------------

    def test_pos_sale_cancellation_and_reversal(self):
        """Cancelling a POS sale restores inventory stock and posts reversal GL journal entry."""
        cpe_device = InventoryDevice.objects.create(
            organization=self.org_a,
            asset_tag="DEV-CPE-5544",
            device_type=InventoryDevice.DeviceType.ONU,
            status=InventoryDevice.Status.AVAILABLE,
        )

        sale = create_pos_sale(
            organization=self.org_a,
            actor=self.user_a,
            walk_in_customer_name="Return Customer",
            items=[
                {
                    "item_id": str(self.item_router.id),
                    "quantity": "1",
                    "device_id": str(cpe_device.id),
                }
            ],
            payment_method=PosSale.PaymentMethod.CASH,
        )

        self.item_router.refresh_from_db()
        self.assertEqual(self.item_router.quantity_on_hand, Decimal("14.00"))
        cpe_device.refresh_from_db()
        self.assertEqual(cpe_device.status, InventoryDevice.Status.SOLD)

        # Cancel sale
        cancelled_sale = cancel_pos_sale(
            organization=self.org_a,
            actor=self.user_a,
            sale_id=sale.id,
            cancellation_reason="Customer changed mind before leaving store",
        )

        self.assertEqual(cancelled_sale.status, PosSale.Status.CANCELLED)
        self.assertEqual(cancelled_sale.cancelled_by, self.user_a)

        # Stock restored
        self.item_router.refresh_from_db()
        self.assertEqual(self.item_router.quantity_on_hand, Decimal("15.00"))

        cpe_device.refresh_from_db()
        self.assertEqual(cpe_device.status, InventoryDevice.Status.AVAILABLE)

        # Reversal Journal Entry
        reversal_entry = JournalEntry.objects.filter(
            reference_type=JournalEntry.ReferenceType.POS_SALE_REVERSAL,
            reference_id=str(sale.id),
        ).first()
        self.assertIsNotNone(reversal_entry)

        dr_rev = reversal_entry.lines.get(account__code="4020")
        cr_cash = reversal_entry.lines.get(account__code="1000")
        self.assertEqual(dr_rev.debit, Decimal("6500.00"))
        self.assertEqual(cr_cash.credit, Decimal("6500.00"))

    # --------------------------------------------------------------------------
    # 4. TENANT ISOLATION & API TESTS
    # --------------------------------------------------------------------------

    def test_tenant_isolation_on_inventory_and_pos_api(self):
        """Tenant B cannot access or sell Tenant A items via API."""
        # Tenant B lists items -> must not see Tenant A's router
        res_b = self.client_b.get("/api/v1/inventory/items/")
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)
        ids_b = [item["id"] for item in res_b.data["results"]]
        self.assertNotIn(str(self.item_router.id), ids_b)

        # Tenant B attempts to sell Tenant A item -> 400 error
        res_sale = self.client_b.post("/api/v1/pos/sales/", {
            "walk_in_customer_name": "Intruder Buyer",
            "items": [
                {
                    "item_id": str(self.item_router.id),
                    "quantity": "1",
                }
            ],
            "payment_method": "CASH",
        }, format="json")
        self.assertEqual(res_sale.status_code, status.HTTP_400_BAD_REQUEST)
