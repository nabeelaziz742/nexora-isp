"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerAccountsOverview } from "@/services/dealer-portal.service";

const pkr = (value: string | number) =>
  `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function DealerAccountsPage() {
  const me = useDealerMe();
  const allowed = me.is_dealer || me.rights.can_view_accounts;
  const [month, setMonth] = useState(currentMonth);
  const [data, setData] = useState<DealerAccountsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (m: string) => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setData(await dealerPortalService.getAccounts(m));
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load accounts summary.");
    } finally {
      setLoading(false);
    }
  }, [allowed]);

  useEffect(() => {
    void load(month);
  }, [load, month]);

  if (!allowed) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
        You do not have permission to view Accounts.
      </div>
    );
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Accounts</h1>
          <p className="text-sm text-slate-400">
            Money collected, commission, payouts from the ISP, cash with employees, and approved expenses.
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

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
        </div>
      ) : data ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Collected ({data.month})
              </p>
              <p className="mt-1 text-xl font-bold text-emerald-400">{pkr(data.collected_this_month)}</p>
            </div>

            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Commission ({data.month})
              </p>
              {data.is_sub_dealer ? (
                <p className="mt-1.5 text-sm font-medium text-slate-300">{data.commission_note}</p>
              ) : (
                <p className="mt-1 text-xl font-bold text-blue-400">{pkr(data.commission_earned)}</p>
              )}
            </div>

            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                ISP Payouts Received
              </p>
              <p className="mt-1 text-xl font-bold text-white">{pkr(data.payouts_received_this_month)}</p>
              <p className="mt-0.5 text-xs text-slate-500">All time: {pkr(data.payouts_received_total)}</p>
            </div>

            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Cash Held by Employees
              </p>
              <p className="mt-1 text-xl font-bold text-amber-400">{pkr(data.employee_cash_in_hand_total)}</p>
            </div>

            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Approved Expenses ({data.month})
              </p>
              <p className="mt-1 text-xl font-bold text-red-400">{pkr(data.approved_expenses_this_month)}</p>
              {data.pending_expenses_count > 0 && (
                <p className="mt-0.5 text-xs text-slate-500">{data.pending_expenses_count} pending with ISP</p>
              )}
            </div>

            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Manual Journal ({data.month})
              </p>
              <p className="mt-1 text-sm text-emerald-400">Income: {pkr(data.manual_income_this_month)}</p>
              <p className="text-sm text-red-400">Expense: {pkr(data.manual_expense_this_month)}</p>
            </div>
          </div>

          {data.employee_cash_breakdown.length > 0 && (
            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Cash with Employees
              </h2>
              <ul className="divide-y divide-[#1C2431]">
                {data.employee_cash_breakdown.map((emp) => (
                  <li key={emp.employee_id} className="flex justify-between py-2 text-sm">
                    <span className="text-slate-300">{emp.name}</span>
                    <span className="font-semibold text-white">{pkr(emp.cash_in_hand)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Recent ISP Payout Settlements
            </h2>
            {data.recent_settlements.length === 0 ? (
              <p className="text-sm text-slate-500">No payouts recorded by the ISP yet.</p>
            ) : (
              <ul className="divide-y divide-[#1C2431]">
                {data.recent_settlements.map((s) => (
                  <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
                    <div>
                      <p className="font-medium text-white">{s.settlement_number}</p>
                      <p className="text-xs text-slate-500">
                        Paid {s.settlement_date} · Period {s.period_start} to {s.period_end}
                        {s.notes ? ` · ${s.notes}` : ""}
                      </p>
                    </div>
                    <span className="font-semibold text-emerald-400">{pkr(s.amount)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </>
  );
}
