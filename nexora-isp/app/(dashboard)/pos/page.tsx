"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  CreditCard,
  History,
  Minus,
  Package,
  Plus,
  Printer,
  Receipt,
  RefreshCw,
  Search,
  ShoppingCart,
  Trash2,
  UserCheck,
  UserX,
  Wallet,
  X,
} from "lucide-react";

import { type InventoryItem, type InventoryItemCategory } from "@/services/inventory.service";
import {
  posService,
  type CreatePosSalePayload,
  type PosSale,
  type PosSalePaymentMethod,
} from "@/services/pos.service";
import { customersService, type CustomerListItem } from "@/services/customers.service";
import Skeleton from "@/components/ui/Skeleton";

interface CartItem {
  item: InventoryItem;
  quantity: number;
  unit_price: number;
  line_discount: number;
}

export default function PosTerminalPage() {
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [catalog, setCatalog] = useState<InventoryItem[]>([]);
  const [customers, setCustomers] = useState<CustomerListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [catalogSearch, setCatalogSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("ALL");

  // Customer Selection
  const [isWalkIn, setIsWalkIn] = useState(true);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerListItem | null>(null);
  const [customerSearch, setCustomerSearch] = useState("");
  const [walkInName, setWalkInName] = useState("");
  const [walkInPhone, setWalkInPhone] = useState("");

  // Cart & Checkout
  const [cart, setCart] = useState<CartItem[]>([]);
  const [overallDiscount, setOverallDiscount] = useState<string>("0");
  const [taxAmount, setTaxAmount] = useState<string>("0");
  const [paymentMethod, setPaymentMethod] = useState<PosSalePaymentMethod>("CASH");
  const [paymentReference, setPaymentReference] = useState("");
  const [saleNotes, setSaleNotes] = useState("");

  // Modals & States
  const [submitting, setSubmitting] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [completedSale, setCompletedSale] = useState<PosSale | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [catData, custData] = await Promise.all([
        posService.getCatalog(),
        customersService.getCustomers(),
      ]);
      setCatalog(catData || []);
      setCustomers(custData || []);
    } catch (err: any) {
      const msg = err?.message || "Failed to initialize POS terminal.";
      setNotification({ type: "error", message: msg });
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Autofocus catalog search input on mount
  useEffect(() => {
    if (!loading) {
      searchInputRef.current?.focus();
    }
  }, [loading]);

  // Filter Catalog
  const filteredCatalog = useMemo(() => {
    return catalog.filter((item) => {
      const matchCat = selectedCategory === "ALL" || item.category === selectedCategory;
      const matchSearch =
        !catalogSearch ||
        item.name.toLowerCase().includes(catalogSearch.toLowerCase()) ||
        item.code.toLowerCase().includes(catalogSearch.toLowerCase());
      return matchCat && matchSearch;
    });
  }, [catalog, selectedCategory, catalogSearch]);

  // Filter Customers
  const filteredCustomers = useMemo(() => {
    if (!customerSearch) return customers.slice(0, 8);
    return customers
      .filter(
        (c) =>
          c.full_name.toLowerCase().includes(customerSearch.toLowerCase()) ||
          c.phone.includes(customerSearch) ||
          c.customer_number.toLowerCase().includes(customerSearch.toLowerCase())
      )
      .slice(0, 8);
  }, [customers, customerSearch]);

  // Cart Actions
  const addToCart = (item: InventoryItem) => {
    const existing = cart.find((c) => c.item.id === item.id);
    const inStock = parseFloat(item.quantity_on_hand);

    if (inStock <= 0) {
      setNotification({ type: "error", message: `${item.name} is completely out of stock!` });
      return;
    }

    if (existing) {
      if (existing.quantity + 1 > inStock) {
        setNotification({ type: "error", message: `Cannot add more. Only ${inStock} available in stock.` });
        return;
      }
      setCart(
        cart.map((c) =>
          c.item.id === item.id ? { ...c, quantity: c.quantity + 1 } : c
        )
      );
    } else {
      setCart([
        ...cart,
        {
          item,
          quantity: 1,
          unit_price: parseFloat(item.unit_selling_price || "0"),
          line_discount: 0,
        },
      ]);
    }
  };

  const updateQuantity = (itemId: string, newQty: number) => {
    const target = cart.find((c) => c.item.id === itemId);
    if (!target) return;
    const inStock = parseFloat(target.item.quantity_on_hand);

    if (newQty <= 0) {
      setCart(cart.filter((c) => c.item.id !== itemId));
      return;
    }

    if (newQty > inStock) {
      setNotification({ type: "error", message: `Cannot exceed available stock of ${inStock}.` });
      return;
    }

    setCart(cart.map((c) => (c.item.id === itemId ? { ...c, quantity: newQty } : c)));
  };

  const removeFromCart = (itemId: string) => {
    setCart(cart.filter((c) => c.item.id !== itemId));
  };

  // Cart Calculations
  const cartSubtotal = useMemo(() => {
    return cart.reduce((sum, c) => sum + c.quantity * c.unit_price - c.line_discount, 0);
  }, [cart]);

  const grandTotal = useMemo(() => {
    const disc = parseFloat(overallDiscount || "0");
    const tax = parseFloat(taxAmount || "0");
    return Math.max(0, cartSubtotal - disc + tax);
  }, [cartSubtotal, overallDiscount, taxAmount]);

  // Handle Checkout
  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cart.length === 0) {
      setNotification({ type: "error", message: "Cart is empty. Select items to checkout." });
      return;
    }

    if (!isWalkIn && !selectedCustomer) {
      setNotification({ type: "error", message: "Please select a registered customer or switch to Walk-in." });
      return;
    }

    setSubmitting(true);
    try {
      const payload: CreatePosSalePayload = {
        customer_id: !isWalkIn && selectedCustomer ? selectedCustomer.id : null,
        walk_in_customer_name: isWalkIn ? walkInName || "Walk-in Customer" : "",
        walk_in_customer_phone: isWalkIn ? walkInPhone : "",
        items: cart.map((c) => ({
          item_id: c.item.id,
          quantity: c.quantity,
          unit_price: c.unit_price,
          line_discount: c.line_discount,
        })),
        payment_method: paymentMethod,
        payment_reference: paymentReference,
        discount_amount: parseFloat(overallDiscount || "0"),
        tax_amount: parseFloat(taxAmount || "0"),
        notes: saleNotes,
      };

      const sale = await posService.createSale(payload);
      setCompletedSale(sale);
      setNotification({ type: "success", message: `Sale #${sale.sale_number} completed and posted to GL!` });

      // Reset cart
      setCart([]);
      setOverallDiscount("0");
      setTaxAmount("0");
      setPaymentReference("");
      setSaleNotes("");
      setWalkInName("");
      setWalkInPhone("");
      setSelectedCustomer(null);

      // Refresh catalog stock
      const freshCatalog = await posService.getCatalog();
      setCatalog(freshCatalog || []);
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Checkout failed." });
    } finally {
      setSubmitting(false);
    }
  };

  const printReceipt = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">POS Hardware Terminal</h1>
            <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/20">
              Immediate Settlement
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Sell routers, splitters, cables, and accessories with instant stock deduction and double-entry GL ledger posting.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/pos/sales"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
          >
            <History className="h-3.5 w-3.5" />
            Sales Register & Receipts
          </Link>
          <button
            onClick={loadData}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
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

      {/* POS Grid: Catalog on Left (60%), Cart on Right (40%) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* ========================================================================= */}
        {/* LEFT COLUMN: LIVE PRODUCT CATALOG (7 Cols) */}
        {/* ========================================================================= */}
        <div className="space-y-4 lg:col-span-7">
          {/* Search & Category Filter */}
          <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search catalog by SKU code or product name..."
                value={catalogSearch}
                onChange={(e) => setCatalogSearch(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 py-2 pl-9 pr-4 text-xs text-slate-100 placeholder-slate-400 focus:border-emerald-500 focus:outline-none"
              />
            </div>

            {/* Category Chips */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {[
                { id: "ALL", label: "All Items" },
                { id: "ROUTERS_AP", label: "Routers" },
                { id: "ONU_ONT", label: "ONU / ONT" },
                { id: "CABLES_CONNECTORS", label: "Cables" },
                { id: "OPTICAL_SPLITTERS", label: "Splitters" },
                { id: "POWER_ADAPTERS", label: "Adapters" },
                { id: "ACCESSORIES", label: "Accessories" },
              ].map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition ${
                    selectedCategory === cat.id
                      ? "bg-emerald-600 text-white"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Product Cards Grid */}
          {loading ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Skeleton className="h-32 w-full rounded-xl" />
              <Skeleton className="h-32 w-full rounded-xl" />
              <Skeleton className="h-32 w-full rounded-xl" />
            </div>
          ) : filteredCatalog.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center">
              <Package className="h-10 w-10 text-slate-600 mb-2" />
              <p className="text-sm font-semibold text-slate-300">No Sellable Products Found</p>
              <p className="text-xs text-slate-500">Try changing your search or category filter.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {filteredCatalog.map((item) => {
                const inStock = parseFloat(item.quantity_on_hand);
                const isOutOfStock = inStock <= 0;
                return (
                  <div
                    key={item.id}
                    onClick={() => !isOutOfStock && addToCart(item)}
                    className={`group flex flex-col justify-between rounded-xl border p-3.5 transition ${
                      isOutOfStock
                        ? "border-slate-800/40 bg-slate-950/40 opacity-60 cursor-not-allowed"
                        : "border-slate-800 bg-slate-900/60 hover:border-emerald-500/50 hover:bg-slate-850 cursor-pointer shadow-sm hover:shadow-md"
                    }`}
                  >
                    <div>
                      <div className="flex items-start justify-between">
                        <span className="font-mono text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                          {item.code}
                        </span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-medium font-mono ${
                            isOutOfStock
                              ? "bg-rose-500/10 text-rose-400"
                              : inStock <= item.reorder_threshold
                              ? "bg-amber-500/10 text-amber-400"
                              : "bg-emerald-500/10 text-emerald-400"
                          }`}
                        >
                          {inStock} in stock
                        </span>
                      </div>
                      <h4 className="mt-2 text-xs font-semibold text-slate-100 line-clamp-2 group-hover:text-emerald-300 transition">
                        {item.name}
                      </h4>
                    </div>

                    <div className="mt-3 flex items-center justify-between border-t border-slate-800/80 pt-2.5">
                      <span className="font-mono text-xs font-bold text-slate-100">
                        PKR {parseFloat(item.unit_selling_price).toLocaleString()}
                      </span>
                      <button
                        disabled={isOutOfStock}
                        className="rounded-md bg-slate-800 p-1.5 text-slate-300 group-hover:bg-emerald-600 group-hover:text-white transition disabled:opacity-30"
                      >
                        <Plus className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ========================================================================= */}
        {/* RIGHT COLUMN: INTERACTIVE CHECKOUT & CART (5 Cols) */}
        {/* ========================================================================= */}
        <div className="space-y-4 lg:col-span-5">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
            {/* Customer Selector */}
            <div className="border-b border-slate-800 pb-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Customer Mode</span>
                <div className="flex rounded-lg bg-slate-800 p-0.5">
                  <button
                    onClick={() => setIsWalkIn(true)}
                    className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition ${
                      isWalkIn ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Walk-in
                  </button>
                  <button
                    onClick={() => setIsWalkIn(false)}
                    className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition ${
                      !isWalkIn ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Registered
                  </button>
                </div>
              </div>

              {isWalkIn ? (
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="Walk-in Name (Optional)"
                    value={walkInName}
                    onChange={(e) => setWalkInName(e.target.value)}
                    className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                  />
                  <input
                    type="text"
                    placeholder="Phone (Optional)"
                    value={walkInPhone}
                    onChange={(e) => setWalkInPhone(e.target.value)}
                    className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none font-mono"
                  />
                </div>
              ) : (
                <div className="mt-3 space-y-2">
                  {selectedCustomer ? (
                    <div className="flex items-center justify-between rounded-lg border border-emerald-500/30 bg-emerald-950/30 p-2.5">
                      <div>
                        <p className="text-xs font-bold text-emerald-300">{selectedCustomer.full_name}</p>
                        <p className="text-[11px] text-slate-400 font-mono">
                          {selectedCustomer.customer_number} • {selectedCustomer.phone}
                        </p>
                      </div>
                      <button
                        onClick={() => setSelectedCustomer(null)}
                        className="rounded p-1 text-slate-400 hover:text-slate-200"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ) : (
                    <div>
                      <input
                        type="text"
                        placeholder="Search subscriber by name, account #, or phone..."
                        value={customerSearch}
                        onChange={(e) => setCustomerSearch(e.target.value)}
                        className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                      />
                      <div className="mt-1.5 max-h-32 overflow-y-auto divide-y divide-slate-800 rounded-lg border border-slate-700 bg-slate-800/80">
                        {filteredCustomers.map((cust) => (
                          <div
                            key={cust.id}
                            onClick={() => {
                              setSelectedCustomer(cust);
                              setCustomerSearch("");
                            }}
                            className="p-2 text-xs hover:bg-slate-700 cursor-pointer flex justify-between items-center"
                          >
                            <span className="font-medium text-slate-200">{cust.full_name}</span>
                            <span className="text-[11px] font-mono text-slate-400">{cust.customer_number}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Cart Items List */}
            <div className="py-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Cart Items ({cart.length})
                </span>
                {cart.length > 0 && (
                  <button
                    onClick={() => setCart([])}
                    className="text-[11px] text-rose-400 hover:text-rose-300 transition"
                  >
                    Clear Cart
                  </button>
                )}
              </div>

              {cart.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-800 py-8 text-center">
                  <ShoppingCart className="h-8 w-8 text-slate-600 mb-2" />
                  <p className="text-xs text-slate-400">Cart is empty</p>
                  <p className="text-[11px] text-slate-500">Click products on the left to add.</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                  {cart.map((c) => (
                    <div
                      key={c.item.id}
                      className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-850 p-2.5"
                    >
                      <div className="flex-1 pr-2">
                        <p className="text-xs font-semibold text-slate-100 truncate">{c.item.name}</p>
                        <p className="text-[11px] text-slate-400 font-mono">
                          PKR {c.unit_price.toLocaleString()} each
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <div className="flex items-center rounded border border-slate-700 bg-slate-800">
                          <button
                            onClick={() => updateQuantity(c.item.id, c.quantity - 1)}
                            className="p-1 text-slate-400 hover:text-slate-200"
                          >
                            <Minus className="h-3 w-3" />
                          </button>
                          <span className="px-2 text-xs font-mono font-bold text-slate-100">{c.quantity}</span>
                          <button
                            onClick={() => updateQuantity(c.item.id, c.quantity + 1)}
                            className="p-1 text-slate-400 hover:text-slate-200"
                          >
                            <Plus className="h-3 w-3" />
                          </button>
                        </div>

                        <span className="w-20 text-right font-mono text-xs font-bold text-slate-100">
                          PKR {(c.quantity * c.unit_price).toLocaleString()}
                        </span>

                        <button
                          onClick={() => removeFromCart(c.item.id)}
                          className="text-slate-500 hover:text-rose-400"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Calculations & Payment Methods */}
            <form onSubmit={handleCheckout} className="border-t border-slate-800 pt-4 space-y-3">
              <div className="space-y-1.5 text-xs text-slate-400">
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span className="font-mono font-medium text-slate-200">
                    PKR {cartSubtotal.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-4">
                  <span>Discount (PKR)</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={overallDiscount}
                    onChange={(e) => setOverallDiscount(e.target.value)}
                    className="w-24 rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-right font-mono text-xs text-slate-100 focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div className="flex items-center justify-between gap-4">
                  <span>Tax (PKR)</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={taxAmount}
                    onChange={(e) => setTaxAmount(e.target.value)}
                    className="w-24 rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-right font-mono text-xs text-slate-100 focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div className="flex justify-between border-t border-slate-800 pt-2 text-sm font-bold text-slate-100">
                  <span>Total Due</span>
                  <span className="font-mono text-emerald-400">
                    PKR {grandTotal.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>

              {/* Payment Method Selector */}
              <div className="pt-2">
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Payment Method
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  {[
                    { id: "CASH", label: "Cash (1000)" },
                    { id: "BANK_TRANSFER", label: "Bank (1010)" },
                    { id: "MOBILE_WALLET", label: "Wallet (1020)" },
                    { id: "CARD", label: "Card" },
                  ].map((pm) => (
                    <button
                      type="button"
                      key={pm.id}
                      onClick={() => setPaymentMethod(pm.id as PosSalePaymentMethod)}
                      className={`rounded-lg border p-2 text-left text-xs font-medium transition ${
                        paymentMethod === pm.id
                          ? "border-emerald-500 bg-emerald-950/40 text-emerald-300"
                          : "border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-700"
                      }`}
                    >
                      {pm.label}
                    </button>
                  ))}
                </div>

                {paymentMethod !== "CASH" && (
                  <input
                    type="text"
                    placeholder="Bank / Transaction Reference #"
                    value={paymentReference}
                    onChange={(e) => setPaymentReference(e.target.value)}
                    className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-100 font-mono focus:border-emerald-500 focus:outline-none"
                  />
                )}
              </div>

              {/* Checkout Button */}
              <button
                type="submit"
                disabled={submitting || cart.length === 0}
                className="w-full mt-3 inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 py-3 text-xs font-bold text-white shadow-lg hover:bg-emerald-500 disabled:opacity-50 transition"
              >
                {submitting ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <CircleDollarSign className="h-4 w-4" />
                )}
                Complete Sale & Collect PKR {grandTotal.toLocaleString()}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* PRINTABLE RECEIPT MODAL */}
      {/* ========================================================================= */}
      {completedSale && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 print:p-0 print:bg-white print:static">
          <div className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl text-slate-100 print:border-0 print:shadow-none print:bg-white print:text-black print:max-w-none">
            {/* Printable Receipt Area */}
            <div id="printable-receipt" className="space-y-4">
              <div className="text-center border-b border-slate-800 pb-3 print:border-black">
                <h2 className="text-lg font-bold tracking-tight text-slate-100 print:text-black uppercase">
                  NEXORA ISP HARDWARE
                </h2>
                <p className="text-xs text-slate-400 print:text-black">Sales & Counter Receipt</p>
                <p className="font-mono text-xs text-emerald-400 print:text-black mt-1">
                  Sale #: {completedSale.sale_number}
                </p>
                <p className="text-[11px] text-slate-400 print:text-black">
                  Date: {completedSale.sale_date}
                </p>
              </div>

              <div className="text-xs space-y-1 text-slate-300 print:text-black">
                <p>
                  <span className="text-slate-500 print:text-black font-medium">Customer: </span>
                  {completedSale.customer_name}
                </p>
                {completedSale.customer_phone && (
                  <p>
                    <span className="text-slate-500 print:text-black font-medium">Phone: </span>
                    {completedSale.customer_phone}
                  </p>
                )}
                <p>
                  <span className="text-slate-500 print:text-black font-medium">Payment: </span>
                  {completedSale.payment_method}
                </p>
                {completedSale.journal_entry_number && (
                  <p className="font-mono text-[10px] text-slate-400 print:text-black">
                    GL Voucher: {completedSale.journal_entry_number}
                  </p>
                )}
              </div>

              {/* Items */}
              <div className="border-t border-b border-slate-800 py-3 print:border-black">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 print:border-black print:text-black">
                      <th className="pb-1">Item</th>
                      <th className="pb-1 text-center">Qty</th>
                      <th className="pb-1 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 print:divide-black">
                    {completedSale.items.map((line) => (
                      <tr key={line.id}>
                        <td className="py-1.5">
                          <div className="font-medium text-slate-200 print:text-black">{line.item_name}</div>
                          <div className="text-[10px] text-slate-500 print:text-black">{line.item_code}</div>
                        </td>
                        <td className="py-1.5 text-center font-mono">{parseFloat(line.quantity)}</td>
                        <td className="py-1.5 text-right font-mono">
                          PKR {parseFloat(line.line_total).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Summary */}
              <div className="space-y-1 text-xs font-mono">
                <div className="flex justify-between text-slate-400 print:text-black">
                  <span>Subtotal:</span>
                  <span>PKR {parseFloat(completedSale.subtotal_amount).toLocaleString()}</span>
                </div>
                {parseFloat(completedSale.discount_amount) > 0 && (
                  <div className="flex justify-between text-emerald-400 print:text-black">
                    <span>Discount:</span>
                    <span>-PKR {parseFloat(completedSale.discount_amount).toLocaleString()}</span>
                  </div>
                )}
                {parseFloat(completedSale.tax_amount) > 0 && (
                  <div className="flex justify-between text-slate-400 print:text-black">
                    <span>Tax:</span>
                    <span>+PKR {parseFloat(completedSale.tax_amount).toLocaleString()}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm font-bold text-slate-100 print:text-black border-t border-slate-800 pt-1.5 print:border-black">
                  <span>Total Paid:</span>
                  <span>PKR {parseFloat(completedSale.paid_amount).toLocaleString()}</span>
                </div>
              </div>

              <div className="text-center pt-2 text-[10px] text-slate-500 print:text-black">
                Thank you for your business with Nexora ISP!
              </div>
            </div>

            {/* Modal Actions (Hidden in Print) */}
            <div className="mt-6 flex gap-3 print:hidden">
              <button
                onClick={printReceipt}
                className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 text-xs font-bold text-white hover:bg-blue-500 transition"
              >
                <Printer className="h-4 w-4" />
                Print Receipt
              </button>
              <button
                onClick={() => setCompletedSale(null)}
                className="flex-1 rounded-xl border border-slate-700 bg-slate-800 py-2.5 text-xs font-bold text-slate-300 hover:bg-slate-700 transition"
              >
                New Sale
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
