"use client";

import {
  AlertTriangle,
  Banknote,
  CheckCircle2,
  CircleDollarSign,
  CreditCard,
  Loader2,
  Plus,
  ReceiptText,
  RefreshCw,
  Search,
  WalletCards,
  X,
} from "lucide-react";
import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { billingService } from "@/services/billing.service";
import {
  customersService,
  type CustomerListItem,
  type CustomerServiceAccount,
} from "@/services/customers.service";

import type {
  BillingSummary,
  Invoice,
  InvoiceDueState,
  InvoiceStatus,
  PaymentMethod,
} from "@/types/billing";

const paymentMethods: {
  value: PaymentMethod;
  label: string;
}[] = [
  {
    value: "CASH",
    label: "Cash",
  },
  {
    value: "BANK_TRANSFER",
    label: "Bank Transfer",
  },
  {
    value: "CARD",
    label: "Card",
  },
  {
    value: "MOBILE_WALLET",
    label: "Mobile Wallet",
  },
  {
    value: "OTHER",
    label: "Other",
  },
];

const months = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

function formatMoney(
  amount: string | number,
  currency: string,
): string {
  const value = Number(amount);

  return `${currency} ${value.toLocaleString("en-PK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-PK", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

function getStatusStyles(
  status: InvoiceStatus,
): string {
  if (status === "PAID") {
    return "border-green-500/20 bg-green-500/10 text-green-400";
  }

  if (status === "PARTIALLY_PAID") {
    return "border-amber-500/20 bg-amber-500/10 text-amber-400";
  }

  return "border-red-500/20 bg-red-500/10 text-red-400";
}

function getStatusLabel(
  status: InvoiceStatus,
): string {
  if (status === "PARTIALLY_PAID") {
    return "Partially Paid";
  }

  if (status === "UNPAID") {
    return "Unpaid";
  }

  return "Paid";
}

export default function BillingPage() {
  const [summary, setSummary] =
    useState<BillingSummary | null>(null);

  const [invoices, setInvoices] = useState<
    Invoice[]
  >([]);

  const [loading, setLoading] = useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] = useState("");

  const [search, setSearch] = useState("");

  const [statusFilter, setStatusFilter] =
    useState<InvoiceStatus | "">("");

  const [dueStateFilter, setDueStateFilter] =
    useState<InvoiceDueState>("");

  const [billingPeriod, setBillingPeriod] =
    useState("");

  const [selectedInvoice, setSelectedInvoice] =
    useState<Invoice | null>(null);

  const [paymentAmount, setPaymentAmount] =
    useState("");

  const [paymentMethod, setPaymentMethod] =
    useState<PaymentMethod>("CASH");

  const [paymentReference, setPaymentReference] =
    useState("");

  const [paymentNotes, setPaymentNotes] =
    useState("");

  const [paymentSubmitting, setPaymentSubmitting] =
    useState(false);

  const [paymentError, setPaymentError] =
    useState("");

  const [generatingInvoice, setGeneratingInvoice] =
    useState(false);

  const [showGenerateModal, setShowGenerateModal] =
    useState(false);

  const [customers, setCustomers] = useState<
    CustomerListItem[]
  >([]);

  const [loadingCustomers, setLoadingCustomers] =
    useState(false);

  const [selectedCustomerId, setSelectedCustomerId] =
    useState("");

  const [serviceAccounts, setServiceAccounts] =
    useState<CustomerServiceAccount[]>([]);

  const [selectedServiceAccountId, setSelectedServiceAccountId] =
    useState("");

  const today = new Date();

  const [billingMonth, setBillingMonth] = useState(
    today.getMonth() + 1,
  );

  const [billingYear, setBillingYear] = useState(
    today.getFullYear(),
  );

  const [generateError, setGenerateError] =
    useState("");

  const [generateSuccess, setGenerateSuccess] =
    useState(false);

  const loadBillingData = useCallback(
    async (showRefreshState = false) => {
      if (showRefreshState) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      try {
        const [summaryData, invoiceData] =
          await Promise.all([
            billingService.getSummary(),
            billingService.getInvoices({
              search,
              status: statusFilter,
              due_state: dueStateFilter,
              billing_period: billingPeriod,
            }),
          ]);

        setSummary(summaryData);
        setInvoices(invoiceData);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to load billing operations.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [
      billingPeriod,
      dueStateFilter,
      search,
      statusFilter,
    ],
  );

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadBillingData();
    }, 250);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [loadBillingData]);

  const metrics = useMemo(() => {
    if (!summary) {
      return [];
    }

    return [
      {
        label: "Total Invoiced",
        value: formatMoney(
          summary.total_invoiced,
          summary.currency,
        ),
        description: `${summary.invoice_count} invoices`,
        icon: ReceiptText,
        tone: "text-blue-400",
      },
      {
        label: "Total Paid",
        value: formatMoney(
          summary.total_paid,
          summary.currency,
        ),
        description: `${summary.paid_count} fully paid`,
        icon: CheckCircle2,
        tone: "text-green-400",
      },
      {
        label: "Outstanding",
        value: formatMoney(
          summary.total_outstanding,
          summary.currency,
        ),
        description: "Open ledger balance",
        icon: CircleDollarSign,
        tone: "text-amber-400",
      },
      {
        label: "Overdue",
        value: formatMoney(
          summary.overdue_outstanding,
          summary.currency,
        ),
        description: `${summary.overdue_count} overdue invoices`,
        icon: AlertTriangle,
        tone: "text-red-400",
      },
      {
        label: "Unpaid",
        value: String(summary.unpaid_count),
        description: "Invoices awaiting payment",
        icon: WalletCards,
        tone: "text-red-400",
      },
      {
        label: "Partial",
        value: String(
          summary.partially_paid_count,
        ),
        description: "Partially settled invoices",
        icon: CreditCard,
        tone: "text-amber-400",
      },
    ];
  }, [summary]);

  function openPayment(invoice: Invoice) {
    setSelectedInvoice(invoice);
    setPaymentAmount(invoice.outstanding_amount);
    setPaymentMethod("CASH");
    setPaymentReference("");
    setPaymentNotes("");
    setPaymentError("");
  }

  function closePayment() {
    if (paymentSubmitting) {
      return;
    }

    setSelectedInvoice(null);
    setPaymentError("");
  }

  async function handlePaymentSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!selectedInvoice) {
      return;
    }

    setPaymentSubmitting(true);
    setPaymentError("");

    try {
      await billingService.recordInvoicePayment(
        selectedInvoice.id,
        {
          amount: paymentAmount,
          payment_method: paymentMethod,
          reference: paymentReference,
          notes: paymentNotes,
        },
      );

      setSelectedInvoice(null);

      await loadBillingData(true);
    } catch (requestError) {
      setPaymentError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to record payment.",
      );
    } finally {
      setPaymentSubmitting(false);
    }
  }

  async function openGenerateInvoiceModal() {
    setShowGenerateModal(true);

    setGenerateError("");
    setGenerateSuccess(false);

    setLoadingCustomers(true);

    try {
      const data =
        await customersService.getCustomers();

      setCustomers(data);
    } catch (error) {
      setGenerateError("Unable to load customers.");
    } finally {
      setLoadingCustomers(false);
    }
  }

  function closeGenerateInvoiceModal() {
    if (generatingInvoice) {
      return;
    }

    setShowGenerateModal(false);

    setSelectedCustomerId("");
    setSelectedServiceAccountId("");

    setCustomers([]);
    setServiceAccounts([]);

    setBillingMonth(today.getMonth() + 1);
    setBillingYear(today.getFullYear());

    setGenerateError("");
    setGenerateSuccess(false);
  }

  async function handleCustomerChange(
    customerId: string,
  ) {
    setSelectedCustomerId(customerId);

    setSelectedServiceAccountId("");

    setGenerateError("");

    if (!customerId) {
      setServiceAccounts([]);
      return;
    }

    try {
      const customer =
        await customersService.getCustomer(
          customerId,
        );

      setServiceAccounts(
        customer.service_accounts,
      );
    } catch {
      setGenerateError(
        "Unable to load customer services.",
      );
    }
  }

  async function handleGenerateInvoice() {
    setGenerateError("");
    setGenerateSuccess(false);

    if (!selectedCustomerId) {
      setGenerateError("Please select customer.");
      return;
    }

    if (!selectedServiceAccountId) {
      setGenerateError("Please select service.");
      return;
    }

    setGeneratingInvoice(true);

    try {
      await billingService.generateInvoice({
        service_account_id: selectedServiceAccountId,
        billing_year: billingYear,
        billing_month: billingMonth,
      });

      setGenerateError("");
      setGenerateSuccess(true);

      await loadBillingData(true);

      window.setTimeout(() => {
        closeGenerateInvoiceModal();
      }, 1200);
    } catch (error) {
      setGenerateError(
        error instanceof Error
          ? error.message
          : "Unable to generate invoice.",
      );
    } finally {
      setGeneratingInvoice(false);
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[#F8FAFC]">
            Billing & Payments
          </h1>

          <p className="mt-1 text-sm text-[#64748B]">
            Monitor invoices, outstanding balances,
            overdue exposure and payment operations.
          </p>
        </div>

        <div className="flex items-center gap-3">

  <div className="flex h-10 items-center gap-2 border border-[#202938] bg-[#0D1117] px-3">
    <Banknote className="h-3.5 w-3.5 text-[#22C55E]" />

    <span className="text-xs text-[#94A3B8]">
      Billing Engine Operational
    </span>
  </div>

  <button
    type="button"
    onClick={openGenerateInvoiceModal}
    disabled={generatingInvoice}
    className="flex h-10 items-center gap-2 bg-emerald-600 px-4 text-xs font-medium text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
  >
    {generatingInvoice ? (
      <Loader2 className="h-4 w-4 animate-spin" />
    ) : (
      <Plus className="h-4 w-4" />
    )}

    Generate Invoice
  </button>

  <button
    type="button"
    onClick={() => void loadBillingData(true)}
    disabled={refreshing}
    className="flex h-10 items-center gap-2 border border-[#202938] bg-[#111827] px-4 text-xs font-medium text-[#CBD5E1] transition-colors hover:bg-[#182131] disabled:cursor-not-allowed disabled:opacity-60"
  >
    <RefreshCw
      className={`h-4 w-4 ${
        refreshing ? "animate-spin" : ""
      }`}
    />

    Refresh
  </button>

</div>
      </div>

      {error ? (
        <div className="border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {metrics.map((metric) => {
          const Icon = metric.icon;

          return (
            <div
              key={metric.label}
              className="border border-[#202938] bg-[#0D1117] p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.12em] text-[#64748B]">
                    {metric.label}
                  </p>

                  <p className="mt-3 text-xl font-semibold text-[#F8FAFC]">
                    {metric.value}
                  </p>
                </div>

                <Icon
                  className={`h-4 w-4 ${metric.tone}`}
                />
              </div>

              <p className="mt-2 text-xs text-[#64748B]">
                {metric.description}
              </p>
            </div>
          );
        })}
      </div>

      <div className="border border-[#202938] bg-[#0D1117]">
        <div className="border-b border-[#202938] p-4">
          <div className="flex flex-col gap-4 2xl:flex-row 2xl:items-center 2xl:justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#F8FAFC]">
                Invoice Operations
              </h2>

              <p className="mt-1 text-xs text-[#64748B]">
                Real tenant-scoped billing ledger.
              </p>
            </div>

            <div className="flex flex-col gap-2 lg:flex-row">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#64748B]" />

                <input
                  value={search}
                  onChange={(event) =>
                    setSearch(event.target.value)
                  }
                  placeholder="Search customer, service, invoice..."
                  className="h-10 w-full border border-[#202938] bg-[#080B10] pl-9 pr-3 text-xs text-[#F8FAFC] outline-none placeholder:text-[#475569] focus:border-[#3B82F6] lg:w-72"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(
                    event.target.value as
                      | InvoiceStatus
                      | "",
                  )
                }
                className="h-10 border border-[#202938] bg-[#080B10] px-3 text-xs text-[#CBD5E1] outline-none focus:border-[#3B82F6]"
              >
                <option value="">
                  All Statuses
                </option>
                <option value="UNPAID">
                  Unpaid
                </option>
                <option value="PARTIALLY_PAID">
                  Partially Paid
                </option>
                <option value="PAID">
                  Paid
                </option>
              </select>

              <select
                value={dueStateFilter}
                onChange={(event) =>
                  setDueStateFilter(
                    event.target
                      .value as InvoiceDueState,
                  )
                }
                className="h-10 border border-[#202938] bg-[#080B10] px-3 text-xs text-[#CBD5E1] outline-none focus:border-[#3B82F6]"
              >
                <option value="">
                  All Due States
                </option>
                <option value="OVERDUE">
                  Overdue
                </option>
                <option value="DUE">
                  Due
                </option>
                <option value="PAID">
                  Paid
                </option>
              </select>

              <input
                type="month"
                value={billingPeriod}
                onChange={(event) =>
                  setBillingPeriod(
                    event.target.value,
                  )
                }
                className="h-10 border border-[#202938] bg-[#080B10] px-3 text-xs text-[#CBD5E1] outline-none focus:border-[#3B82F6]"
              />
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1200px]">
            <thead>
              <tr className="border-b border-[#202938] bg-[#0A0E14]">
                {[
                  "Invoice",
                  "Customer",
                  "Service",
                  "Package",
                  "Period",
                  "Total",
                  "Paid",
                  "Outstanding",
                  "Due Date",
                  "Status",
                  "Action",
                ].map((heading) => (
                  <th
                    key={heading}
                    className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[#64748B]"
                  >
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td
                    colSpan={11}
                    className="px-4 py-16 text-center"
                  >
                    <Loader2 className="mx-auto h-5 w-5 animate-spin text-[#3B82F6]" />

                    <p className="mt-3 text-xs text-[#64748B]">
                      Loading billing ledger...
                    </p>
                  </td>
                </tr>
              ) : invoices.length === 0 ? (
                <tr>
                  <td
                    colSpan={11}
                    className="px-4 py-16 text-center text-sm text-[#64748B]"
                  >
                    No invoices matched the current
                    filters.
                  </td>
                </tr>
              ) : (
                invoices.map((invoice) => (
                  <tr
                    key={invoice.id}
                    className="border-b border-[#182131] transition-colors last:border-b-0 hover:bg-[#111827]"
                  >
                    <td className="px-4 py-4">
                      <p className="text-xs font-medium text-[#F8FAFC]">
                        {invoice.invoice_number}
                      </p>

                      <p className="mt-1 text-[11px] text-[#64748B]">
                        {formatDate(
                          invoice.issue_date,
                        )}
                      </p>
                    </td>

                    <td className="px-4 py-4">
                      <p className="text-xs text-[#E2E8F0]">
                        {invoice.customer_name}
                      </p>

                      <p className="mt-1 text-[11px] text-[#64748B]">
                        {invoice.customer_number}
                      </p>
                    </td>

                    <td className="px-4 py-4 text-xs text-[#94A3B8]">
                      {invoice.service_number}
                    </td>

                    <td className="px-4 py-4 text-xs text-[#94A3B8]">
                      {invoice.package_name}
                    </td>

                    <td className="px-4 py-4 text-xs text-[#94A3B8]">
                      {formatDate(
                        invoice.billing_period_start,
                      )}
                      <span className="mx-1 text-[#475569]">
                        —
                      </span>
                      {formatDate(
                        invoice.billing_period_end,
                      )}
                    </td>

                    <td className="px-4 py-4 text-xs font-medium text-[#E2E8F0]">
                      {formatMoney(
                        invoice.total_amount,
                        summary?.currency ?? "PKR",
                      )}
                    </td>

                    <td className="px-4 py-4 text-xs text-green-400">
                      {formatMoney(
                        invoice.paid_amount,
                        summary?.currency ?? "PKR",
                      )}
                    </td>

                    <td className="px-4 py-4 text-xs font-medium text-amber-400">
                      {formatMoney(
                        invoice.outstanding_amount,
                        summary?.currency ?? "PKR",
                      )}
                    </td>

                    <td className="px-4 py-4 text-xs text-[#94A3B8]">
                      {formatDate(invoice.due_date)}
                    </td>

                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] ${getStatusStyles(
                          invoice.status,
                        )}`}
                      >
                        {getStatusLabel(
                          invoice.status,
                        )}
                      </span>
                    </td>

                    <td className="px-4 py-4">
                      {invoice.status !== "PAID" ? (
                        <button
                          type="button"
                          onClick={() =>
                            openPayment(invoice)
                          }
                          className="h-8 bg-[#3B82F6] px-3 text-[11px] font-medium text-white transition-colors hover:bg-[#2563EB]"
                        >
                          Record Payment
                        </button>
                      ) : (
                        <span className="text-[11px] text-green-400">
                          Settled
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedInvoice ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md border border-[#202938] bg-[#0D1117] shadow-2xl">
            <div className="flex items-start justify-between border-b border-[#202938] px-4 py-3">
              <div>
                <h2 className="text-base font-semibold text-[#F8FAFC]">
                  Record Invoice Payment
                </h2>

                <p className="mt-1 text-xs text-[#64748B]">
                  {selectedInvoice.invoice_number}
                  {" · "}
                  {selectedInvoice.customer_name}
                </p>
              </div>

              <button
                type="button"
                onClick={closePayment}
                className="text-[#64748B] transition-colors hover:text-[#F8FAFC]"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form
              onSubmit={handlePaymentSubmit}
              className="space-y-3 p-4"
            >
              <div className="grid grid-cols-2 gap-3">
                <div className="border border-[#202938] bg-[#080B10] p-3">
                  <p className="text-[10px] uppercase tracking-[0.1em] text-[#64748B]">
                    Invoice Total
                  </p>

                  <p className="mt-2 text-sm font-semibold text-[#F8FAFC]">
                    {formatMoney(
                      selectedInvoice.total_amount,
                      summary?.currency ?? "PKR",
                    )}
                  </p>
                </div>

                <div className="border border-[#202938] bg-[#080B10] p-3">
                  <p className="text-[10px] uppercase tracking-[0.1em] text-[#64748B]">
                    Outstanding
                  </p>

                  <p className="mt-2 text-sm font-semibold text-amber-400">
                    {formatMoney(
                      selectedInvoice.outstanding_amount,
                      summary?.currency ?? "PKR",
                    )}
                  </p>
                </div>
              </div>

              {paymentError ? (
                <div className="border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                  {paymentError}
                </div>
              ) : null}

              <label className="block">
                <span className="text-xs text-[#94A3B8]">
                  Payment Amount
                </span>

                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  required
                  value={paymentAmount}
                  onChange={(event) =>
                    setPaymentAmount(
                      event.target.value,
                    )
                  }
                  className="mt-2 h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-sm text-[#F8FAFC] outline-none focus:border-[#3B82F6]"
                />
              </label>

              <label className="block">
                <span className="text-xs text-[#94A3B8]">
                  Payment Method
                </span>

                <select
                  value={paymentMethod}
                  onChange={(event) =>
                    setPaymentMethod(
                      event.target
                        .value as PaymentMethod,
                    )
                  }
                  className="mt-2 h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-sm text-[#F8FAFC] outline-none focus:border-[#3B82F6]"
                >
                  {paymentMethods.map((method) => (
                    <option
                      key={method.value}
                      value={method.value}
                    >
                      {method.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs text-[#94A3B8]">
                  Reference
                </span>

                <input
                  value={paymentReference}
                  onChange={(event) =>
                    setPaymentReference(
                      event.target.value,
                    )
                  }
                  maxLength={150}
                  placeholder="Bank reference, receipt number..."
                  className="mt-2 h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-sm text-[#F8FAFC] outline-none placeholder:text-[#475569] focus:border-[#3B82F6]"
                />
              </label>

              <label className="block">
                <span className="text-xs text-[#94A3B8]">
                  Notes
                </span>

                <textarea
                  value={paymentNotes}
                  onChange={(event) =>
                    setPaymentNotes(
                      event.target.value,
                    )
                  }
                  rows={2}
                  placeholder="Optional payment notes..."
                  className="mt-2 w-full resize-none border border-[#202938] bg-[#080B10] p-3 text-sm text-[#F8FAFC] outline-none placeholder:text-[#475569] focus:border-[#3B82F6]"
                />
              </label>

              <div className="flex justify-end gap-3 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={closePayment}
                  disabled={paymentSubmitting}
                  className="h-10 border border-[#202938] px-4 text-xs font-medium text-[#94A3B8] transition-colors hover:bg-[#111827]"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={paymentSubmitting}
                  className="flex h-10 items-center gap-2 bg-[#3B82F6] px-4 text-xs font-medium text-white transition-colors hover:bg-[#2563EB] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {paymentSubmitting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Banknote className="h-4 w-4" />
                  )}

                  Record Payment
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {showGenerateModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg border border-[#202938] bg-[#0D1117]">

            <div className="flex items-center justify-between border-b border-[#202938] px-5 py-4">

              <div>
                <h2 className="text-lg font-semibold text-white">
                  Generate Invoice
                </h2>

                <p className="mt-1 text-xs text-[#64748B]">
                  Generate a billing invoice for an active service.
                </p>
              </div>

              <button
                onClick={closeGenerateInvoiceModal}
                disabled={generatingInvoice}
                className="text-[#64748B] hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                <X className="h-5 w-5" />
              </button>

            </div>

            <div className="space-y-4 p-5">

              {generateError ? (
                <div className="rounded border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">
                  {generateError}
                </div>
              ) : null}

              {generateSuccess ? (
                <div className="rounded border border-green-500/20 bg-green-500/10 p-3 text-xs text-green-400">
                  Invoice generated successfully.
                </div>
              ) : null}

              <div>
                <label className="mb-2 block text-xs text-[#94A3B8]">
                  Customer
                </label>

                <select
                  value={selectedCustomerId}
                  onChange={(e) =>
                    void handleCustomerChange(e.target.value)
                  }
                  disabled={loadingCustomers}
                  className="h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-sm text-white"
                >
                  <option value="">
                    {loadingCustomers
                      ? "Loading customers..."
                      : "Select Customer"}
                  </option>

                  {customers.map((customer) => (
                    <option
                      key={customer.id}
                      value={customer.id}
                    >
                      {customer.full_name}
                      {" - "}
                      {customer.customer_number}
                    </option>
                  ))}
                </select>

              </div>

              <div>

                <label className="mb-2 block text-xs text-[#94A3B8]">
                  Service Account
                </label>

                <select
                  value={selectedServiceAccountId}
                  onChange={(e) =>
                    setSelectedServiceAccountId(
                      e.target.value,
                    )
                  }
                  disabled={
                    !selectedCustomerId ||
                    serviceAccounts.length === 0
                  }
                  className="h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-sm text-white"
                >

                  <option value="">
                    {!selectedCustomerId
                      ? "Select Customer First"
                      : "Select Service"}
                  </option>

                  {serviceAccounts.map((service) => (

                    <option
                      key={service.id}
                      value={service.id}
                    >

                      {service.service_number}

                      {" • "}

                      {service.internet_package.name}

                      {" • "}

                      {service.status}

                    </option>

                  ))}

                </select>

              </div>

              <div className="grid grid-cols-2 gap-4">

                <div>

                  <label className="mb-2 block text-xs text-[#94A3B8]">
                    Billing Month
                  </label>

                  <select
                    value={billingMonth}
                    onChange={(e) =>
                      setBillingMonth(Number(e.target.value))
                    }
                    className="h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-sm text-white"
                  >

                    {months.map((month, index) => (
                      <option
                        key={index}
                        value={index + 1}
                      >
                        {month}
                      </option>
                    ))}

                  </select>

                </div>

                <div>

                  <label className="mb-2 block text-xs text-[#94A3B8]">
                    Billing Year
                  </label>

                  <input
                    type="number"
                    value={billingYear}
                    onChange={(e) =>
                      setBillingYear(
                        Number(e.target.value),
                      )
                    }
                    className="h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-sm text-white"
                  />

                </div>

              </div>

              <div className="flex justify-end gap-3 border-t border-[#202938] pt-5">

                <button
                  type="button"
                  onClick={closeGenerateInvoiceModal}
                  disabled={generatingInvoice}
                  className="h-10 border border-[#202938] px-5 text-xs text-[#CBD5E1] disabled:cursor-not-allowed disabled:opacity-60"
                >

                  Cancel

                </button>

                <button
                  type="button"
                  onClick={() => void handleGenerateInvoice()}
                  disabled={
                    generatingInvoice ||
                    !selectedCustomerId ||
                    !selectedServiceAccountId
                  }
                  className="flex h-10 items-center gap-2 bg-emerald-600 px-5 text-xs font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                >

                  {generatingInvoice ? (

                    <Loader2 className="h-4 w-4 animate-spin" />

                  ) : (

                    <Plus className="h-4 w-4" />

                  )}

                  Generate Invoice

                </button>

              </div>

            </div>

          </div>

        </div>
      ) : null}
    </div>
  );
}