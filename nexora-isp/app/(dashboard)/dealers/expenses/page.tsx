"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Loader2, RefreshCw, X } from "lucide-react";
import { toast } from "sonner";

import ExpenseStatusBadge, { pkr, shortDate } from "@/components/dealers/ExpenseStatusBadge";
import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerExpense, type ExpenseStatus } from "@/services/dealer-portal.service";

const TABS: { value: "" | ExpenseStatus; label: string }[] = [
  { value: "PENDING", label: "Pending" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
  { value: "", label: "All" },
];

// The ISP decides on expenses that dealers' employees paid on the job.
// Approving one takes it off that employee's cash in hand.
export default function DealerExpensesPage() {
  const [tab, setTab] = useState<"" | ExpenseStatus>("PENDING");
  const [rows, setRows] = useState<DealerExpense[]>([]);
  const [counts, setCounts] = useState<Record<ExpenseStatus, number> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async (status: "" | ExpenseStatus) => {
    setLoading(true);
    try {
      const data = await dealerPortalService.getOfficeExpenses(status);
      setRows(data.results);
      setCounts(data.counts);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load expense requests.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(tab);
  }, [tab, load]);

  async function decide(row: DealerExpense, decision: "APPROVE" | "REJECT") {
    let note = "";
    if (decision === "APPROVE") {
      if (!window.confirm(`Approve ${pkr(row.amount)} for ${row.employee_name}? It will come off their cash in hand.`)) return;
    } else {
      const reason = window.prompt(`Reject ${pkr(row.amount)} for ${row.employee_name}? Reason (optional):`, "");
      if (reason === null) return;
      note = reason;
    }
    setBusy(row.id);
    try {
      await dealerPortalService.reviewExpense(row.id, decision, note);
      toast.success(decision === "APPROVE" ? "Expense approved." : "Expense rejected.");
      await load(tab);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "That could not be saved. Please try again.");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link href="/dealers" className="mb-2 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white">
            <ArrowLeft className="h-3.5 w-3.5" /> Dealers
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-white">Employee Expenses</h1>
          <p className="mt-1 text-sm text-slate-400">
            Requests from dealers&apos; employees. Approved amounts come off the employee&apos;s cash in hand.
          </p>
        </div>
        <button
          onClick={() => load(tab)}
          className="rounded-lg border border-slate-700 bg-slate-800 p-2 text-slate-300 hover:bg-slate-700 hover:text-white"
          aria-label="Refresh"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item.label}
            onClick={() => setTab(item.value)}
            className={`rounded-lg border px-3.5 py-1.5 text-sm font-medium ${
              tab === item.value
                ? "border-blue-500 bg-blue-500/10 text-white"
                : "border-slate-700 text-slate-400 hover:text-white"
            }`}
          >
            {item.label}
            {item.value && counts ? <span className="ml-1.5 text-xs text-slate-500">{counts[item.value]}</span> : null}
          </button>
        ))}
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-blue-500" /></div>
      ) : rows.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-10 text-center text-sm text-slate-500">
          {tab === "PENDING" ? "No requests waiting for a decision." : "Nothing here."}
        </div>
      ) : (
        <ul className="divide-y divide-slate-800 rounded-xl border border-slate-800 bg-slate-900/60">
          {rows.map((row) => (
            <li key={row.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3.5">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-white">
                  {row.employee_name}
                  <span className="ml-2 font-normal text-slate-500">
                    {row.dealer_name} ({row.dealer_code})
                  </span>
                </p>
                <p className="text-xs text-slate-400">
                  {row.category_label} · spent {shortDate(row.spent_on)}
                  {row.description && ` · ${row.description}`}
                </p>
                {row.status !== "PENDING" && (
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {row.status === "APPROVED" ? "Approved" : "Rejected"}
                    {row.reviewed_by && ` by ${row.reviewed_by}`}
                    {row.reviewed_at && ` on ${shortDate(row.reviewed_at)}`}
                    {row.review_note && ` — "${row.review_note}"`}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-base font-bold text-white">{pkr(row.amount)}</span>
                {row.status === "PENDING" ? (
                  <>
                    <button
                      onClick={() => decide(row, "REJECT")}
                      disabled={busy === row.id}
                      className="inline-flex h-9 items-center gap-1 rounded-lg border border-red-500/30 bg-red-500/10 px-3 text-xs font-semibold text-red-400 hover:bg-red-500/20 disabled:opacity-40"
                    >
                      <X className="h-3.5 w-3.5" /> Reject
                    </button>
                    <button
                      onClick={() => decide(row, "APPROVE")}
                      disabled={busy === row.id}
                      className="inline-flex h-9 items-center gap-1 rounded-lg bg-emerald-600 px-3 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
                    >
                      {busy === row.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                      Approve
                    </button>
                  </>
                ) : (
                  <ExpenseStatusBadge status={row.status} />
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
