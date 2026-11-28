"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, RotateCcw, X } from "lucide-react";
import { toast } from "sonner";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerCollectionRow, type DealerCollections } from "@/services/dealer-portal.service";

const pkr = (value: string | number) => `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

const METHOD_LABEL: Record<string, string> = {
  CASH: "Cash",
  MOBILE_WALLET: "Wallet",
  BANK_TRANSFER: "Bank",
  CARD: "Card",
  OTHER: "Other",
};

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function DealerCollectionsPage() {
  const me = useDealerMe();
  const [month, setMonth] = useState(currentMonth);
  const [data, setData] = useState<DealerCollections | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reverseRow, setReverseRow] = useState<DealerCollectionRow | null>(null);
  const [reverseReason, setReverseReason] = useState("");
  const [reverseRef, setReverseRef] = useState("");
  const [reversing, setReversing] = useState(false);

  const load = useCallback(async (value: string) => {
    setLoading(true);
    try {
      setData(await dealerPortalService.getCollections(value));
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load collections.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(month);
  }, [month, load]);

  const showAllCollections = me.is_dealer || me.rights.can_view_all_collections || data?.can_view_all_collections;

  async function handleReverse(event: React.FormEvent) {
    event.preventDefault();
    if (!reverseRow || !reverseReason.trim()) return;
    setReversing(true);
    try {
      await dealerPortalService.reversePayment(reverseRow.payment_id, {
        reason: reverseReason.trim(),
        reference: reverseRef.trim(),
      });
      toast.success(`Payment ${reverseRow.payment_number} reversed.`);
      setReverseRow(null);
      setReverseReason("");
      setReverseRef("");
      void load(month);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to reverse payment.");
    } finally {
      setReversing(false);
    }
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Collections</h1>
          <p className="text-sm text-slate-400">
            {me.is_dealer
              ? "Payments from your customers, who collected them, and your commission."
              : showAllCollections
                ? "All dealer customer payments collected this month."
                : "Payments you collected."}
          </p>
        </div>
        <input
          type="month"
          value={month}
          max={currentMonth()}
          onChange={(e) => e.target.value && setMonth(e.target.value)}
          className="h-10 rounded-lg border border-[#263142] bg-[#0D1117] px-3 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
        />
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

      {data && (
        <div className={`mb-4 grid gap-2 ${data.commission !== undefined ? "grid-cols-3" : "grid-cols-2"}`}>
          {[
            { label: showAllCollections ? "Total collected" : "Collected", value: data.total_collected, tone: "text-white" },
            { label: "Collected by you", value: data.collected_by_me, tone: "text-emerald-400" },
            ...(data.commission !== undefined ? [{ label: "Commission", value: data.commission, tone: "text-blue-400" }] : []),
          ].map((card) => (
            <div key={card.label} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{card.label}</p>
              <p className={`mt-1 text-base font-bold sm:text-lg ${card.tone}`}>{pkr(card.value)}</p>
            </div>
          ))}
        </div>
      )}

      {data && showAllCollections && data.by_person.length > 1 && (
        <div className="mb-4 rounded-xl border border-[#1C2431] bg-[#0D1117] p-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Collected by</p>
          <ul className="space-y-1">
            {data.by_person.map((person) => (
              <li key={person.name} className="flex justify-between text-sm">
                <span className="text-slate-300">{person.name}</span>
                <span className="font-semibold text-white">{pkr(person.total)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-blue-500" /></div>
      ) : !data || data.results.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">
          No payments in this month.
        </div>
      ) : (
        <ul className="divide-y divide-[#1C2431] rounded-xl border border-[#1C2431] bg-[#0D1117]">
          {data.results.map((row) => (
            <li key={row.payment_id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="truncate text-sm font-medium text-slate-200">{row.customer_name}</p>
                  {row.is_reversed && (
                    <span className="rounded bg-red-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-red-400">
                      Reversed
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500">
                  {row.paid_at ? new Date(row.paid_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) : "—"}
                  {" · "}{METHOD_LABEL[row.payment_method] ?? row.payment_method}
                  {" · "}{row.payment_number}
                  {row.collected_by_me ? " · by you" : ` · by ${row.collected_by}`}
                </p>
                {row.is_reversed && row.reversal_reason && (
                  <p className="mt-0.5 text-[11px] text-red-400/90">Reason: {row.reversal_reason}</p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <p className={`text-sm font-bold ${row.is_reversed ? "text-slate-500 line-through" : "text-emerald-400"}`}>
                  {pkr(row.amount)}
                </p>
                {row.can_reverse && (
                  <button
                    type="button"
                    onClick={() => {
                      setReverseRow(row);
                      setReverseReason("");
                      setReverseRef("");
                    }}
                    className="inline-flex h-8 items-center gap-1 rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 text-xs font-medium text-red-300 hover:bg-red-500/20"
                  >
                    <RotateCcw className="h-3.5 w-3.5" /> Reverse
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-xs text-slate-500">Reversed payments are struck through and not counted. Payments within the last 7 days can be reversed with permission.</p>

      {reverseRow && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center"
          onClick={() => !reversing && setReverseRow(null)}
        >
          <form
            onSubmit={handleReverse}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">Reverse payment</h2>
              <button type="button" onClick={() => setReverseRow(null)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-1 text-sm text-slate-400">
              {reverseRow.customer_name} · {reverseRow.payment_number} · {pkr(reverseRow.amount)}
            </p>
            <label className="mt-4 block text-xs text-slate-400">
              Reason *
              <textarea
                rows={3}
                value={reverseReason}
                onChange={(e) => setReverseReason(e.target.value)}
                placeholder="e.g. Wrong customer selected or duplicate entry"
                className="mt-1 w-full rounded-lg border border-[#263142] bg-[#070B12] p-2.5 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </label>
            <label className="mt-3 block text-xs text-slate-400">
              Reference (optional)
              <input
                value={reverseRef}
                onChange={(e) => setReverseRef(e.target.value)}
                className="mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070B12] px-3 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </label>
            <div className="mt-5 flex gap-2">
              <button
                type="button"
                onClick={() => setReverseRow(null)}
                disabled={reversing}
                className="h-10 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={reversing || !reverseReason.trim()}
                className="flex h-10 flex-1 items-center justify-center gap-2 rounded-lg bg-red-600 text-sm font-semibold text-white hover:bg-red-500 disabled:cursor-not-allowed disabled:bg-slate-600"
              >
                {reversing && <Loader2 className="h-4 w-4 animate-spin" />}
                Confirm Reverse
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
