"use client";

import { useCallback, useEffect, useState } from "react";
import { Bike, Loader2, Plus, Receipt, Utensils, X } from "lucide-react";
import { toast } from "sonner";

import ExpenseStatusBadge, { pkr, shortDate } from "@/components/dealers/ExpenseStatusBadge";
import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerExpense, type ExpenseCategory } from "@/services/dealer-portal.service";

const CATEGORIES: { value: ExpenseCategory; label: string; icon: typeof Bike }[] = [
  { value: "BIKE", label: "Bike repair / fuel", icon: Bike },
  { value: "FOOD", label: "Food & drinks", icon: Utensils },
  { value: "OTHER", label: "Other", icon: Receipt },
];

const inputClass =
  "mt-1 h-11 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

const today = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};

const emptyForm = () => ({ category: "BIKE" as ExpenseCategory, amount: "", spent_on: today(), description: "" });

export default function DealerExpensesPage() {
  const me = useDealerMe();
  const [rows, setRows] = useState<DealerExpense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setRows((await dealerPortalService.getExpenses()).results);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load expenses.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const needsDescription = form.category === "OTHER";
  const canSend =
    Number(form.amount) >= 1 && form.spent_on && (!needsDescription || form.description.trim()) && !saving;

  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!canSend) return;
    setSaving(true);
    try {
      const row = await dealerPortalService.requestExpense({ ...form, description: form.description.trim() });
      setRows((current) => [row, ...current]);
      setForm(emptyForm());
      setAdding(false);
      toast.success(`Request for ${pkr(row.amount)} sent to the ISP.`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "That could not be sent. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Expenses</h1>
          <p className="text-sm text-slate-400">
            {me.is_dealer
              ? "Money your employees spent on the job. The ISP approves or rejects each request."
              : "Spent money on the job? Send a request. If the ISP approves it, it comes off your cash in hand."}
          </p>
        </div>
        {!me.is_dealer && !adding && (
          <button
            onClick={() => setAdding(true)}
            className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500"
          >
            <Plus className="h-4 w-4" /> New request
          </button>
        )}
      </div>

      {adding && (
        <form onSubmit={send} className="mb-4 rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="font-semibold text-white">New expense request</p>
            <button type="button" onClick={() => setAdding(false)} className="text-slate-500 hover:text-white" aria-label="Close">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {CATEGORIES.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => setForm((f) => ({ ...f, category: value }))}
                className={`flex flex-col items-center gap-1 rounded-lg border px-2 py-3 text-xs font-medium ${
                  form.category === value
                    ? "border-blue-500 bg-blue-500/10 text-white"
                    : "border-[#263142] text-slate-400 hover:text-white"
                }`}
              >
                <Icon className="h-5 w-5" />
                {label}
              </button>
            ))}
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="text-xs text-slate-400">
              Amount (PKR) *
              <input
                type="number"
                inputMode="numeric"
                min={1}
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                className={inputClass}
                placeholder="e.g. 800"
              />
            </label>
            <label className="text-xs text-slate-400">
              Date *
              <input
                type="date"
                max={today()}
                value={form.spent_on}
                onChange={(e) => setForm((f) => ({ ...f, spent_on: e.target.value }))}
                className={inputClass}
              />
            </label>
          </div>
          <label className="mt-3 block text-xs text-slate-400">
            Details{needsDescription ? " *" : ""}
            <input
              value={form.description}
              maxLength={255}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              className={inputClass}
              placeholder={needsDescription ? "What was the money spent on?" : "e.g. Puncture repair at Model Town"}
            />
          </label>
          <button
            type="submit"
            disabled={!canSend}
            className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Send to ISP
          </button>
        </form>
      )}

      {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-blue-500" /></div>
      ) : rows.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">
          No expense requests yet.
        </div>
      ) : (
        <ul className="divide-y divide-[#1C2431] rounded-xl border border-[#1C2431] bg-[#0D1117]">
          {rows.map((row) => (
            <li key={row.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">
                    {row.category_label}
                    {me.is_dealer && <span className="text-slate-500"> · {row.employee_name}</span>}
                  </p>
                  <p className="text-xs text-slate-500">
                    {shortDate(row.spent_on)}
                    {row.description && ` · ${row.description}`}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-sm font-bold text-white">{pkr(row.amount)}</p>
                  <ExpenseStatusBadge status={row.status} />
                </div>
              </div>
              {row.status !== "PENDING" && (
                <p className={`mt-1.5 text-xs ${row.status === "APPROVED" ? "text-emerald-400/80" : "text-red-400/80"}`}>
                  {row.status === "APPROVED" ? "Approved" : "Rejected"}
                  {row.reviewed_by && ` by ${row.reviewed_by}`}
                  {row.reviewed_at && ` on ${shortDate(row.reviewed_at)}`}
                  {row.review_note && ` — "${row.review_note}"`}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
