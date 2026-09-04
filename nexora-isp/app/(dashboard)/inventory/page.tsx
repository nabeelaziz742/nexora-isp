"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Archive,
  ArrowDownRight,
  ArrowUpRight,
  Box,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  Clock,
  Filter,
  Layers,
  Loader2,
  Package,
  PackageCheck,
  PackageMinus,
  PackagePlus,
  PackageX,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  Tag,
  Trash2,
  Wrench,
  X,
} from "lucide-react";

import {
  type DeviceAssignment,
  type InventoryDevice,
  type InventoryItem,
  type InventoryItemCategory,
  type InventoryItemUnit,
  type ReturnCondition,
  type StockMovement,
  inventoryService,
} from "@/services/inventory.service";
import Skeleton from "@/components/ui/Skeleton";

function formatDate(value: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-PK", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<"items" | "devices" | "movements">("items");

  // Items State
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(true);
  const [itemCategory, setItemCategory] = useState<string>("ALL");
  const [itemSearch, setItemSearch] = useState<string>("");
  const [lowStockOnly, setLowStockOnly] = useState<boolean>(false);

  // Serialized Devices State
  const [devices, setDevices] = useState<InventoryDevice[]>([]);
  const [assignments, setAssignments] = useState<DeviceAssignment[]>([]);
  const [devicesLoading, setDevicesLoading] = useState(false);
  const [deviceSearch, setDeviceSearch] = useState<string>("");
  const [deviceStatus, setDeviceStatus] = useState<string>("ALL");

  // Movements State
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [movementsLoading, setMovementsLoading] = useState(false);
  const [movementSearch, setMovementSearch] = useState<string>("");

  // Modals State
  const [showCreateItemModal, setShowCreateItemModal] = useState(false);
  const [restockModalItem, setRestockModalItem] = useState<InventoryItem | null>(null);
  const [adjustModalItem, setAdjustModalItem] = useState<InventoryItem | null>(null);
  const [damageModalItem, setDamageModalItem] = useState<InventoryItem | null>(null);
  const [disposeModalItem, setDisposeModalItem] = useState<InventoryItem | null>(null);
  const [returnModalAssignment, setReturnModalAssignment] = useState<DeviceAssignment | null>(null);

  // Form Submissions
  const [submitting, setSubmitting] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // New Item Form Data
  const [newItemData, setNewItemData] = useState({
    name: "",
    code: "",
    category: "ACCESSORIES" as InventoryItemCategory,
    unit_of_measure: "PIECES" as InventoryItemUnit,
    unit_cost_price: "",
    unit_selling_price: "",
    quantity_on_hand: "0",
    reorder_threshold: 5,
    notes: "",
  });

  // Action Form Inputs
  const [actionQuantity, setActionQuantity] = useState<string>("");
  const [actionUnitCost, setActionUnitCost] = useState<string>("");
  const [actionReason, setActionReason] = useState<string>("");
  const [actionNotes, setActionNotes] = useState<string>("");
  const [returnCondition, setReturnCondition] = useState<ReturnCondition>("GOOD");

  // Load Inventory Items
  const loadItems = useCallback(async () => {
    setItemsLoading(true);
    try {
      const res = await inventoryService.getItems({
        category: itemCategory !== "ALL" ? itemCategory : undefined,
        search: itemSearch || undefined,
        low_stock: lowStockOnly || undefined,
      });
      setItems(res.results || []);
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Failed to load inventory items." });
    } finally {
      setItemsLoading(false);
    }
  }, [itemCategory, itemSearch, lowStockOnly]);

  // Load Devices & Assignments
  const loadDevices = useCallback(async () => {
    setDevicesLoading(true);
    try {
      const [devList, assignList] = await Promise.all([
        inventoryService.getDevices(),
        inventoryService.getAssignments(),
      ]);
      setDevices(devList || []);
      setAssignments(assignList || []);
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Failed to load devices." });
    } finally {
      setDevicesLoading(false);
    }
  }, []);

  // Load Movements
  const loadMovements = useCallback(async () => {
    setMovementsLoading(true);
    try {
      const res = await inventoryService.getMovements({
        search: movementSearch || undefined,
      });
      setMovements(res.results || []);
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Failed to load stock movements." });
    } finally {
      setMovementsLoading(false);
    }
  }, [movementSearch]);

  useEffect(() => {
    if (activeTab === "items") loadItems();
    else if (activeTab === "devices") loadDevices();
    else if (activeTab === "movements") loadMovements();
  }, [activeTab, loadItems, loadDevices, loadMovements]);

  // Metrics
  const itemMetrics = useMemo(() => {
    const totalItems = items.length;
    const lowStockCount = items.filter((i) => i.is_low_stock).length;
    const totalStockValue = items.reduce(
      (sum, i) => sum + parseFloat(i.quantity_on_hand || "0") * parseFloat(i.unit_cost_price || "0"),
      0
    );
    const damagedUnits = items.reduce((sum, i) => sum + parseFloat(i.quantity_damaged || "0"), 0);
    return { totalItems, lowStockCount, totalStockValue, damagedUnits };
  }, [items]);

  // Handle Item Creation
  const handleCreateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemData.name || !newItemData.code) {
      setNotification({ type: "error", message: "Item name and SKU code are required." });
      return;
    }
    setSubmitting(true);
    try {
      await inventoryService.createItem(newItemData);
      setNotification({ type: "success", message: "Inventory item SKU created successfully!" });
      setShowCreateItemModal(false);
      setNewItemData({
        name: "",
        code: "",
        category: "ACCESSORIES",
        unit_of_measure: "PIECES",
        unit_cost_price: "",
        unit_selling_price: "",
        quantity_on_hand: "0",
        reorder_threshold: 5,
        notes: "",
      });
      loadItems();
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Failed to create item." });
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Restock
  const handleRestock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!restockModalItem || !actionQuantity) return;
    setSubmitting(true);
    try {
      await inventoryService.restockItem(restockModalItem.id, {
        quantity: actionQuantity,
        unit_cost: actionUnitCost || undefined,
        notes: actionNotes,
      });
      setNotification({ type: "success", message: `Successfully restocked ${restockModalItem.name}.` });
      setRestockModalItem(null);
      setActionQuantity("");
      setActionUnitCost("");
      setActionNotes("");
      loadItems();
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Restock failed." });
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Adjust
  const handleAdjust = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adjustModalItem || actionQuantity === "") return;
    setSubmitting(true);
    try {
      await inventoryService.adjustItem(adjustModalItem.id, {
        new_quantity: actionQuantity,
        reason: actionReason || "Physical Inventory Audit",
        notes: actionNotes,
      });
      setNotification({ type: "success", message: `Stock adjusted for ${adjustModalItem.name}.` });
      setAdjustModalItem(null);
      setActionQuantity("");
      setActionReason("");
      setActionNotes("");
      loadItems();
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Stock adjustment failed." });
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Damage
  const handleDamage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!damageModalItem || !actionQuantity) return;
    setSubmitting(true);
    try {
      await inventoryService.damageItem(damageModalItem.id, {
        quantity: actionQuantity,
        notes: actionNotes,
      });
      setNotification({ type: "success", message: `Transferred ${actionQuantity} units to damaged stock.` });
      setDamageModalItem(null);
      setActionQuantity("");
      setActionNotes("");
      loadItems();
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Failed to mark damage." });
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Dispose
  const handleDispose = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disposeModalItem || !actionQuantity) return;
    setSubmitting(true);
    try {
      await inventoryService.disposeItem(disposeModalItem.id, {
        quantity: actionQuantity,
        notes: actionNotes,
      });
      setNotification({ type: "success", message: `Disposed ${actionQuantity} damaged units.` });
      setDisposeModalItem(null);
      setActionQuantity("");
      setActionNotes("");
      loadItems();
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Failed to dispose stock." });
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Device Return
  const handleReturnDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!returnModalAssignment) return;
    setSubmitting(true);
    try {
      await inventoryService.returnDevice(returnModalAssignment.id, returnCondition, actionNotes);
      setNotification({ type: "success", message: "Device returned to inventory successfully." });
      setReturnModalAssignment(null);
      setActionNotes("");
      loadDevices();
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Failed to return device." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">Inventory & Hardware</h1>
            <span className="inline-flex items-center rounded-md bg-blue-500/10 px-2 py-0.5 text-xs font-medium text-blue-400 border border-blue-500/20">
              Audit Tracked
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Quantity stock management, serialized CPE custody, and double-entry stock movement ledger.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => (activeTab === "items" ? loadItems() : activeTab === "devices" ? loadDevices() : loadMovements())}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>

          {activeTab === "items" && (
            <button
              onClick={() => setShowCreateItemModal(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-500 transition"
            >
              <Plus className="h-4 w-4" />
              Add Inventory SKU
            </button>
          )}
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          className={`flex items-center justify-between rounded-lg border p-4 ${
            notification.type === "success"
              ? "border-emerald-500/30 bg-emerald-950/40 text-emerald-300"
              : "border-rose-500/30 bg-rose-950/40 text-rose-300"
          }`}
        >
          <div className="flex items-center gap-3">
            {notification.type === "success" ? <CheckCircle2 className="h-5 w-5 text-emerald-400" /> : <AlertCircle className="h-5 w-5 text-rose-400" />}
            <span className="text-sm font-medium">{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-slate-400 hover:text-slate-200">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex border-b border-slate-800">
        <button
          onClick={() => setActiveTab("items")}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition ${
            activeTab === "items"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Box className="h-4 w-4" />
          Item Catalog & Stock ({items.length})
        </button>

        <button
          onClick={() => setActiveTab("devices")}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition ${
            activeTab === "devices"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Wrench className="h-4 w-4" />
          CPE Devices & Custody ({devices.length})
        </button>

        <button
          onClick={() => setActiveTab("movements")}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition ${
            activeTab === "movements"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Clock className="h-4 w-4" />
          Stock Movements Ledger
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: ITEM CATALOG & STOCK */}
      {/* ========================================================================= */}
      {activeTab === "items" && (
        <div className="space-y-5">
          {/* Metrics */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Total SKUs</span>
              <p className="mt-2 text-2xl font-bold text-slate-100">{itemMetrics.totalItems}</p>
              <p className="mt-1 text-xs text-slate-500">Active catalog items</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Valuation (Cost)</span>
              <p className="mt-2 text-2xl font-bold text-slate-100 font-mono">
                PKR {itemMetrics.totalStockValue.toLocaleString("en-PK", { minimumFractionDigits: 0 })}
              </p>
              <p className="mt-1 text-xs text-slate-500">Current warehouse valuation</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Low Stock Alerts</span>
              <p className={`mt-2 text-2xl font-bold ${itemMetrics.lowStockCount > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                {itemMetrics.lowStockCount}
              </p>
              <p className="mt-1 text-xs text-slate-500">Items below reorder limit</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Damaged Stock</span>
              <p className="mt-2 text-2xl font-bold text-rose-400 font-mono">{itemMetrics.damagedUnits}</p>
              <p className="mt-1 text-xs text-slate-500">Awaiting disposal / write-off</p>
            </div>
          </div>

          {/* Filters */}
          <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search SKU by name, code, or description..."
                value={itemSearch}
                onChange={(e) => setItemSearch(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 py-2 pl-9 pr-4 text-xs text-slate-100 placeholder-slate-400 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-3">
              <select
                value={itemCategory}
                onChange={(e) => setItemCategory(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="ALL">All Categories</option>
                <option value="CABLES_CONNECTORS">Cables & Connectors</option>
                <option value="OPTICAL_SPLITTERS">Optical Splitters</option>
                <option value="ROUTERS_AP">Routers & Access Points</option>
                <option value="ONU_ONT">ONU / ONT Devices</option>
                <option value="POWER_ADAPTERS">Power Adapters</option>
                <option value="ACCESSORIES">Hardware & Accessories</option>
                <option value="TOOLS_EQUIPMENT">Tools & Field Gear</option>
                <option value="OTHER">Other</option>
              </select>

              <button
                onClick={() => setLowStockOnly(!lowStockOnly)}
                className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-semibold transition ${
                  lowStockOnly
                    ? "border-amber-500/50 bg-amber-500/10 text-amber-400"
                    : "border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-700"
                }`}
              >
                <AlertTriangle className="h-3.5 w-3.5" />
                Low Stock Only
              </button>
            </div>
          </div>

          {/* Items Table */}
          <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm">
            {itemsLoading ? (
              <div className="p-8 space-y-4">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : items.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-12 text-center">
                <Box className="h-12 w-12 text-slate-600 mb-3" />
                <h3 className="text-base font-semibold text-slate-300">No Inventory SKUs Found</h3>
                <p className="mt-1 text-xs text-slate-500 max-w-sm">
                  Add hardware items, fiber splitters, patch cords, or routers to begin quantity tracking.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="border-b border-slate-800 bg-slate-950/60 font-semibold uppercase tracking-wider text-slate-400">
                    <tr>
                      <th className="px-4 py-3.5">SKU / Code</th>
                      <th className="px-4 py-3.5">Item Name</th>
                      <th className="px-4 py-3.5">Category</th>
                      <th className="px-4 py-3.5 text-right">In Stock</th>
                      <th className="px-4 py-3.5 text-right">Damaged</th>
                      <th className="px-4 py-3.5 text-right">Cost (PKR)</th>
                      <th className="px-4 py-3.5 text-right">Sell (PKR)</th>
                      <th className="px-4 py-3.5 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-800/40 transition">
                        <td className="px-4 py-3.5 font-mono font-semibold text-slate-100">{item.code}</td>
                        <td className="px-4 py-3.5 font-medium text-slate-200">
                          {item.name}
                          {item.is_low_stock && (
                            <span className="ml-2 inline-flex items-center rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-400 border border-amber-500/20">
                              Low Stock
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-slate-400">{item.category}</td>
                        <td className="px-4 py-3.5 text-right font-mono font-bold text-slate-100">
                          {parseFloat(item.quantity_on_hand).toLocaleString()} {item.unit_of_measure.toLowerCase()}
                        </td>
                        <td className="px-4 py-3.5 text-right font-mono text-rose-400">
                          {parseFloat(item.quantity_damaged) > 0 ? `${item.quantity_damaged}` : "0"}
                        </td>
                        <td className="px-4 py-3.5 text-right font-mono text-slate-400">
                          {parseFloat(item.unit_cost_price).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-3.5 text-right font-mono font-medium text-emerald-400">
                          {parseFloat(item.unit_selling_price).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-3.5 text-center">
                          <div className="flex items-center justify-center gap-1.5">
                            <button
                              onClick={() => {
                                setRestockModalItem(item);
                                setActionQuantity("");
                                setActionUnitCost(item.unit_cost_price);
                              }}
                              className="rounded bg-blue-500/10 px-2 py-1 text-[11px] font-semibold text-blue-400 hover:bg-blue-500/20 border border-blue-500/20"
                              title="Restock Inventory"
                            >
                              + Stock
                            </button>
                            <button
                              onClick={() => {
                                setAdjustModalItem(item);
                                setActionQuantity(item.quantity_on_hand);
                              }}
                              className="rounded bg-slate-800 px-2 py-1 text-[11px] font-semibold text-slate-300 hover:bg-slate-700 border border-slate-700"
                              title="Manual Stock Adjustment"
                            >
                              Adjust
                            </button>
                            <button
                              onClick={() => {
                                setDamageModalItem(item);
                                setActionQuantity("");
                              }}
                              className="rounded bg-rose-500/10 px-2 py-1 text-[11px] font-semibold text-rose-400 hover:bg-rose-500/20 border border-rose-500/20"
                              title="Mark Damaged"
                            >
                              Damage
                            </button>
                            {parseFloat(item.quantity_damaged) > 0 && (
                              <button
                                onClick={() => {
                                  setDisposeModalItem(item);
                                  setActionQuantity(item.quantity_damaged);
                                }}
                                className="rounded bg-amber-500/10 px-2 py-1 text-[11px] font-semibold text-amber-400 hover:bg-amber-500/20 border border-amber-500/20"
                                title="Dispose Damaged"
                              >
                                Dispose
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: CPE DEVICES & CUSTODY */}
      {/* ========================================================================= */}
      {activeTab === "devices" && (
        <div className="space-y-5">
          <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm">
            {devicesLoading ? (
              <div className="p-8 space-y-4">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : devices.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-12 text-center">
                <Wrench className="h-12 w-12 text-slate-600 mb-3" />
                <h3 className="text-base font-semibold text-slate-300">No Serialized CPE Devices Found</h3>
                <p className="mt-1 text-xs text-slate-500 max-w-sm">
                  Serialized devices (ONUs, Routers) attached to customer connections will appear here.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="border-b border-slate-800 bg-slate-950/60 font-semibold uppercase tracking-wider text-slate-400">
                    <tr>
                      <th className="px-4 py-3.5">Asset Tag</th>
                      <th className="px-4 py-3.5">Type & Model</th>
                      <th className="px-4 py-3.5">Serial / MAC</th>
                      <th className="px-4 py-3.5">Status</th>
                      <th className="px-4 py-3.5">Assigned Custody</th>
                      <th className="px-4 py-3.5 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {devices.map((dev) => (
                      <tr key={dev.id} className="hover:bg-slate-800/40 transition">
                        <td className="px-4 py-3.5 font-mono font-semibold text-slate-100">{dev.asset_tag}</td>
                        <td className="px-4 py-3.5">
                          <div className="font-medium text-slate-200">{dev.model_name || dev.device_type}</div>
                          <div className="text-[11px] text-slate-500">{dev.manufacturer || "Generic"}</div>
                        </td>
                        <td className="px-4 py-3.5 font-mono text-[11px] text-slate-400">
                          <div>SN: {dev.serial_number || "—"}</div>
                          <div>MAC: {dev.mac_address || "—"}</div>
                        </td>
                        <td className="px-4 py-3.5">
                          <span
                            className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold border ${
                              dev.status === "AVAILABLE"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : dev.status === "ASSIGNED"
                                ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                                : dev.status === "SOLD"
                                ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                                : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                            }`}
                          >
                            {dev.status}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          {dev.assigned_service_number ? (
                            <div>
                              <div className="font-medium text-slate-200">{dev.assigned_customer_name}</div>
                              <div className="text-[11px] text-slate-400 font-mono">
                                Acc: {dev.assigned_service_number} ({dev.assigned_customer_number})
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-500">In Warehouse</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-center">
                          {dev.active_assignment_id && (
                            <button
                              onClick={() => {
                                const assign = assignments.find((a) => a.id === dev.active_assignment_id);
                                if (assign) setReturnModalAssignment(assign);
                              }}
                              className="rounded bg-rose-500/10 px-2.5 py-1 text-[11px] font-semibold text-rose-400 hover:bg-rose-500/20 border border-rose-500/20"
                            >
                              Return Device
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: STOCK MOVEMENTS LEDGER */}
      {/* ========================================================================= */}
      {activeTab === "movements" && (
        <div className="space-y-5">
          <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm">
            {movementsLoading ? (
              <div className="p-8 space-y-4">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : movements.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-12 text-center">
                <Clock className="h-12 w-12 text-slate-600 mb-3" />
                <h3 className="text-base font-semibold text-slate-300">No Stock Movements Yet</h3>
                <p className="mt-1 text-xs text-slate-500 max-w-sm">
                  All restocks, POS sales deductions, damage transfers, and cycle count adjustments are recorded here.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="border-b border-slate-800 bg-slate-950/60 font-semibold uppercase tracking-wider text-slate-400">
                    <tr>
                      <th className="px-4 py-3.5">Timestamp</th>
                      <th className="px-4 py-3.5">Item SKU</th>
                      <th className="px-4 py-3.5">Movement Type</th>
                      <th className="px-4 py-3.5 text-right">Quantity</th>
                      <th className="px-4 py-3.5 text-right">Before &rarr; After</th>
                      <th className="px-4 py-3.5">Reference / Notes</th>
                      <th className="px-4 py-3.5">Actor</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {movements.map((m) => (
                      <tr key={m.id} className="hover:bg-slate-800/40 transition">
                        <td className="px-4 py-3.5 text-slate-400 whitespace-nowrap">{formatDate(m.created_at)}</td>
                        <td className="px-4 py-3.5 font-mono font-medium text-slate-200">
                          <div>{m.item_name}</div>
                          <div className="text-[11px] text-slate-500">{m.item_code}</div>
                        </td>
                        <td className="px-4 py-3.5">
                          <span
                            className={`inline-flex items-center rounded px-2 py-0.5 text-[10px] font-semibold border ${
                              m.movement_type.includes("RESTOCK") || m.movement_type.includes("RETURN")
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : m.movement_type.includes("SALE")
                                ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                                : m.movement_type.includes("DAMAGE")
                                ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                                : "bg-slate-800 text-slate-300 border-slate-700"
                            }`}
                          >
                            {m.movement_type}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-right font-mono font-bold text-slate-100">
                          {parseFloat(m.quantity).toLocaleString()}
                        </td>
                        <td className="px-4 py-3.5 text-right font-mono text-[11px] text-slate-400">
                          {parseFloat(m.previous_quantity).toLocaleString()} &rarr;{" "}
                          <span className="text-slate-200 font-semibold">{parseFloat(m.new_quantity).toLocaleString()}</span>
                        </td>
                        <td className="px-4 py-3.5 text-slate-300 max-w-xs truncate">
                          {m.reference_id && <span className="font-mono text-slate-400 mr-1">[{m.reference_id}]</span>}
                          {m.notes || "—"}
                        </td>
                        <td className="px-4 py-3.5 text-slate-400">{m.created_by_name || "System"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 1: ADD NEW SKU */}
      {/* ========================================================================= */}
      {showCreateItemModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="text-base font-semibold text-slate-100">Create Inventory Item SKU</h3>
              <button onClick={() => setShowCreateItemModal(false)} className="text-slate-400 hover:text-slate-200">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleCreateItem} className="mt-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300">Item Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Dual Band Wi-Fi Router"
                    value={newItemData.name}
                    onChange={(e) => setNewItemData({ ...newItemData, name: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300">SKU / Code *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. RTR-GIG-01"
                    value={newItemData.code}
                    onChange={(e) => setNewItemData({ ...newItemData, code: e.target.value.toUpperCase() })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 font-mono focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300">Category *</label>
                  <select
                    value={newItemData.category}
                    onChange={(e) => setNewItemData({ ...newItemData, category: e.target.value as any })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="CABLES_CONNECTORS">Cables & Connectors</option>
                    <option value="OPTICAL_SPLITTERS">Optical Splitters</option>
                    <option value="ROUTERS_AP">Routers & Access Points</option>
                    <option value="ONU_ONT">ONU / ONT Devices</option>
                    <option value="POWER_ADAPTERS">Power Adapters</option>
                    <option value="ACCESSORIES">Hardware & Accessories</option>
                    <option value="TOOLS_EQUIPMENT">Tools & Field Gear</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300">Unit of Measure *</label>
                  <select
                    value={newItemData.unit_of_measure}
                    onChange={(e) => setNewItemData({ ...newItemData, unit_of_measure: e.target.value as any })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="PIECES">Pieces (Pcs)</option>
                    <option value="METERS">Meters (m)</option>
                    <option value="ROLLS">Rolls</option>
                    <option value="PACKS">Packs</option>
                    <option value="BOXES">Boxes</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300">Unit Cost Price (PKR)</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={newItemData.unit_cost_price}
                    onChange={(e) => setNewItemData({ ...newItemData, unit_cost_price: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 font-mono focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300">Unit Selling Price (PKR)</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={newItemData.unit_selling_price}
                    onChange={(e) => setNewItemData({ ...newItemData, unit_selling_price: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 font-mono focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 border-t border-slate-800 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateItemModal(false)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-blue-600 px-5 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  Create SKU
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: RESTOCK */}
      {/* ========================================================================= */}
      {restockModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="text-base font-semibold text-slate-100">Restock {restockModalItem.name}</h3>
              <button onClick={() => setRestockModalItem(null)} className="text-slate-400 hover:text-slate-200">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleRestock} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Quantity to Add *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  placeholder="e.g. 50"
                  value={actionQuantity}
                  onChange={(e) => setActionQuantity(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 font-mono focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300">Unit Cost Price (PKR)</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder={restockModalItem.unit_cost_price}
                  value={actionUnitCost}
                  onChange={(e) => setActionUnitCost(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 font-mono focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300">Notes / Supplier</label>
                <input
                  type="text"
                  placeholder="e.g. Invoice #9981 from Tech Distro"
                  value={actionNotes}
                  onChange={(e) => setActionNotes(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="flex justify-end gap-3 border-t border-slate-800 pt-4">
                <button
                  type="button"
                  onClick={() => setRestockModalItem(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-blue-600 px-5 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  Confirm Restock
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 3: ADJUST */}
      {/* ========================================================================= */}
      {adjustModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="text-base font-semibold text-slate-100">Adjust Stock Count ({adjustModalItem.name})</h3>
              <button onClick={() => setAdjustModalItem(null)} className="text-slate-400 hover:text-slate-200">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleAdjust} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Exact New Quantity on Hand *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={actionQuantity}
                  onChange={(e) => setActionQuantity(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 font-mono focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300">Reason for Adjustment *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Monthly Physical Count / Cycle Audit"
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="flex justify-end gap-3 border-t border-slate-800 pt-4">
                <button
                  type="button"
                  onClick={() => setAdjustModalItem(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-blue-600 px-5 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  Save Adjustment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 4: DAMAGE */}
      {/* ========================================================================= */}
      {damageModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="text-base font-semibold text-rose-400">Mark Damaged Stock ({damageModalItem.name})</h3>
              <button onClick={() => setDamageModalItem(null)} className="text-slate-400 hover:text-slate-200">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleDamage} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Quantity Damaged *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={damageModalItem.quantity_on_hand}
                  required
                  placeholder="e.g. 2"
                  value={actionQuantity}
                  onChange={(e) => setActionQuantity(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 font-mono focus:border-rose-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300">Damage Details</label>
                <input
                  type="text"
                  placeholder="e.g. Short circuit / Water leakage"
                  value={actionNotes}
                  onChange={(e) => setActionNotes(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-rose-500 focus:outline-none"
                />
              </div>
              <div className="flex justify-end gap-3 border-t border-slate-800 pt-4">
                <button
                  type="button"
                  onClick={() => setDamageModalItem(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-rose-600 px-5 py-2 text-xs font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
                >
                  Transfer to Damaged
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 5: DISPOSE */}
      {/* ========================================================================= */}
      {disposeModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="text-base font-semibold text-amber-400">Dispose Damaged Stock ({disposeModalItem.name})</h3>
              <button onClick={() => setDisposeModalItem(null)} className="text-slate-400 hover:text-slate-200">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleDispose} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Quantity to Dispose / Scrap *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={disposeModalItem.quantity_damaged}
                  required
                  value={actionQuantity}
                  onChange={(e) => setActionQuantity(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 font-mono focus:border-amber-500 focus:outline-none"
                />
              </div>
              <div className="flex justify-end gap-3 border-t border-slate-800 pt-4">
                <button
                  type="button"
                  onClick={() => setDisposeModalItem(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-amber-600 px-5 py-2 text-xs font-semibold text-white hover:bg-amber-500 disabled:opacity-50"
                >
                  Confirm Disposal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 6: DEVICE RETURN */}
      {/* ========================================================================= */}
      {returnModalAssignment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="text-base font-semibold text-slate-100">
                Return Device ({returnModalAssignment.asset_tag})
              </h3>
              <button onClick={() => setReturnModalAssignment(null)} className="text-slate-400 hover:text-slate-200">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleReturnDevice} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Return Condition *</label>
                <select
                  value={returnCondition}
                  onChange={(e) => setReturnCondition(e.target.value as ReturnCondition)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
                >
                  <option value="GOOD">Good / Working (Return to Available Stock)</option>
                  <option value="FAULTY">Faulty / Defective (Return to Repair/Faulty Stock)</option>
                  <option value="DAMAGED">Physically Damaged</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300">Return Notes</label>
                <input
                  type="text"
                  placeholder="e.g. Subscriber disconnected service"
                  value={actionNotes}
                  onChange={(e) => setActionNotes(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="flex justify-end gap-3 border-t border-slate-800 pt-4">
                <button
                  type="button"
                  onClick={() => setReturnModalAssignment(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-rose-600 px-5 py-2 text-xs font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
                >
                  Confirm Return
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}