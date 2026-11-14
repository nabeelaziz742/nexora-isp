"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, RefreshCw, Search, Wallet, Zap } from "lucide-react";
import { toast } from "sonner";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import {
  dealerPortalService,
  type DealerCustomerRow,
  type DealerPaymentMethod,
  type DealerSummary,
} from "@/services/dealer-portal.service";

const METHODS: { value: DealerPaymentMethod; label: string }[] = [
  { value: "CASH", label: "Cash" },
  { value: "MOBILE_WALLET", label: "JazzCash / Easypaisa" },
  { value: "BANK_TRANSFER", label: "Bank Transfer" },
];

const FILTERS = [
  { value: "", label: "All" },
  { value: "due", label: "Payment due" },
  { value: "expiring", label: "Expiring" },
] as const;

const pkr = (value: string | number) => `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

const inputClass =
  "mt-1 h-11 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

function statusLabel(row: DealerCustomerRow) {
  if (row.status === "ACTIVE") return { text: "Active", cls: "text-emerald-400" };
  if (row.status.startsWith("SUSPENDED")) return { text: "Suspended", cls: "text-red-400" };
  return { text: row.status.replaceAll("_", " ").toLowerCase(), cls: "text-amber-400" };
}

function expiryText(row: DealerCustomerRow) {
  if (row.billing_mode !== "PREPAID" || row.days_to_expiry === null) return null;
  if (row.days_to_expiry < 0) return { text: `Expired ${Math.abs(row.days_to_expiry)}d ago`, cls: "text-red-400" };
  if (row.days_to_expiry <= 3) return { text: `${row.days_to_expiry}d left`, cls: "text-amber-400" };
  return { text: `${row.days_to_expiry}d left`, cls: "text-slate-500" };
}

type Action = { kind: "collect" | "recharge"; row: DealerCustomerRow } | null;

type Card = { label: string; value: string | number; hint: string; tone?: string };

// Money cards appear only when the summary includes them (employees may not see them).
function summaryCards(summary: DealerSummary): Card[] {
  const cards: Card[] = [
    { label: "Customers", value: summary.total_customers, hint: `${summary.active_connections} active` },
  ];
  if (summary.total_outstanding !== undefined) {
    cards.push({ label: "Due from customers", value: pkr(summary.total_outstanding), hint: `${summary.expiring_in_3_days} expiring in 3 days`, tone: "text-amber-400" });
  }
  if (summary.collected_this_month !== undefined) {
    cards.push({ label: "Collected this month", value: pkr(summary.collected_this_month), hint: `${pkr(summary.collected_by_me_this_month)} by you`, tone: "text-emerald-400" });
  } else {
    cards.push({ label: "Collected by you", value: pkr(summary.collected_by_me_this_month), hint: "This month", tone: "text-emerald-400" });
  }
  if (summary.commission_this_month !== undefined) {
    cards.push({ label: "My commission", value: pkr(summary.commission_this_month), hint: "This month, estimated", tone: "text-blue-400" });
  }
  return cards;
}

export default function DealerHomePage() {
  const me = useDealerMe();
  const [summary, setSummary] = useState<DealerSummary | null>(null);
  const [rows, setRows] = useState<DealerCustomerRow[]>([]);
  const [search, setSearch] = useState("");
  const [show, setShow] = useState<"" | "due" | "expiring">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [action, setAction] = useState<Action>(null);
  const [amount, setAmount] = useState("");
  const [months, setMonths] = useState(1);
  const [method, setMethod] = useState<DealerPaymentMethod>("CASH");
  const [reference, setReference] = useState("");
  const [saving, setSaving] = useState(false);

  const loadSummary = useCallback(async () => {
    try {
      setSummary(await dealerPortalService.getSummary());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load your summary.");
    }
  }, []);

  const loadRows = useCallback(async (query: string, filter: typeof show) => {
    setLoading(true);
    try {
      setRows((await dealerPortalService.getCustomers({ search: query, show: filter })).results);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load your customers.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    const timer = setTimeout(() => void loadRows(search.trim(), show), 300);
    return () => clearTimeout(timer);
  }, [search, show, loadRows]);

  function open(kind: "collect" | "recharge", row: DealerCustomerRow) {
    setAction({ kind, row });
    setAmount(kind === "collect" ? (Number(row.outstanding) > 0 ? row.outstanding : row.monthly_price) : "");
    setMonths(1);
    setMethod("CASH");
    setReference("");
  }

  async function submit() {
    if (!action) return;
    setSaving(true);
    try {
      if (action.kind === "collect") {
        const result = await dealerPortalService.collectPayment(action.row.service_id, {
          amount, payment_method: method, reference,
        });
        toast.success(`Received ${pkr(result.receipt.amount)} from ${action.row.customer_name}. Receipt ${result.receipt.payment_number}.`);
      } else {
        const result = await dealerPortalService.recharge(action.row.service_id, {
          months, payment_method: method, reference,
        });
        toast.success(`${action.row.customer_name} recharged until ${new Date(`${result.new_expiry_date}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}.`);
      }
      setAction(null);
      void loadSummary();
      void loadRows(search.trim(), show);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "That could not be saved. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const amountValid = action?.kind !== "collect" || (Number(amount) >= 1 && Number.isFinite(Number(amount)));
  const rechargeTotal = action?.kind === "recharge" ? Number(action.row.monthly_price) * months : 0;

  return (
    <>
      {summary && (
        <div className="mb-5">
          <p className="text-sm text-slate-400">Assalam o Alaikum,</p>
          <h1 className="text-xl font-bold text-white">{me.is_dealer ? summary.dealer.name : me.name}</h1>
          <p className="text-xs text-slate-500">
            {summary.dealer.dealer_code}
            {me.is_dealer
              ? ` · Commission ${
                  summary.dealer.commission_type === "PERCENTAGE"
                    ? `${Number(summary.dealer.commission_rate)}% of collections`
                    : `${pkr(summary.dealer.commission_rate ?? 0)} per active customer`
                }`
              : ` · Working for ${summary.dealer.name}`}
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            {summaryCards(summary).map((card) => (
              <div key={card.label} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-3.5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{card.label}</p>
                <p className={`mt-1.5 text-lg font-bold ${card.tone ?? "text-white"}`}>{card.value}</p>
                <p className="mt-0.5 text-[11px] text-slate-500">{card.hint}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

      <div className="mb-3 flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, phone or ID"
            className="h-11 w-full rounded-lg border border-[#263142] bg-[#0D1117] pl-9 pr-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div className="flex gap-1.5">
          {FILTERS.map((filter) => (
            <button
              key={filter.value}
              onClick={() => setShow(filter.value)}
              className={`h-11 flex-1 rounded-lg border px-3 text-sm sm:flex-none ${
                show === filter.value ? "border-blue-600 bg-blue-600 font-semibold text-white" : "border-[#263142] text-slate-300 hover:bg-[#121821]"
              }`}
            >
              {filter.label}
            </button>
          ))}
          <button
            onClick={() => { void loadSummary(); void loadRows(search.trim(), show); }}
            aria-label="Refresh"
            className="h-11 rounded-lg border border-[#263142] px-3 text-slate-300 hover:bg-[#121821]"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {loading && rows.length === 0 ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-blue-500" /></div>
      ) : rows.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">No customers here.</div>
      ) : (
        <ul className="space-y-2">
          {rows.map((row) => {
            const st = statusLabel(row);
            const exp = expiryText(row);
            const due = Number(row.outstanding);
            return (
              <li key={row.service_id} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-3.5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-white">{row.customer_name}</p>
                    <p className="text-xs text-slate-500">
                      <a href={`tel:${row.phone}`} className="text-blue-400">{row.phone}</a> · {row.service_number}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {row.package_name} · {row.billing_mode === "PREPAID" ? "Prepaid" : "Monthly"}
                      {row.area ? ` · ${row.area}` : ""}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className={`text-xs font-semibold ${st.cls}`}>{st.text}</p>
                    {exp && <p className={`text-xs ${exp.cls}`}>{exp.text}</p>}
                    <p className={`mt-1 text-sm font-bold ${due > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                      {due > 0 ? `${pkr(due)} due` : "Paid up"}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex gap-2 empty:hidden">
                  {me.rights.can_collect_payments && (
                    <button
                      onClick={() => open("collect", row)}
                      className="flex h-10 flex-1 items-center justify-center gap-1.5 rounded-lg bg-emerald-600 text-sm font-semibold text-white hover:bg-emerald-500"
                    >
                      <Wallet className="h-4 w-4" /> Collect
                    </button>
                  )}
                  {row.billing_mode === "PREPAID" && me.rights.can_recharge && (
                    <button
                      onClick={() => open("recharge", row)}
                      className="flex h-10 flex-1 items-center justify-center gap-1.5 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500"
                    >
                      <Zap className="h-4 w-4" /> Recharge
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {action && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center" onClick={() => !saving && setAction(null)}>
          <div className="w-full max-w-md rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-base font-bold text-white">
              {action.kind === "collect" ? "Collect payment" : "Recharge connection"}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              {action.row.customer_name} · {action.row.service_number}
              {Number(action.row.outstanding) > 0 && ` · ${pkr(action.row.outstanding)} due`}
            </p>

            {action.kind === "collect" ? (
              <label className="mt-4 block text-xs text-slate-400">
                Amount received (PKR)
                <input type="number" min="1" inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} className={inputClass} />
              </label>
            ) : (
              <label className="mt-4 block text-xs text-slate-400">
                Months
                <select value={months} onChange={(e) => setMonths(Number(e.target.value))} className={inputClass}>
                  {[1, 2, 3, 6, 12].map((m) => <option key={m} value={m}>{m} month{m > 1 ? "s" : ""} · {pkr(Number(action.row.monthly_price) * m)}</option>)}
                </select>
              </label>
            )}

            <label className="mt-3 block text-xs text-slate-400">
              Received as
              <select value={method} onChange={(e) => setMethod(e.target.value as DealerPaymentMethod)} className={inputClass}>
                {METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </label>
            {method !== "CASH" && (
              <label className="mt-3 block text-xs text-slate-400">
                Transaction ID
                <input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Optional" className={inputClass} />
              </label>
            )}

            {action.kind === "recharge" && (
              <p className="mt-3 text-sm text-slate-300">Collect <span className="font-bold text-white">{pkr(rechargeTotal)}</span> from the customer.</p>
            )}

            <div className="mt-5 flex gap-2">
              <button onClick={() => setAction(null)} disabled={saving} className="h-11 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">
                Cancel
              </button>
              <button
                onClick={() => void submit()}
                disabled={saving || !amountValid}
                className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-emerald-600 text-sm font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-500"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                {action.kind === "collect" ? `Confirm ${amount ? pkr(amount) : ""}` : "Confirm Recharge"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
