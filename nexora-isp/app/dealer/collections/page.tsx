"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerCollections } from "@/services/dealer-portal.service";

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
  const [month, setMonth] = useState(currentMonth);
  const [data, setData] = useState<DealerCollections | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Collections</h1>
          <p className="text-sm text-slate-400">Payments from your customers, and your commission.</p>
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
        <div className="mb-4 grid grid-cols-3 gap-2">
          {[
            { label: "Total collected", value: data.total_collected, tone: "text-white" },
            { label: "Collected by you", value: data.collected_by_me, tone: "text-emerald-400" },
            { label: "Commission", value: data.commission, tone: "text-blue-400" },
          ].map((card) => (
            <div key={card.label} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{card.label}</p>
              <p className={`mt-1 text-base font-bold sm:text-lg ${card.tone}`}>{pkr(card.value)}</p>
            </div>
          ))}
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
            <li key={row.payment_id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-200">{row.customer_name}</p>
                <p className="text-xs text-slate-500">
                  {row.paid_at ? new Date(row.paid_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) : "—"}
                  {" · "}{METHOD_LABEL[row.payment_method] ?? row.payment_method}
                  {" · "}{row.payment_number}
                  {row.collected_by_me ? " · by you" : " · by office"}
                </p>
              </div>
              <p className={`shrink-0 text-sm font-bold ${row.is_reversed ? "text-slate-500 line-through" : "text-emerald-400"}`}>
                {pkr(row.amount)}
              </p>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-xs text-slate-500">Reversed payments are struck through and not counted.</p>
    </>
  );
}
