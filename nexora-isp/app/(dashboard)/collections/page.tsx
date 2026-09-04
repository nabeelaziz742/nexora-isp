"use client";

import {
  AlertTriangle,
  Banknote,
  CheckCircle2,
  CircleDollarSign,
  CreditCard,
  Eye,
  Filter,
  Loader2,
  Plus,
  Printer,
  Receipt,
  RefreshCw,
  RotateCcw,
  Search,
  WalletCards,
  X,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { billingService } from "@/services/billing.service";
import {
  customersService,
  type CustomerDetail,
  type CustomerListItem,
} from "@/services/customers.service";

import type {
  Invoice,
  Payment,
  PaymentMethod,
  PaymentReceipt,
} from "@/types/billing";

const paymentMethods: { value: PaymentMethod; label: string }[] = [
  { value: "CASH", label: "Cash" },
  { value: "BANK_TRANSFER", label: "Bank Transfer" },
  { value: "CARD", label: "Debit / Credit Card" },
  { value: "MOBILE_WALLET", label: "Mobile Wallet" },
  { value: "OTHER", label: "Other" },
];

function formatMoney(amount: string | number, currency: string = "PKR"): string {
  const value = Number(amount || 0);
  return `${currency} ${value.toLocaleString("en-PK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatDate(value: string | undefined): string {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("en-PK", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export default function CollectionsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  // Filters
  const [search, setSearch] = useState("");
  const [methodFilter, setMethodFilter] = useState<PaymentMethod | "">("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "ACTIVE" | "REVERSED">("ALL");

  // Receipt Modal
  const [selectedReceipt, setSelectedReceipt] = useState<PaymentReceipt | null>(null);
  const [receiptLoading, setReceiptLoading] = useState(false);
  const [isReceiptModalOpen, setIsReceiptModalOpen] = useState(false);

  // Reversal Modal
  const [reversalTarget, setReversalTarget] = useState<Payment | null>(null);
  const [reversalReason, setReversalReason] = useState("");
  const [reversalReference, setReversalReference] = useState("");
  const [submittingReversal, setSubmittingReversal] = useState(false);

  // New Payment Collection Modal
  const [isNewCollectionOpen, setIsNewCollectionOpen] = useState(false);
  const [customersList, setCustomersList] = useState<CustomerListItem[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [selectedCustomerDetail, setSelectedCustomerDetail] = useState<CustomerDetail | null>(null);
  const [selectedServiceId, setSelectedServiceId] = useState("");
  const [customerUnpaidInvoices, setCustomerUnpaidInvoices] = useState<Invoice[]>([]);
  const [invoicesLoading, setInvoicesLoading] = useState(false);
  const [collectAmount, setCollectAmount] = useState("");
  const [collectMethod, setCollectMethod] = useState<PaymentMethod>("CASH");
  const [collectReference, setCollectReference] = useState("");
  const [collectNotes, setCollectNotes] = useState("");
  const [submittingCollection, setSubmittingCollection] = useState(false);

  // Load Payments
  const loadPayments = useCallback(async () => {
    try {
      setError("");
      const res = await billingService.getPayments({
        payment_method: methodFilter,
        search: search.trim() || undefined,
      });
      setPayments(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load collections.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [methodFilter, search]);

  useEffect(() => {
    void loadPayments();
  }, [loadPayments]);

  const filteredPayments = useMemo(() => {
    return payments.filter((p) => {
      if (statusFilter === "ACTIVE") return !p.is_reversed;
      if (statusFilter === "REVERSED") return p.is_reversed;
      return true;
    });
  }, [payments, statusFilter]);

  const totalCollectedActive = useMemo(() => {
    return payments
      .filter((p) => !p.is_reversed)
      .reduce((sum, p) => sum + Number(p.amount || 0), 0);
  }, [payments]);

  const totalReversed = useMemo(() => {
    return payments
      .filter((p) => p.is_reversed)
      .reduce((sum, p) => sum + Number(p.amount || 0), 0);
  }, [payments]);

  // Open Receipt
  const handleViewReceipt = async (paymentId: string) => {
    try {
      setReceiptLoading(true);
      setIsReceiptModalOpen(true);
      const receipt = await billingService.getReceipt(paymentId);
      setSelectedReceipt(receipt);
    } catch (err) {
      toast.error("Failed to load payment receipt.");
      setIsReceiptModalOpen(false);
    } finally {
      setReceiptLoading(false);
    }
  };

  // Reverse Payment
  const handleConfirmReversal = async (e: FormEvent) => {
    e.preventDefault();
    if (!reversalTarget) return;
    if (!reversalReason.trim()) {
      toast.error("Please provide a reversal reason.");
      return;
    }

    try {
      setSubmittingReversal(true);
      await billingService.reversePayment(reversalTarget.id, {
        reversal_reason: reversalReason.trim(),
        reversal_reference: reversalReference.trim(),
      });
      toast.success(`Payment ${reversalTarget.payment_number} reversed.`);
      setReversalTarget(null);
      setReversalReason("");
      setReversalReference("");
      await loadPayments();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to reverse payment.");
    } finally {
      setSubmittingReversal(false);
    }
  };

  // Open New Collection Modal
  const handleOpenNewCollection = async () => {
    setIsNewCollectionOpen(true);
    if (customersList.length === 0) {
      try {
        const res = await customersService.getCustomers();
        setCustomersList(res);
      } catch (err) {
        toast.error("Failed to load customers.");
      }
    }
  };

  // When customer changes, load their unpaid invoices
  const handleCustomerChange = async (customerId: string) => {
    setSelectedCustomerId(customerId);
    setCustomerUnpaidInvoices([]);
    if (!customerId) {
      setSelectedCustomerDetail(null);
      setSelectedServiceId("");
      return;
    }

    try {
      const detail = await customersService.getCustomer(customerId);
      setSelectedCustomerDetail(detail);
      if (detail && detail.service_accounts && detail.service_accounts.length > 0) {
        const svcId = detail.service_accounts[0].id;
        setSelectedServiceId(svcId);
        setInvoicesLoading(true);
        const [unpaidInvs, partialInvs] = await Promise.all([
          billingService.getInvoices({
            service_account_id: svcId,
            status: "UNPAID",
          }),
          billingService.getInvoices({
            service_account_id: svcId,
            status: "PARTIALLY_PAID",
          }),
        ]);
        const combined = [...unpaidInvs, ...partialInvs];
        setCustomerUnpaidInvoices(combined);
        const totalOutstanding = combined.reduce(
          (sum, i) => sum + Number(i.outstanding_amount || 0),
          0,
        );
        setCollectAmount(totalOutstanding > 0 ? String(totalOutstanding) : "");
      } else {
        setSelectedServiceId("");
      }
    } catch {
      setSelectedCustomerDetail(null);
      setSelectedServiceId("");
    } finally {
      setInvoicesLoading(false);
    }
  };

  const handleRecordCollection = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedServiceId) {
      toast.error("Please select a service connection.");
      return;
    }
    if (!collectAmount || Number(collectAmount) <= 0) {
      toast.error("Please enter a valid payment amount.");
      return;
    }

    try {
      setSubmittingCollection(true);
      await billingService.recordPaymentWithAllocations({
        service_account_id: selectedServiceId,
        amount: collectAmount,
        payment_method: collectMethod,
        reference: collectReference.trim(),
        notes: collectNotes.trim(),
      });
      toast.success("Payment recorded and allocated successfully.");
      setIsNewCollectionOpen(false);
      setSelectedCustomerId("");
      setSelectedServiceId("");
      setCollectAmount("");
      setCollectReference("");
      setCollectNotes("");
      await loadPayments();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to record collection.");
    } finally {
      setSubmittingCollection(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-[var(--border)] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-emerald-400">
              <CircleDollarSign className="size-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                Collections & Receipts
              </h1>
              <p className="text-xs text-[var(--text-muted)]">
                Authoritative payment register, instant receipts, bank transfers, mobile wallets, and reversals.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={() => {
              setRefreshing(true);
              void loadPayments();
            }}
            disabled={refreshing}
            className="flex h-9 items-center gap-1.5 border border-[var(--border)] bg-[var(--surface)] px-3 text-xs font-semibold text-[var(--text-muted)] hover:bg-white/[0.04] hover:text-white"
          >
            <RefreshCw className={`size-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>

          <button
            type="button"
            onClick={() => void handleOpenNewCollection()}
            className="flex h-9 items-center gap-1.5 bg-emerald-600 px-3.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-500"
          >
            <Plus className="size-3.5" />
            Collect Payment
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
            Total Active Collections
          </span>
          <p className="mt-1 font-mono text-lg font-bold text-emerald-400">
            {formatMoney(totalCollectedActive)}
          </p>
          <span className="text-[10px] text-[var(--text-muted)]">
            {payments.filter((p) => !p.is_reversed).length} recorded payments
          </span>
        </div>

        <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-rose-400">
            Total Reversals
          </span>
          <p className="mt-1 font-mono text-lg font-bold text-rose-400">
            {formatMoney(totalReversed)}
          </p>
          <span className="text-[10px] text-rose-500/80">
            {payments.filter((p) => p.is_reversed).length} reversed transactions
          </span>
        </div>

        <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-blue-400">
            Cash Collections
          </span>
          <p className="mt-1 font-mono text-lg font-bold text-blue-400">
            {formatMoney(
              payments
                .filter((p) => !p.is_reversed && p.payment_method === "CASH")
                .reduce((s, p) => s + Number(p.amount || 0), 0)
            )}
          </p>
          <span className="text-[10px] text-[var(--text-muted)]">Counter & field collections</span>
        </div>

        <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-purple-400">
            Digital & Bank Transfers
          </span>
          <p className="mt-1 font-mono text-lg font-bold text-purple-400">
            {formatMoney(
              payments
                .filter((p) => !p.is_reversed && p.payment_method !== "CASH")
                .reduce((s, p) => s + Number(p.amount || 0), 0)
            )}
          </p>
          <span className="text-[10px] text-[var(--text-muted)]">Bank / JazzCash / EasyPaisa</span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="border border-[var(--border)] bg-[var(--surface)] p-4 space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              type="text"
              placeholder="Search receipt #, subscriber, ref #..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9 w-full border border-[var(--border)] bg-[var(--background)] pl-9 pr-3 text-xs text-white placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <select
              value={methodFilter}
              onChange={(e) => setMethodFilter(e.target.value as PaymentMethod | "")}
              className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="">All Payment Methods</option>
              {paymentMethods.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as "ALL" | "ACTIVE" | "REVERSED")}
              className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="ALL">All Payments</option>
              <option value="ACTIVE">Active Receipts Only</option>
              <option value="REVERSED">Reversed Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Payments List Table */}
      <div className="border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="size-6 animate-spin text-emerald-500" />
          </div>
        ) : error ? (
          <div className="p-8 text-center">
            <AlertTriangle className="mx-auto size-8 text-rose-400" />
            <p className="mt-2 text-sm text-rose-400">{error}</p>
          </div>
        ) : filteredPayments.length === 0 ? (
          <div className="p-12 text-center">
            <Receipt className="mx-auto size-10 text-[var(--text-muted)] opacity-40" />
            <h3 className="mt-3 text-sm font-semibold text-white">No Collections Found</h3>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              No payment transactions match your query.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-[var(--border)] bg-white/[0.02] text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  <th className="px-4 py-3">Receipt / Trx #</th>
                  <th className="px-4 py-3">Subscriber & Service</th>
                  <th className="px-4 py-3">Date & Time</th>
                  <th className="px-4 py-3">Method</th>
                  <th className="px-4 py-3">Reference</th>
                  <th className="px-4 py-3 text-right">Amount (PKR)</th>
                  <th className="px-4 py-3">Collected By</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {filteredPayments.map((pay) => {
                  return (
                    <tr
                      key={pay.id}
                      className={`transition-colors hover:bg-white/[0.02] ${
                        pay.is_reversed ? "opacity-60 bg-rose-500/[0.02]" : ""
                      }`}
                    >
                      <td className="px-4 py-3 font-mono font-bold text-emerald-400">
                        {pay.payment_number}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/customers/${pay.customer_id}`}
                          className="font-semibold text-white hover:text-emerald-400 hover:underline"
                        >
                          {pay.customer_name}
                        </Link>
                        <div className="font-mono text-[10px] text-[var(--text-muted)]">
                          {pay.service_number}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-zinc-300">
                        {formatDate(pay.paid_at)}
                      </td>
                      <td className="px-4 py-3">
                        <span className="border border-[var(--border)] bg-[var(--background)] px-2 py-0.5 text-[10px] font-semibold text-zinc-300">
                          {pay.payment_method}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-[var(--text-muted)]">
                        {pay.reference || "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-bold text-white">
                        {pay.is_reversed ? (
                          <span className="line-through text-rose-400">{formatMoney(pay.amount)}</span>
                        ) : (
                          formatMoney(pay.amount)
                        )}
                      </td>
                      <td className="px-4 py-3 text-[var(--text-muted)]">
                        {pay.received_by_email || "System"}
                      </td>
                      <td className="px-4 py-3">
                        {pay.is_reversed ? (
                          <span className="border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-[9px] font-bold uppercase text-rose-400">
                            Reversed
                          </span>
                        ) : (
                          <span className="border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold uppercase text-emerald-400">
                            Active
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => void handleViewReceipt(pay.id)}
                            className="flex h-7 items-center gap-1 border border-[var(--border)] bg-[var(--background)] px-2 text-[10px] font-semibold text-emerald-400 hover:text-emerald-300"
                            title="View Printable Receipt"
                          >
                            <Receipt className="size-3" />
                            Receipt
                          </button>

                          {!pay.is_reversed && (
                            <button
                              type="button"
                              onClick={() => setReversalTarget(pay)}
                              className="flex h-7 items-center gap-1 border border-rose-500/30 bg-rose-500/10 px-2 text-[10px] font-semibold text-rose-400 hover:bg-rose-500/20"
                              title="Reverse Payment"
                            >
                              <RotateCcw className="size-3" />
                              Reverse
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Printable Receipt Modal */}
      {isReceiptModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-lg border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl">
            <button
              type="button"
              onClick={() => setIsReceiptModalOpen(false)}
              className="absolute right-4 top-4 text-[var(--text-muted)] hover:text-white"
            >
              <X className="size-4" />
            </button>

            {receiptLoading || !selectedReceipt ? (
              <div className="flex h-64 items-center justify-center">
                <Loader2 className="size-6 animate-spin text-emerald-500" />
              </div>
            ) : (
              <div className="space-y-5" id="printable-receipt">
                {/* Receipt Header */}
                <div className="border-b border-[var(--border)] pb-4 text-center">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">
                    Official Payment Receipt
                  </span>
                  <h2 className="mt-0.5 text-lg font-bold text-white">
                    {selectedReceipt.organization_name}
                  </h2>
                  <p className="font-mono text-xs text-[var(--text-muted)]">
                    Receipt #: {selectedReceipt.payment_number}
                  </p>
                </div>

                {/* Status Alert if Reversed */}
                {selectedReceipt.is_reversed && (
                  <div className="border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
                    <p className="font-bold uppercase">Transaction Reversed</p>
                    <p className="mt-0.5 text-[11px]">Reason: {selectedReceipt.reversal_reason || "Voided entry"}</p>
                  </div>
                )}

                {/* Subscriber Details Grid */}
                <div className="grid grid-cols-2 gap-3 border border-[var(--border)] bg-[var(--background)] p-3 text-xs">
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Subscriber</span>
                    <p className="font-semibold text-white">{selectedReceipt.customer.full_name}</p>
                    <p className="text-[10px] text-[var(--text-muted)]">{selectedReceipt.customer.customer_number}</p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Service Account</span>
                    <p className="font-mono font-semibold text-white">{selectedReceipt.service_number}</p>
                    <p className="text-[10px] text-[var(--text-muted)]">{selectedReceipt.customer.phone}</p>
                  </div>
                  <div className="col-span-2 border-t border-[var(--border)] pt-2">
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Address</span>
                    <p className="text-[11px] text-zinc-300">
                      {selectedReceipt.customer.address}, {selectedReceipt.customer.city}
                    </p>
                  </div>
                </div>

                {/* Amount Paid Box */}
                <div className="flex items-center justify-between border-2 border-emerald-500/30 bg-emerald-500/10 p-4">
                  <div>
                    <span className="text-[10px] font-bold uppercase text-emerald-300">Amount Received</span>
                    <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                      Method: {selectedReceipt.payment_method} {selectedReceipt.reference ? `(Ref: ${selectedReceipt.reference})` : ""}
                    </p>
                  </div>
                  <p className="font-mono text-2xl font-bold text-emerald-400">
                    {formatMoney(selectedReceipt.amount, selectedReceipt.currency)}
                  </p>
                </div>

                {/* Allocations Breakdown */}
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                    Invoices Paid by this Transaction
                  </span>
                  <div className="mt-1.5 border border-[var(--border)] overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-[var(--border)] bg-white/[0.02] text-[10px] text-[var(--text-muted)]">
                          <th className="p-2">Invoice #</th>
                          <th className="p-2">Period</th>
                          <th className="p-2 text-right">Applied Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border)]">
                        {selectedReceipt.allocations.map((alloc, idx) => (
                          <tr key={idx}>
                            <td className="p-2 font-mono font-semibold text-blue-400">{alloc.invoice_number}</td>
                            <td className="p-2 text-[10px] text-zinc-300">{alloc.billing_period}</td>
                            <td className="p-2 text-right font-mono font-bold text-emerald-400">{formatMoney(alloc.allocated_amount)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Remaining Balance Summary */}
                <div className="flex justify-between border-t border-[var(--border)] pt-3 text-xs">
                  <span className="text-[var(--text-muted)]">Subscriber Remaining Balance:</span>
                  <span className="font-mono font-bold text-amber-400">
                    {formatMoney(selectedReceipt.customer_remaining_balance, selectedReceipt.currency)}
                  </span>
                </div>

                {/* Footer and Print Button */}
                <div className="flex items-center justify-between pt-2 border-t border-[var(--border)]">
                  <span className="text-[10px] text-[var(--text-muted)]">
                    Date: {formatDate(selectedReceipt.payment_date)} • Officer: {selectedReceipt.received_by_name}
                  </span>
                  <button
                    type="button"
                    onClick={() => window.print()}
                    className="flex h-8 items-center gap-1.5 bg-emerald-600 px-3 text-xs font-semibold text-white hover:bg-emerald-500"
                  >
                    <Printer className="size-3.5" />
                    Print Receipt
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Payment Reversal Modal */}
      {reversalTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="size-5 text-rose-400" />
                <h3 className="text-base font-bold text-white">Reverse Payment Receipt</h3>
              </div>
              <button
                type="button"
                onClick={() => setReversalTarget(null)}
                className="text-[var(--text-muted)] hover:text-white"
              >
                <X className="size-4" />
              </button>
            </div>

            <form onSubmit={handleConfirmReversal} className="mt-4 space-y-4">
              <div className="border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-300">
                <p className="font-semibold">Reversal Effect:</p>
                <p className="mt-0.5 text-[11px] text-rose-200/80">
                  All invoice balances covered by payment <strong className="font-mono">{reversalTarget.payment_number}</strong> (PKR {reversalTarget.amount}) will be restored to UNPAID.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-white">Reversal Reason *</label>
                <textarea
                  rows={3}
                  required
                  value={reversalReason}
                  onChange={(e) => setReversalReason(e.target.value)}
                  placeholder="e.g. Bounced cheque, wrong amount recorded by collector, bank chargeback..."
                  className="mt-1 w-full border border-[var(--border)] bg-[var(--background)] p-2 text-xs text-white focus:border-rose-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-white">Reversal Reference</label>
                <input
                  type="text"
                  value={reversalReference}
                  onChange={(e) => setReversalReference(e.target.value)}
                  placeholder="Optional reversal tracking #"
                  className="mt-1 h-8 w-full border border-[var(--border)] bg-[var(--background)] px-2.5 text-xs text-white focus:border-rose-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setReversalTarget(null)}
                  className="h-9 px-4 text-xs font-semibold text-[var(--text-muted)] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingReversal}
                  className="flex h-9 items-center gap-1.5 bg-rose-600 px-4 text-xs font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
                >
                  {submittingReversal && <Loader2 className="size-3.5 animate-spin" />}
                  Confirm Reversal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Payment Collection Modal */}
      {isNewCollectionOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="h-full max-h-[90vh] w-full max-w-lg overflow-y-auto border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
              <div>
                <h3 className="text-base font-bold text-white">Collect Subscriber Payment</h3>
                <p className="text-xs text-[var(--text-muted)]">
                  Record collection with automatic FIFO allocation across unpaid invoices.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsNewCollectionOpen(false)}
                className="text-[var(--text-muted)] hover:text-white"
              >
                <X className="size-4" />
              </button>
            </div>

            <form onSubmit={handleRecordCollection} className="mt-4 space-y-4">
              {/* Select Customer */}
              <div>
                <label className="block text-xs font-semibold text-white">Select Subscriber *</label>
                <select
                  required
                  value={selectedCustomerId}
                  onChange={(e) => void handleCustomerChange(e.target.value)}
                  className="mt-1 h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
                >
                  <option value="">Select customer...</option>
                  {customersList.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.full_name} ({c.customer_number}) - {c.phone}
                    </option>
                  ))}
                </select>
              </div>

              {/* Select Service */}
              {selectedCustomerDetail && selectedCustomerDetail.service_accounts.length > 0 && (
                <div>
                  <label className="block text-xs font-semibold text-white">Select Service Connection *</label>
                  <select
                    required
                    value={selectedServiceId}
                    onChange={(e) => setSelectedServiceId(e.target.value)}
                    className="mt-1 h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
                  >
                    {selectedCustomerDetail.service_accounts.map((svc) => (
                      <option key={svc.id} value={svc.id}>
                        {svc.service_number} ({svc.internet_package.name})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Unpaid Invoices Summary */}
              {selectedCustomerId && (
                <div className="border border-[var(--border)] bg-[var(--background)] p-3">
                  <span className="text-[10px] font-bold uppercase text-[var(--text-muted)]">
                    Pending Invoices for this Account
                  </span>
                  {invoicesLoading ? (
                    <div className="flex justify-center p-3">
                      <Loader2 className="size-4 animate-spin text-blue-500" />
                    </div>
                  ) : customerUnpaidInvoices.length === 0 ? (
                    <p className="mt-1 text-xs text-emerald-400">
                      ✓ No outstanding unpaid invoices for this subscriber.
                    </p>
                  ) : (
                    <div className="mt-2 space-y-1.5 max-h-36 overflow-y-auto">
                      {customerUnpaidInvoices.map((inv) => (
                        <div key={inv.id} className="flex items-center justify-between text-xs border-b border-[var(--border)]/50 pb-1">
                          <span className="font-mono text-blue-400">{inv.invoice_number}</span>
                          <span className="text-zinc-400">{formatDate(inv.due_date)}</span>
                          <span className="font-mono font-bold text-amber-400">{formatMoney(inv.outstanding_amount)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Amount */}
              <div>
                <label className="block text-xs font-semibold text-white">Collected Amount (PKR) *</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={collectAmount}
                  onChange={(e) => setCollectAmount(e.target.value)}
                  className="mt-1 h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 font-mono text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              {/* Method */}
              <div>
                <label className="block text-xs font-semibold text-white">Payment Method *</label>
                <select
                  value={collectMethod}
                  onChange={(e) => setCollectMethod(e.target.value as PaymentMethod)}
                  className="mt-1 h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
                >
                  {paymentMethods.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </div>

              {/* Reference */}
              <div>
                <label className="block text-xs font-semibold text-white">Reference / Transaction ID</label>
                <input
                  type="text"
                  value={collectReference}
                  onChange={(e) => setCollectReference(e.target.value)}
                  placeholder="e.g. Bank slip #, JazzCash TID"
                  className="mt-1 h-8 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
                />
              </div>

              {/* Notes */}
              <div>
                <label className="block text-xs font-semibold text-white">Notes</label>
                <textarea
                  rows={2}
                  value={collectNotes}
                  onChange={(e) => setCollectNotes(e.target.value)}
                  placeholder="Optional collection notes"
                  className="mt-1 w-full border border-[var(--border)] bg-[var(--background)] p-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsNewCollectionOpen(false)}
                  className="h-9 px-4 text-xs font-semibold text-[var(--text-muted)] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingCollection}
                  className="flex h-9 items-center gap-1.5 bg-emerald-600 px-4 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {submittingCollection && <Loader2 className="size-3.5 animate-spin" />}
                  Record Collection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
