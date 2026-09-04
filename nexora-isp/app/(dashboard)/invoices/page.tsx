"use client";

import {
  AlertCircle,
  AlertTriangle,
  Banknote,
  CheckCircle2,
  ChevronRight,
  CreditCard,
  Download,
  Eye,
  FileSpreadsheet,
  Filter,
  Loader2,
  Plus,
  Printer,
  Receipt,
  RefreshCw,
  Search,
  Trash2,
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
  type CustomerServiceAccount,
} from "@/services/customers.service";

import type {
  BillingSummary,
  CustomInvoiceLineItem,
  Invoice,
  InvoiceDetail,
  InvoiceDueState,
  InvoiceStatus,
  PaymentMethod,
} from "@/types/billing";

const statusConfig: Record<
  InvoiceStatus,
  { label: string; badge: string; dot: string }
> = {
  PAID: {
    label: "Paid",
    badge: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    dot: "bg-emerald-400",
  },
  PARTIALLY_PAID: {
    label: "Partially Paid",
    badge: "border-amber-500/30 bg-amber-500/10 text-amber-400",
    dot: "bg-amber-400",
  },
  UNPAID: {
    label: "Unpaid",
    badge: "border-rose-500/30 bg-rose-500/10 text-rose-400",
    dot: "bg-rose-400",
  },
  CANCELLED: {
    label: "Cancelled",
    badge: "border-zinc-500/30 bg-zinc-500/10 text-zinc-400",
    dot: "bg-zinc-400",
  },
};

const paymentMethods: { value: PaymentMethod; label: string }[] = [
  { value: "CASH", label: "Cash" },
  { value: "BANK_TRANSFER", label: "Bank Transfer" },
  { value: "CARD", label: "Debit / Credit Card" },
  { value: "MOBILE_WALLET", label: "Mobile Wallet (JazzCash / EasyPaisa)" },
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
    }).format(new Date(`${value.split("T")[0]}T00:00:00`));
  } catch {
    return value;
  }
}

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | "">("");
  const [dueStateFilter, setDueStateFilter] = useState<InvoiceDueState>("");
  const [billingPeriod, setBillingPeriod] = useState("");

  // Modals state
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);

  // Quick Pay Modal
  const [payModalInvoice, setPayModalInvoice] = useState<Invoice | null>(null);
  const [payAmount, setPayAmount] = useState("");
  const [payMethod, setPayMethod] = useState<PaymentMethod>("CASH");
  const [payReference, setPayReference] = useState("");
  const [payNotes, setPayNotes] = useState("");
  const [submittingPayment, setSubmittingPayment] = useState(false);

  // Cancel Invoice Modal
  const [cancelModalInvoice, setCancelModalInvoice] = useState<Invoice | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [submittingCancel, setSubmittingCancel] = useState(false);

  // Custom Invoice Modal
  const [isCustomInvoiceOpen, setIsCustomInvoiceOpen] = useState(false);
  const [customersList, setCustomersList] = useState<CustomerListItem[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [selectedCustomerDetail, setSelectedCustomerDetail] = useState<CustomerDetail | null>(null);
  const [selectedServiceId, setSelectedServiceId] = useState("");
  const [customPeriodStart, setCustomPeriodStart] = useState("");
  const [customPeriodEnd, setCustomPeriodEnd] = useState("");
  const [customIssueDate, setCustomIssueDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [customDueDate, setCustomDueDate] = useState("");
  const [customNotes, setCustomNotes] = useState("");
  const [customLineItems, setCustomLineItems] = useState<CustomInvoiceLineItem[]>([
    { description: "Monthly Broadband Service", amount: "", quantity: 1, unit_price: "" },
  ]);
  const [submittingCustomInv, setSubmittingCustomInv] = useState(false);

  // Monthly Run Modal
  const [isMonthlyRunOpen, setIsMonthlyRunOpen] = useState(false);
  const [runYear, setRunYear] = useState(new Date().getFullYear());
  const [runMonth, setRunMonth] = useState(new Date().getMonth() + 1);
  const [submittingMonthlyRun, setSubmittingMonthlyRun] = useState(false);

  // Load Data
  const loadData = useCallback(async () => {
    try {
      setError("");
      const [summaryRes, invoicesRes] = await Promise.all([
        billingService.getSummary(),
        billingService.getInvoices({
          status: statusFilter,
          due_state: dueStateFilter,
          search: search.trim() || undefined,
          billing_period: billingPeriod || undefined,
        }),
      ]);
      setSummary(summaryRes);
      setInvoices(invoicesRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load invoices.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [statusFilter, dueStateFilter, search, billingPeriod]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Load Customers for Custom Invoice
  const handleOpenCustomInvoiceModal = async () => {
    setIsCustomInvoiceOpen(true);
    if (customersList.length === 0) {
      try {
        const res = await customersService.getCustomers();
        setCustomersList(res);
      } catch (err) {
        toast.error("Failed to load customer list.");
      }
    }
  };

  const selectedCustomerRecord = useMemo(() => {
    return customersList.find((c) => c.id === selectedCustomerId);
  }, [customersList, selectedCustomerId]);

  const handleOpenDetail = async (invoiceId: string) => {
    try {
      setDetailLoading(true);
      setIsDetailDrawerOpen(true);
      const detail = await billingService.getInvoice(invoiceId);
      setSelectedInvoice(detail);
    } catch (err) {
      toast.error("Failed to load invoice details.");
      setIsDetailDrawerOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleRecordPayment = async (e: FormEvent) => {
    e.preventDefault();
    if (!payModalInvoice) return;

    try {
      setSubmittingPayment(true);
      await billingService.recordInvoicePayment(payModalInvoice.id, {
        amount: payAmount,
        payment_method: payMethod,
        reference: payReference.trim(),
        notes: payNotes.trim(),
      });
      toast.success(`Payment of PKR ${payAmount} recorded for ${payModalInvoice.invoice_number}`);
      setPayModalInvoice(null);
      setPayAmount("");
      setPayReference("");
      setPayNotes("");
      await loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to record payment.");
    } finally {
      setSubmittingPayment(false);
    }
  };

  const handleCancelInvoice = async (e: FormEvent) => {
    e.preventDefault();
    if (!cancelModalInvoice) return;
    if (!cancelReason.trim()) {
      toast.error("Please provide a cancellation reason.");
      return;
    }

    try {
      setSubmittingCancel(true);
      await billingService.cancelInvoice(cancelModalInvoice.id, cancelReason);
      toast.success(`Invoice ${cancelModalInvoice.invoice_number} cancelled.`);
      setCancelModalInvoice(null);
      setCancelReason("");
      await loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to cancel invoice.");
    } finally {
      setSubmittingCancel(false);
    }
  };

  const handleCreateCustomInvoice = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedServiceId) {
      toast.error("Please select a customer service connection.");
      return;
    }
    if (!customPeriodStart || !customPeriodEnd || !customDueDate) {
      toast.error("Please fill all billing dates.");
      return;
    }

    const validLines = customLineItems.filter(
      (l) => l.description.trim() && Number(l.amount) > 0
    );
    if (validLines.length === 0) {
      toast.error("Please enter at least one valid line item with an amount.");
      return;
    }

    try {
      setSubmittingCustomInv(true);
      await billingService.createCustomInvoice({
        service_account_id: selectedServiceId,
        billing_period_start: customPeriodStart,
        billing_period_end: customPeriodEnd,
        issue_date: customIssueDate,
        due_date: customDueDate,
        line_items: validLines,
        notes: customNotes.trim(),
      });
      toast.success("Custom invoice generated successfully.");
      setIsCustomInvoiceOpen(false);
      setSelectedCustomerId("");
      setSelectedServiceId("");
      setCustomLineItems([{ description: "Monthly Broadband Service", amount: "", quantity: 1 }]);
      await loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to generate custom invoice.");
    } finally {
      setSubmittingCustomInv(false);
    }
  };

  const handleRunMonthlyBilling = async (e: FormEvent) => {
    e.preventDefault();
    try {
      setSubmittingMonthlyRun(true);
      const res = await billingService.runMonthlyBilling({
        billing_year: Number(runYear),
        billing_month: Number(runMonth),
      });
      toast.success(
        `Monthly Run: ${res.generated_invoices} generated, ${res.skipped_existing_invoices} skipped, ${res.failed_services} failed.`
      );
      setIsMonthlyRunOpen(false);
      await loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to execute monthly billing run.");
    } finally {
      setSubmittingMonthlyRun(false);
    }
  };

  const addLineItem = () => {
    setCustomLineItems((prev) => [
      ...prev,
      { description: "", amount: "", quantity: 1, unit_price: "" },
    ]);
  };

  const removeLineItem = (index: number) => {
    setCustomLineItems((prev) => prev.filter((_, i) => i !== index));
  };

  const updateLineItem = (index: number, field: keyof CustomInvoiceLineItem, value: string | number) => {
    setCustomLineItems((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  const customInvoiceTotal = useMemo(() => {
    return customLineItems.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
  }, [customLineItems]);

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-[var(--border)] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-blue-500/20 bg-blue-500/10 text-blue-400">
              <FileSpreadsheet className="size-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                Invoices Management
              </h1>
              <p className="text-xs text-[var(--text-muted)]">
                Authoritative billing ledger, pro-rata invoices, recurring generation, and collection tracking.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={() => {
              setRefreshing(true);
              void loadData();
            }}
            disabled={refreshing}
            className="flex h-9 items-center gap-1.5 border border-[var(--border)] bg-[var(--surface)] px-3 text-xs font-semibold text-[var(--text-muted)] hover:bg-white/[0.04] hover:text-white"
          >
            <RefreshCw className={`size-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>

          <button
            type="button"
            onClick={() => setIsMonthlyRunOpen(true)}
            className="flex h-9 items-center gap-1.5 border border-purple-500/30 bg-purple-500/10 px-3.5 text-xs font-semibold text-purple-300 hover:bg-purple-500/20"
          >
            <RefreshCw className="size-3.5" />
            Run Monthly Billing
          </button>

          <button
            type="button"
            onClick={() => void handleOpenCustomInvoiceModal()}
            className="flex h-9 items-center gap-1.5 bg-blue-600 px-3.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-500"
          >
            <Plus className="size-3.5" />
            Create Custom Invoice
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Total Invoiced
            </span>
            <p className="mt-1 font-mono text-base font-bold text-white">
              {formatMoney(summary.total_invoiced, summary.currency)}
            </p>
            <span className="text-[10px] text-[var(--text-muted)]">{summary.invoice_count} invoices</span>
          </div>

          <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
              Total Collected
            </span>
            <p className="mt-1 font-mono text-base font-bold text-emerald-400">
              {formatMoney(summary.total_paid, summary.currency)}
            </p>
            <span className="text-[10px] text-emerald-500/80">{summary.paid_count} fully paid</span>
          </div>

          <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400">
              Outstanding Balance
            </span>
            <p className="mt-1 font-mono text-base font-bold text-amber-400">
              {formatMoney(summary.total_outstanding, summary.currency)}
            </p>
            <span className="text-[10px] text-amber-500/80">{summary.partially_paid_count} partial</span>
          </div>

          <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-rose-400">
              Overdue Amount
            </span>
            <p className="mt-1 font-mono text-base font-bold text-rose-400">
              {formatMoney(summary.overdue_outstanding, summary.currency)}
            </p>
            <span className="text-[10px] text-rose-500/80">{summary.overdue_count} overdue</span>
          </div>

          <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-blue-400">
              Collection Rate
            </span>
            <p className="mt-1 font-mono text-base font-bold text-blue-400">
              {summary.collection_rate || "0.00"}%
            </p>
            <span className="text-[10px] text-[var(--text-muted)]">Recovery efficiency</span>
          </div>

          <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
              Cancelled / Void
            </span>
            <p className="mt-1 font-mono text-base font-bold text-zinc-300">
              {summary.cancelled_count || 0}
            </p>
            <span className="text-[10px] text-[var(--text-muted)]">Audit trail preserved</span>
          </div>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="border border-[var(--border)] bg-[var(--surface)] p-4 space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              type="text"
              placeholder="Search invoice #, customer, service #..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9 w-full border border-[var(--border)] bg-[var(--background)] pl-9 pr-3 text-xs text-white placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as InvoiceStatus | "")}
              className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="">All Invoice Statuses</option>
              <option value="UNPAID">Unpaid Only</option>
              <option value="PARTIALLY_PAID">Partially Paid Only</option>
              <option value="PAID">Paid Only</option>
              <option value="CANCELLED">Cancelled / Voided Only</option>
            </select>
          </div>

          <div>
            <select
              value={dueStateFilter}
              onChange={(e) => setDueStateFilter(e.target.value as InvoiceDueState)}
              className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="">All Due States</option>
              <option value="OVERDUE">Overdue Invoices</option>
              <option value="DUE">Current Due Invoices</option>
              <option value="PAID">Cleared / Paid Invoices</option>
            </select>
          </div>

          <div>
            <input
              type="month"
              value={billingPeriod}
              onChange={(e) => setBillingPeriod(e.target.value)}
              className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
              placeholder="Billing Month (YYYY-MM)"
            />
          </div>
        </div>
      </div>

      {/* Invoices List Table */}
      <div className="border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="size-6 animate-spin text-blue-500" />
          </div>
        ) : error ? (
          <div className="p-8 text-center">
            <AlertTriangle className="mx-auto size-8 text-rose-400" />
            <p className="mt-2 text-sm text-rose-400">{error}</p>
          </div>
        ) : invoices.length === 0 ? (
          <div className="p-12 text-center">
            <FileSpreadsheet className="mx-auto size-10 text-[var(--text-muted)] opacity-40" />
            <h3 className="mt-3 text-sm font-semibold text-white">No Invoices Found</h3>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              No invoice records match your current filter criteria.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-[var(--border)] bg-white/[0.02] text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  <th className="px-4 py-3">Invoice Number</th>
                  <th className="px-4 py-3">Subscriber & Service</th>
                  <th className="px-4 py-3">Billing Period</th>
                  <th className="px-4 py-3">Due Date</th>
                  <th className="px-4 py-3 text-right">Total Amount</th>
                  <th className="px-4 py-3 text-right">Paid Amount</th>
                  <th className="px-4 py-3 text-right">Outstanding</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {invoices.map((inv) => {
                  const cfg = statusConfig[inv.status] || statusConfig.UNPAID;
                  const canPay = inv.status !== "PAID" && inv.status !== "CANCELLED";
                  const canCancel = inv.status === "UNPAID" && Number(inv.paid_amount) === 0;

                  return (
                    <tr key={inv.id} className="transition-colors hover:bg-white/[0.02]">
                      <td className="px-4 py-3 font-mono font-bold text-blue-400">
                        {inv.invoice_number}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/customers/${inv.customer_id}`}
                          className="font-semibold text-white hover:text-blue-400 hover:underline"
                        >
                          {inv.customer_name}
                        </Link>
                        <div className="font-mono text-[10px] text-[var(--text-muted)]">
                          {inv.service_number} • {inv.package_name}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-zinc-300">
                        {formatDate(inv.billing_period_start)} — {formatDate(inv.billing_period_end)}
                      </td>
                      <td className="px-4 py-3 text-zinc-300">
                        {formatDate(inv.due_date)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-white">
                        {formatMoney(inv.total_amount)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-emerald-400">
                        {formatMoney(inv.paid_amount)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-bold text-amber-400">
                        {formatMoney(inv.outstanding_amount)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${cfg.badge}`}>
                          <span className={`size-1.5 rounded-full ${cfg.dot}`} />
                          {cfg.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => void handleOpenDetail(inv.id)}
                            className="flex h-7 items-center gap-1 border border-[var(--border)] bg-[var(--background)] px-2 text-[10px] font-semibold text-[var(--text-muted)] hover:text-white"
                            title="View Invoice Breakdown"
                          >
                            <Eye className="size-3" />
                            View
                          </button>

                          {canPay && (
                            <button
                              type="button"
                              onClick={() => {
                                setPayModalInvoice(inv);
                                setPayAmount(inv.outstanding_amount);
                              }}
                              className="flex h-7 items-center gap-1 border border-emerald-500/30 bg-emerald-500/10 px-2 text-[10px] font-semibold text-emerald-400 hover:bg-emerald-500/20"
                            >
                              <Banknote className="size-3" />
                              Pay
                            </button>
                          )}

                          {canCancel && (
                            <button
                              type="button"
                              onClick={() => setCancelModalInvoice(inv)}
                              className="flex h-7 items-center gap-1 border border-rose-500/30 bg-rose-500/10 px-2 text-[10px] font-semibold text-rose-400 hover:bg-rose-500/20"
                              title="Cancel / Void Invoice"
                            >
                              <Trash2 className="size-3" />
                              Void
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

      {/* Invoice Detail Drawer */}
      {isDetailDrawerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/70 backdrop-blur-sm p-4">
          <div className="relative h-full max-h-[90vh] w-full max-w-2xl overflow-y-auto border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl">
            <button
              type="button"
              onClick={() => setIsDetailDrawerOpen(false)}
              className="absolute right-4 top-4 text-[var(--text-muted)] hover:text-white"
            >
              <X className="size-5" />
            </button>

            {detailLoading || !selectedInvoice ? (
              <div className="flex h-64 items-center justify-center">
                <Loader2 className="size-6 animate-spin text-blue-500" />
              </div>
            ) : (
              <div className="space-y-6">
                {/* Drawer Header */}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-blue-400">
                      {selectedInvoice.invoice_number}
                    </span>
                    <span className={`border px-2 py-0.5 text-[9px] font-bold uppercase ${statusConfig[selectedInvoice.status].badge}`}>
                      {selectedInvoice.status}
                    </span>
                  </div>
                  <h2 className="mt-1 text-lg font-bold text-white">
                    {selectedInvoice.customer_name}
                  </h2>
                  <p className="font-mono text-xs text-[var(--text-muted)]">
                    Service: {selectedInvoice.service_number} • {selectedInvoice.package_name}
                  </p>
                </div>

                {/* Dates & Totals Grid */}
                <div className="grid grid-cols-2 gap-3 border border-[var(--border)] bg-[var(--background)] p-4 sm:grid-cols-4">
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Billing Start</span>
                    <p className="text-xs font-semibold text-white">{formatDate(selectedInvoice.billing_period_start)}</p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Billing End</span>
                    <p className="text-xs font-semibold text-white">{formatDate(selectedInvoice.billing_period_end)}</p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Issue Date</span>
                    <p className="text-xs font-semibold text-white">{formatDate(selectedInvoice.issue_date)}</p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-rose-400">Due Date</span>
                    <p className="text-xs font-semibold text-rose-400">{formatDate(selectedInvoice.due_date)}</p>
                  </div>
                </div>

                {/* Line Items Breakdown */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                    Itemized Breakdown
                  </h3>
                  <div className="mt-2 border border-[var(--border)] overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-[var(--border)] bg-white/[0.02] text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                          <th className="p-3">Description</th>
                          <th className="p-3 text-center">Qty</th>
                          <th className="p-3 text-right">Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border)]">
                        {selectedInvoice.lines.map((line) => (
                          <tr key={line.id}>
                            <td className="p-3 text-white">{line.description}</td>
                            <td className="p-3 text-center font-mono text-[var(--text-muted)]">{line.quantity || 1}</td>
                            <td className="p-3 text-right font-mono font-semibold text-white">{formatMoney(line.amount)}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="border-t-2 border-[var(--border)] bg-white/[0.04] font-bold">
                          <td className="p-3 text-white" colSpan={2}>Total Invoiced Amount</td>
                          <td className="p-3 text-right font-mono text-emerald-400">{formatMoney(selectedInvoice.total_amount)}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>

                {/* Payments & Allocations */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                    Payment Allocations History
                  </h3>
                  {selectedInvoice.allocations.length === 0 ? (
                    <p className="mt-2 text-xs text-[var(--text-muted)] border border-[var(--border)] bg-[var(--background)] p-4 text-center">
                      No payments recorded yet for this invoice.
                    </p>
                  ) : (
                    <div className="mt-2 border border-[var(--border)] overflow-hidden">
                      <table className="w-full text-xs text-left">
                        <thead>
                          <tr className="border-b border-[var(--border)] bg-white/[0.02] text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                            <th className="p-3">Receipt / Payment #</th>
                            <th className="p-3">Method</th>
                            <th className="p-3">Date</th>
                            <th className="p-3 text-right">Allocated Amount</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--border)]">
                          {selectedInvoice.allocations.map((alloc) => (
                            <tr key={alloc.id}>
                              <td className="p-3 font-mono font-semibold text-blue-400">{alloc.payment_number}</td>
                              <td className="p-3 text-zinc-300">{alloc.payment_method}</td>
                              <td className="p-3 text-[var(--text-muted)]">{formatDate(alloc.paid_at)}</td>
                              <td className="p-3 text-right font-mono font-bold text-emerald-400">{formatMoney(alloc.amount)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Print button */}
                <div className="flex justify-end gap-2 pt-4 border-t border-[var(--border)]">
                  <button
                    type="button"
                    onClick={() => window.print()}
                    className="flex h-9 items-center gap-1.5 border border-[var(--border)] bg-[var(--background)] px-4 text-xs font-semibold text-white hover:bg-white/[0.05]"
                  >
                    <Printer className="size-3.5" />
                    Print Statement
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Record Payment Modal */}
      {payModalInvoice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
              <div>
                <h3 className="text-base font-bold text-white">Record Invoice Payment</h3>
                <p className="font-mono text-xs text-blue-400">{payModalInvoice.invoice_number}</p>
              </div>
              <button
                type="button"
                onClick={() => setPayModalInvoice(null)}
                className="text-[var(--text-muted)] hover:text-white"
              >
                <X className="size-4" />
              </button>
            </div>

            <form onSubmit={handleRecordPayment} className="mt-4 space-y-4">
              <div>
                <span className="text-[10px] uppercase text-[var(--text-muted)]">Outstanding Balance</span>
                <p className="font-mono text-lg font-bold text-amber-400">
                  {formatMoney(payModalInvoice.outstanding_amount)}
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-white">Payment Amount (PKR) *</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={payAmount}
                  onChange={(e) => setPayAmount(e.target.value)}
                  max={payModalInvoice.outstanding_amount}
                  className="mt-1 h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 font-mono text-sm text-white focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-white">Payment Method *</label>
                <select
                  value={payMethod}
                  onChange={(e) => setPayMethod(e.target.value as PaymentMethod)}
                  className="mt-1 h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
                >
                  {paymentMethods.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-white">Reference / Trx ID</label>
                <input
                  type="text"
                  value={payReference}
                  onChange={(e) => setPayReference(e.target.value)}
                  placeholder="e.g. Bank Ref #, Cheque #, JazzCash TID"
                  className="mt-1 h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-white">Collection Notes</label>
                <textarea
                  rows={2}
                  value={payNotes}
                  onChange={(e) => setPayNotes(e.target.value)}
                  placeholder="Optional collection remarks"
                  className="mt-1 w-full border border-[var(--border)] bg-[var(--background)] p-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setPayModalInvoice(null)}
                  className="h-9 px-4 text-xs font-semibold text-[var(--text-muted)] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingPayment}
                  className="flex h-9 items-center gap-1.5 bg-emerald-600 px-4 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {submittingPayment && <Loader2 className="size-3.5 animate-spin" />}
                  Confirm Collection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cancel Invoice Modal */}
      {cancelModalInvoice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="size-5 text-rose-400" />
                <h3 className="text-base font-bold text-white">Cancel / Void Invoice</h3>
              </div>
              <button
                type="button"
                onClick={() => setCancelModalInvoice(null)}
                className="text-[var(--text-muted)] hover:text-white"
              >
                <X className="size-4" />
              </button>
            </div>

            <form onSubmit={handleCancelInvoice} className="mt-4 space-y-4">
              <p className="text-xs text-[var(--text-muted)]">
                Are you sure you want to void invoice <strong className="text-white font-mono">{cancelModalInvoice.invoice_number}</strong>?
                This action is irreversible and recorded in the audit log.
              </p>

              <div>
                <label className="block text-xs font-semibold text-white">Cancellation Reason *</label>
                <textarea
                  rows={3}
                  required
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="Explain why this invoice is being voided (e.g. billing error, customer changed plan before cycle)..."
                  className="mt-1 w-full border border-[var(--border)] bg-[var(--background)] p-2 text-xs text-white focus:border-rose-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCancelModalInvoice(null)}
                  className="h-9 px-4 text-xs font-semibold text-[var(--text-muted)] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingCancel}
                  className="flex h-9 items-center gap-1.5 bg-rose-600 px-4 text-xs font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
                >
                  {submittingCancel && <Loader2 className="size-3.5 animate-spin" />}
                  Confirm Void
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Monthly Run Modal */}
      {isMonthlyRunOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
              <div>
                <h3 className="text-base font-bold text-white">Run Monthly Billing Batch</h3>
                <p className="text-xs text-[var(--text-muted)]">
                  Generates invoices for all eligible active subscribers for the cycle.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsMonthlyRunOpen(false)}
                className="text-[var(--text-muted)] hover:text-white"
              >
                <X className="size-4" />
              </button>
            </div>

            <form onSubmit={handleRunMonthlyBilling} className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-white">Year *</label>
                  <input
                    type="number"
                    min={2024}
                    max={2100}
                    required
                    value={runYear}
                    onChange={(e) => setRunYear(Number(e.target.value))}
                    className="mt-1 h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-white">Month *</label>
                  <select
                    value={runMonth}
                    onChange={(e) => setRunMonth(Number(e.target.value))}
                    className="mt-1 h-9 w-full border border-[var(--border)] bg-[var(--background)] px-3 text-xs text-white focus:border-blue-500 focus:outline-none"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => (
                      <option key={m} value={m}>
                        {new Date(2026, m - 1).toLocaleString("default", { month: "long" })} ({m})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="border border-blue-500/20 bg-blue-500/10 p-3 text-xs text-blue-300">
                <p className="font-semibold">Idempotent Execution Guarantee:</p>
                <p className="mt-0.5 text-[11px] text-blue-200/80">
                  Subscribers with an invoice already generated for this billing cycle will be safely skipped. No duplicates will be created.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsMonthlyRunOpen(false)}
                  className="h-9 px-4 text-xs font-semibold text-[var(--text-muted)] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingMonthlyRun}
                  className="flex h-9 items-center gap-1.5 bg-purple-600 px-4 text-xs font-semibold text-white hover:bg-purple-500 disabled:opacity-50"
                >
                  {submittingMonthlyRun && <Loader2 className="size-3.5 animate-spin" />}
                  Execute Run
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Custom Invoice Modal */}
      {isCustomInvoiceOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="h-full max-h-[90vh] w-full max-w-2xl overflow-y-auto border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
              <div>
                <h3 className="text-base font-bold text-white">Create Custom Invoice</h3>
                <p className="text-xs text-[var(--text-muted)]">
                  Generate manual, pro-rata, equipment, or customized multi-item invoices.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsCustomInvoiceOpen(false)}
                className="text-[var(--text-muted)] hover:text-white"
              >
                <X className="size-4" />
              </button>
            </div>

            <form onSubmit={handleCreateCustomInvoice} className="mt-4 space-y-4">
              {/* Select Customer */}
              <div>
                <label className="block text-xs font-semibold text-white">Select Subscriber *</label>
                <select
                  required
                  value={selectedCustomerId}
                  onChange={async (e) => {
                    const cId = e.target.value;
                    setSelectedCustomerId(cId);
                    if (!cId) {
                      setSelectedCustomerDetail(null);
                      setSelectedServiceId("");
                      return;
                    }
                    try {
                      const detail = await customersService.getCustomer(cId);
                      setSelectedCustomerDetail(detail);
                      if (detail.service_accounts && detail.service_accounts.length > 0) {
                        setSelectedServiceId(detail.service_accounts[0].id);
                      } else {
                        setSelectedServiceId("");
                      }
                    } catch {
                      setSelectedCustomerDetail(null);
                      setSelectedServiceId("");
                    }
                  }}
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

              {/* Select Service Account */}
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
                        {svc.service_number} ({svc.internet_package.name} - PKR {svc.internet_package.monthly_price})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Dates */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div>
                  <label className="block text-[11px] font-semibold text-white">Period Start *</label>
                  <input
                    type="date"
                    required
                    value={customPeriodStart}
                    onChange={(e) => setCustomPeriodStart(e.target.value)}
                    className="mt-1 h-8 w-full border border-[var(--border)] bg-[var(--background)] px-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-white">Period End *</label>
                  <input
                    type="date"
                    required
                    value={customPeriodEnd}
                    onChange={(e) => setCustomPeriodEnd(e.target.value)}
                    className="mt-1 h-8 w-full border border-[var(--border)] bg-[var(--background)] px-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-white">Issue Date *</label>
                  <input
                    type="date"
                    required
                    value={customIssueDate}
                    onChange={(e) => setCustomIssueDate(e.target.value)}
                    className="mt-1 h-8 w-full border border-[var(--border)] bg-[var(--background)] px-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-rose-400">Due Date *</label>
                  <input
                    type="date"
                    required
                    value={customDueDate}
                    onChange={(e) => setCustomDueDate(e.target.value)}
                    className="mt-1 h-8 w-full border border-rose-500/30 bg-[var(--background)] px-2 text-xs text-rose-400 focus:border-rose-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Line items */}
              <div className="border border-[var(--border)] p-3">
                <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
                  <span className="text-xs font-bold uppercase tracking-wider text-white">
                    Invoice Line Items
                  </span>
                  <button
                    type="button"
                    onClick={addLineItem}
                    className="flex h-6 items-center gap-1 border border-blue-500/30 bg-blue-500/10 px-2 text-[10px] font-semibold text-blue-400 hover:bg-blue-500/20"
                  >
                    <Plus className="size-3" />
                    Add Item
                  </button>
                </div>

                <div className="mt-3 space-y-2">
                  {customLineItems.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input
                        type="text"
                        required
                        placeholder="Item description (e.g. ONT Router Fee, Installation Service)..."
                        value={item.description}
                        onChange={(e) => updateLineItem(idx, "description", e.target.value)}
                        className="h-8 flex-1 border border-[var(--border)] bg-[var(--background)] px-2.5 text-xs text-white focus:border-blue-500 focus:outline-none"
                      />
                      <input
                        type="number"
                        min={1}
                        placeholder="Qty"
                        value={item.quantity || 1}
                        onChange={(e) => updateLineItem(idx, "quantity", Number(e.target.value))}
                        className="h-8 w-16 border border-[var(--border)] bg-[var(--background)] px-2 text-center text-xs text-white focus:border-blue-500 focus:outline-none"
                      />
                      <input
                        type="number"
                        step="0.01"
                        required
                        placeholder="Amount"
                        value={item.amount}
                        onChange={(e) => updateLineItem(idx, "amount", e.target.value)}
                        className="h-8 w-28 border border-[var(--border)] bg-[var(--background)] px-2 text-right font-mono text-xs text-white focus:border-blue-500 focus:outline-none"
                      />
                      {customLineItems.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeLineItem(idx)}
                          className="text-rose-400 hover:text-rose-300 p-1"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                <div className="mt-3 flex justify-between border-t border-[var(--border)] pt-2 text-xs font-bold text-white">
                  <span>Total Calculated:</span>
                  <span className="font-mono text-emerald-400">{formatMoney(customInvoiceTotal)}</span>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-xs font-semibold text-white">Notes / Description</label>
                <textarea
                  rows={2}
                  value={customNotes}
                  onChange={(e) => setCustomNotes(e.target.value)}
                  placeholder="Optional internal remarks"
                  className="mt-1 w-full border border-[var(--border)] bg-[var(--background)] p-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCustomInvoiceOpen(false)}
                  className="h-9 px-4 text-xs font-semibold text-[var(--text-muted)] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingCustomInv}
                  className="flex h-9 items-center gap-1.5 bg-blue-600 px-4 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  {submittingCustomInv && <Loader2 className="size-3.5 animate-spin" />}
                  Generate Invoice
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
