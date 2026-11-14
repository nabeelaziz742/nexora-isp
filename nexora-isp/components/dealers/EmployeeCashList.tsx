"use client";

import { useCallback, useEffect, useState } from "react";
import { HandCoins, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/services/api-error";
import type { CashReceivedResult, EmployeeCashTeam } from "@/services/dealer-portal.service";

const pkr = (value: string | number) => `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

export function handoverText(handover: { amount: string; received_by: string; received_by_type: string; created_at: string }) {
  const when = new Date(handover.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  const who = handover.received_by_type === "ISP" ? `ISP office${handover.received_by ? ` (${handover.received_by})` : ""}` : handover.received_by || "Dealer";
  return `${pkr(handover.amount)} handed to ${who} on ${when}`;
}

// Each employee's cash in hand, with a button to mark it received (back to zero).
// Used by the dealer (portal) and by the ISP office (dealer page).
export default function EmployeeCashList({
  load,
  receive,
  receiverLabel,
}: {
  load: () => Promise<EmployeeCashTeam>;
  receive: (employeeId: string) => Promise<CashReceivedResult>;
  receiverLabel: string;
}) {
  const [team, setTeam] = useState<EmployeeCashTeam | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const refresh = useCallback(async () => {
    try {
      setTeam(await load());
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load employees' cash.");
    }
  }, [load]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function markReceived(employeeId: string, name: string, amount: string) {
    if (!window.confirm(`Mark ${pkr(amount)} as received from ${name}? Their cash in hand will go back to zero.`)) return;
    setBusy(employeeId);
    try {
      const result = await receive(employeeId);
      toast.success(`${pkr(result.handover.amount)} received from ${name}.`);
      await refresh();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "That could not be saved. Please try again.");
    } finally {
      setBusy("");
    }
  }

  if (error) {
    return <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>;
  }
  if (!team) {
    return <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin text-blue-500" /></div>;
  }
  if (team.results.length === 0) return null;

  return (
    <section className="rounded-xl border border-[#1C2431] bg-[#0D1117]">
      <div className="flex items-center justify-between gap-3 border-b border-[#1C2431] px-4 py-3">
        <div>
          <p className="flex items-center gap-1.5 text-sm font-semibold text-white">
            <HandCoins className="h-4 w-4 text-amber-400" /> Cash with employees
          </p>
          <p className="text-xs text-slate-500">Money collected from customers and not handed over yet.</p>
        </div>
        <p className="text-right">
          <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Total</span>
          <span className="text-lg font-bold text-amber-400">{pkr(team.total_cash_in_hand)}</span>
        </p>
      </div>
      <ul className="divide-y divide-[#1C2431]">
        {team.results.map((row) => {
          const hasCash = Number(row.cash_in_hand) > 0;
          return (
            <li key={row.employee_id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-200">
                  {row.name}
                  {!row.is_active && <span className="ml-2 text-[11px] text-slate-500">(login off)</span>}
                </p>
                <p className="text-xs text-slate-500">
                  {row.last_handover ? `Last: ${handoverText(row.last_handover)}` : "Nothing handed over yet"}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-sm font-bold ${hasCash ? "text-amber-400" : "text-slate-500"}`}>{pkr(row.cash_in_hand)}</span>
                <button
                  onClick={() => markReceived(row.employee_id, row.name, row.cash_in_hand)}
                  disabled={!hasCash || busy === row.employee_id}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-emerald-600 px-3 text-xs font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {busy === row.employee_id && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  {receiverLabel}
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
