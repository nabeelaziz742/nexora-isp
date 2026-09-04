"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  CircleDollarSign,
  Filter,
  History,
  Printer,
  Receipt,
  RefreshCw,
  RotateCcw,
  Search,
  ShoppingCart,
  X,
} from "lucide-react";

import {
  posService,
  type PosSale,
  type PosSalePaymentMethod,
  type PosSaleStatus,
} from "@/services/pos.service";
import Skeleton from "@/components/ui/Skeleton";

function formatDate(value: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-PK", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function PosSalesRegisterPage() {
  const [sales, setSales] = useState<PosSale[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [paymentMethodFilter, setPaymentMethodFilter] = useState<string>("ALL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  // Modals
  const [selectedReceiptSale, setSelectedReceiptSale] = useState<PosSale | null>(null);
  const [cancelModalSale, setCancelModalSale] = useState<PosSale | null>(null);
  const [cancellationReason, setCancellationReason] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const loadSales = async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    setRefreshing(true);
    try {
      const res = await posService.getSales({
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        payment_method: paymentMethodFilter !== "ALL" ? paymentMethodFilter : undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        search: searchQuery || undefined,
      });
      setSales(res.results || []);
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Failed to load sales register." });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadSales();
  }, [statusFilter, paymentMethodFilter]);

  // Metrics
  const metrics = useMemo(() => {
    const completed = sales.filter((s) => s.status === "COMPLETED");
    const totalVolume = completed.reduce((sum, s) => sum + parseFloat(s.total_amount || "0"), 0);
    const count = completed.length;
    const cancelledCount = sales.filter((s) => s.status === "CANCELLED").length;
    return { totalVolume, count, cancelledCount };
  }, [sales]);

  const handleCancelSale = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cancelModalSale || !cancellationReason.trim()) return;

    setCancelling(true);
    try {
      await posService.cancelSale(cancelModalSale.id, cancellationReason);
      setNotification({
        type: "success",
        message: `Sale #${cancelModalSale.sale_number} cancelled. Stock restored and GL reversal posted.`,
      });
      setCancelModalSale(null);
      setCancellationReason("");
      loadSales(false);
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Failed to cancel sale." });
    } finally {
      setCancelling(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Link
              href="/pos"
              className="inline-flex items-center gap-1 text-xs font-semibold text-slate-400 hover:text-slate-200 transition mr-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Terminal
            </Link>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">POS Sales Register</h1>
            <span className="inline-flex items-center rounded-md bg-blue-500/10 px-2 py-0.5 text-xs font-medium text-blue-400 border border-blue-500/20">
              Audit Trail
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Historical register of all POS transactions, counter receipts, GL vouchers, and stock reversal cancellations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadSales(false)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>

          <Link
            href="/pos"
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-500 transition"
          >
            <ShoppingCart className="h-4 w-4" />
            Open Terminal
          </Link>
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

      {/* Metrics Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Net Sales</span>
            <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-400">
              <CircleDollarSign className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-100 font-mono">
            PKR {metrics.totalVolume.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
          </p>
          <p className="mt-1 text-xs text-slate-500">Collected and posted to GL revenue</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Completed Sales</span>
            <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
              <Receipt className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-100">{metrics.count}</p>
          <p className="mt-1 text-xs text-slate-500">Successful counter checkout receipts</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Cancelled Sales</span>
            <div className="rounded-lg bg-rose-500/10 p-2 text-rose-400">
              <RotateCcw className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-2xl font-bold text-rose-400">{metrics.cancelledCount}</p>
          <p className="mt-1 text-xs text-slate-500">Stock restored & GL reversed</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by sale #, customer name, phone, or reference..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadSales(false)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 py-2 pl-9 pr-4 text-xs text-slate-100 placeholder-slate-400 focus:border-emerald-500 focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>

          <select
            value={paymentMethodFilter}
            onChange={(e) => setPaymentMethodFilter(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none"
          >
            <option value="ALL">All Payment Methods</option>
            <option value="CASH">Cash</option>
            <option value="BANK_TRANSFER">Bank Transfer</option>
            <option value="MOBILE_WALLET">Mobile Wallet</option>
            <option value="CARD">Card</option>
          </select>
        </div>
      </div>

      {/* Sales Table */}
      <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm">
        {loading ? (
          <div className="p-8 space-y-4">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : sales.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-center">
            <Receipt className="h-12 w-12 text-slate-600 mb-3" />
            <h3 className="text-base font-semibold text-slate-300">No Sales Recorded</h3>
            <p className="mt-1 text-xs text-slate-500 max-w-sm">
              Use the POS Terminal to make hardware sales. All counter transactions will appear here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="border-b border-slate-800 bg-slate-950/60 font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-4 py-3.5">Sale #</th>
                  <th className="px-4 py-3.5">Date</th>
                  <th className="px-4 py-3.5">Customer</th>
                  <th className="px-4 py-3.5">Payment</th>
                  <th className="px-4 py-3.5 text-center">Items</th>
                  <th className="px-4 py-3.5 text-right">Total (PKR)</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">GL Entry</th>
                  <th className="px-4 py-3.5 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {sales.map((sale) => (
                  <tr key={sale.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3.5 font-mono font-bold text-slate-100">{sale.sale_number}</td>
                    <td className="px-4 py-3.5 text-slate-400">{sale.sale_date}</td>
                    <td className="px-4 py-3.5">
                      <div className="font-medium text-slate-200">{sale.customer_name}</div>
                      {sale.customer_phone && (
                        <div className="text-[11px] text-slate-500 font-mono">{sale.customer_phone}</div>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="font-medium text-slate-300">{sale.payment_method}</span>
                      {sale.payment_reference && (
                        <div className="text-[10px] text-slate-500 font-mono truncate max-w-[120px]">
                          Ref: {sale.payment_reference}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-center font-mono text-slate-200">
                      {sale.items?.length || 0}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono font-bold text-slate-100">
                      {parseFloat(sale.total_amount).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3.5">
                      <span
                        className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold border ${
                          sale.status === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                        }`}
                      >
                        {sale.status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      {sale.journal_entry_number ? (
                        <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-mono text-emerald-400 border border-emerald-500/20">
                          {sale.journal_entry_number}
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          onClick={() => setSelectedReceiptSale(sale)}
                          className="inline-flex items-center gap-1 rounded bg-slate-800 px-2 py-1 text-[11px] font-semibold text-slate-300 hover:bg-slate-700 border border-slate-700"
                        >
                          <Printer className="h-3 w-3" />
                          Receipt
                        </button>
                        {sale.status === "COMPLETED" && (
                          <button
                            onClick={() => {
                              setCancelModalSale(sale);
                              setCancellationReason("");
                            }}
                            className="inline-flex items-center gap-1 rounded bg-rose-500/10 px-2 py-1 text-[11px] font-semibold text-rose-400 hover:bg-rose-500/20 border border-rose-500/20"
                          >
                            <RotateCcw className="h-3 w-3" />
                            Void
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

      {/* ========================================================================= */}
      {/* REPRINT RECEIPT MODAL */}
      {/* ========================================================================= */}
      {selectedReceiptSale && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 print:p-0 print:bg-white print:static">
          <div className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl text-slate-100 print:border-0 print:shadow-none print:bg-white print:text-black print:max-w-none">
            <div id="reprint-receipt" className="space-y-4">
              <div className="text-center border-b border-slate-800 pb-3 print:border-black">
                <h2 className="text-lg font-bold uppercase tracking-tight text-slate-100 print:text-black">
                  NEXORA ISP HARDWARE
                </h2>
                <p className="text-xs text-slate-400 print:text-black">Sales Receipt (Duplicate)</p>
                <p className="font-mono text-xs text-emerald-400 print:text-black mt-1">
                  Sale #: {selectedReceiptSale.sale_number}
                </p>
                <p className="text-[11px] text-slate-400 print:text-black">
                  Date: {selectedReceiptSale.sale_date}
                </p>
              </div>

              <div className="text-xs space-y-1 text-slate-300 print:text-black">
                <p>
                  <span className="text-slate-500 print:text-black font-medium">Customer: </span>
                  {selectedReceiptSale.customer_name}
                </p>
                {selectedReceiptSale.customer_phone && (
                  <p>
                    <span className="text-slate-500 print:text-black font-medium">Phone: </span>
                    {selectedReceiptSale.customer_phone}
                  </p>
                )}
                <p>
                  <span className="text-slate-500 print:text-black font-medium">Payment: </span>
                  {selectedReceiptSale.payment_method}
                </p>
                {selectedReceiptSale.journal_entry_number && (
                  <p className="font-mono text-[10px] text-slate-400 print:text-black">
                    GL Voucher: {selectedReceiptSale.journal_entry_number}
                  </p>
                )}
                {selectedReceiptSale.status === "CANCELLED" && (
                  <div className="rounded bg-rose-500/20 p-2 text-rose-300 print:text-black border border-rose-500/40 text-center font-bold">
                    VOID / CANCELLED: {selectedReceiptSale.cancellation_reason}
                  </div>
                )}
              </div>

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
                    {selectedReceiptSale.items.map((line) => (
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

              <div className="space-y-1 text-xs font-mono">
                <div className="flex justify-between text-slate-400 print:text-black">
                  <span>Subtotal:</span>
                  <span>PKR {parseFloat(selectedReceiptSale.subtotal_amount).toLocaleString()}</span>
                </div>
                {parseFloat(selectedReceiptSale.discount_amount) > 0 && (
                  <div className="flex justify-between text-emerald-400 print:text-black">
                    <span>Discount:</span>
                    <span>-PKR {parseFloat(selectedReceiptSale.discount_amount).toLocaleString()}</span>
                  </div>
                )}
                {parseFloat(selectedReceiptSale.tax_amount) > 0 && (
                  <div className="flex justify-between text-slate-400 print:text-black">
                    <span>Tax:</span>
                    <span>+PKR {parseFloat(selectedReceiptSale.tax_amount).toLocaleString()}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm font-bold text-slate-100 print:text-black border-t border-slate-800 pt-1.5 print:border-black">
                  <span>Total Paid:</span>
                  <span>PKR {parseFloat(selectedReceiptSale.paid_amount).toLocaleString()}</span>
                </div>
              </div>
            </div>

            <div className="mt-6 flex gap-3 print:hidden">
              <button
                onClick={() => window.print()}
                className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 text-xs font-bold text-white hover:bg-blue-500 transition"
              >
                <Printer className="h-4 w-4" />
                Print Receipt
              </button>
              <button
                onClick={() => setSelectedReceiptSale(null)}
                className="flex-1 rounded-xl border border-slate-700 bg-slate-800 py-2.5 text-xs font-bold text-slate-300 hover:bg-slate-700 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* CANCEL / VOID SALE MODAL */}
      {/* ========================================================================= */}
      {cancelModalSale && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2">
                <RotateCcw className="h-5 w-5 text-rose-400" />
                <h3 className="text-base font-semibold text-slate-100">
                  Void POS Sale #{cancelModalSale.sale_number}
                </h3>
              </div>
              <button onClick={() => setCancelModalSale(null)} className="text-slate-400 hover:text-slate-200">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCancelSale} className="mt-5 space-y-4">
              <div className="rounded-lg bg-rose-500/10 p-3 border border-rose-500/20 text-xs text-rose-300">
                <p className="font-semibold">Important Financial Action:</p>
                <p className="mt-1">
                  Cancelling this sale will automatically restore all deducted stock to warehouse inventory and post a
                  full reversal entry in the General Ledger.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">Cancellation Reason *</label>
                <textarea
                  rows={3}
                  required
                  placeholder="e.g. Customer returned items / Transaction entered in error..."
                  value={cancellationReason}
                  onChange={(e) => setCancellationReason(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-rose-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 border-t border-slate-800 pt-4">
                <button
                  type="button"
                  onClick={() => setCancelModalSale(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Keep Sale
                </button>
                <button
                  type="submit"
                  disabled={cancelling || !cancellationReason.trim()}
                  className="inline-flex items-center gap-2 rounded-lg bg-rose-600 px-5 py-2 text-xs font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
                >
                  {cancelling && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                  Confirm Void & Reversal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
