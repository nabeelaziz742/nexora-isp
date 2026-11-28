"use client";

import { useCallback, useEffect, useState } from "react";
import { Ban, FileSpreadsheet, Loader2, Plus, X } from "lucide-react";
import { toast } from "sonner";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerJournalResponse, type DealerJournalRow } from "@/services/dealer-portal.service";

const pkr = (value: string | number) =>
  `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

function todayStr() {
  const dt = new Date();
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const d = String(dt.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function currentMonth() {
  return todayStr().slice(0, 7);
}

const inputClass =
  "mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070B12] px-3 text-sm text-white focus:border-blue-500 focus:outline-none";

export default function DealerJournalPage() {
  const me = useDealerMe();
  const canView = me.is_dealer || me.rights.can_view_journal || me.rights.can_add_journal_entries;
  const canAdd = me.is_dealer || me.rights.can_add_journal_entries;

  const [month, setMonth] = useState(currentMonth);
  const [kindFilter, setKindFilter] = useState<"" | "INCOME" | "EXPENSE">("");
  const [data, setData] = useState<DealerJournalResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  // Add entry modal
  const [addOpen, setAddOpen] = useState(false);
  const [date, setDate] = useState(todayStr);
  const [kind, setKind] = useState<"INCOME" | "EXPENSE">("EXPENSE");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  // Void entry modal
  const [voidRow, setVoidRow] = useState<DealerJournalRow | null>(null);
  const [voidReason, setVoidReason] = useState("");
  const [voiding, setVoiding] = useState(false);

  const load = useCallback(async () => {
    if (!canView) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setData(await dealerPortalService.getJournal({ month, kind: kindFilter }));
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load journal.");
    } finally {
      setLoading(false);
    }
  }, [canView, month, kindFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    if (!amount || Number(amount) <= 0 || !description.trim()) return;
    setSaving(true);
    try {
      await dealerPortalService.addJournalEntry({
        date,
        kind,
        amount,
        description: description.trim(),
      });
      toast.success("Journal entry added.");
      setAddOpen(false);
      setAmount("");
      setDescription("");
      void load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save entry.");
    } finally {
      setSaving(false);
    }
  }

  async function handleVoid(event: React.FormEvent) {
    event.preventDefault();
    if (!voidRow || !voidReason.trim()) return;
    setVoiding(true);
    try {
      await dealerPortalService.voidJournalEntry(voidRow.id, voidReason.trim());
      toast.success("Entry voided.");
      setVoidRow(null);
      setVoidReason("");
      void load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not void entry.");
    } finally {
      setVoiding(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      const blob = await dealerPortalService.exportJournal({ month, kind: kindFilter });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `dealer_journal_${month}.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  if (!canView) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
        You do not have permission to view Journal.
      </div>
    );
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Journal</h1>
          <p className="text-sm text-slate-400">
            Daily cashbook combining customer payments, ISP payouts, approved expenses, and manual entries.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="month"
            value={month}
            max={currentMonth()}
            onChange={(e) => e.target.value && setMonth(e.target.value)}
            className="h-10 rounded-lg border border-[#263142] bg-[#0D1117] px-3 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
          />
          <button
            type="button"
            onClick={() => void handleExport()}
            disabled={exporting}
            className="inline-flex h-10 items-center gap-1.5 rounded-lg border border-[#263142] bg-[#0D1117] px-3 text-xs font-medium text-slate-200 hover:bg-[#161D29]"
          >
            {exporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />}
            Excel
          </button>
          {canAdd && (
            <button
              type="button"
              onClick={() => {
                setDate(todayStr());
                setKind("EXPENSE");
                setAmount("");
                setDescription("");
                setAddOpen(true);
              }}
              className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 text-sm font-semibold text-white hover:bg-blue-500"
            >
              <Plus className="h-4 w-4" /> Add Entry
            </button>
          )}
        </div>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {[
          { value: "", label: "All" },
          { value: "INCOME", label: "Income" },
          { value: "EXPENSE", label: "Expense" },
        ].map((chip) => (
          <button
            key={chip.label}
            type="button"
            onClick={() => setKindFilter(chip.value as "" | "INCOME" | "EXPENSE")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
              kindFilter === chip.value
                ? "bg-blue-600 text-white"
                : "border border-[#1C2431] bg-[#0D1117] text-slate-400 hover:text-white"
            }`}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {data && (
        <div className="mb-4 grid grid-cols-3 gap-2">
          <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Income</p>
            <p className="mt-1 text-base font-bold text-emerald-400">{pkr(data.total_income)}</p>
          </div>
          <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Expense</p>
            <p className="mt-1 text-base font-bold text-red-400">{pkr(data.total_expense)}</p>
          </div>
          <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Net</p>
            <p className="mt-1 text-base font-bold text-white">{pkr(data.net)}</p>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
        </div>
      ) : !data || data.results.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">
          No journal entries in this period.
        </div>
      ) : (
        <ul className="divide-y divide-[#1C2431] rounded-xl border border-[#1C2431] bg-[#0D1117]">
          {data.results.map((row) => (
            <li key={row.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-slate-500">{row.date}</span>
                  <span className="rounded bg-[#111927] px-1.5 py-0.5 text-[10px] font-medium text-slate-300">
                    {row.source_label}
                  </span>
                  {row.is_void && (
                    <span className="rounded bg-red-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-red-400">
                      Void
                    </span>
                  )}
                </div>
                <p className={`mt-1 text-sm font-medium ${row.is_void ? "text-slate-500 line-through" : "text-slate-200"}`}>
                  {row.description}
                </p>
                <p className="text-xs text-slate-500">
                  By {row.recorded_by}
                  {row.is_void && row.void_reason ? ` · Void reason: ${row.void_reason}` : ""}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span
                  className={`text-sm font-bold ${
                    row.is_void
                      ? "text-slate-500 line-through"
                      : row.kind === "INCOME"
                        ? "text-emerald-400"
                        : "text-red-400"
                  }`}
                >
                  {row.kind === "INCOME" ? "+" : "-"}
                  {pkr(row.amount)}
                </span>
                {row.can_void && (
                  <button
                    type="button"
                    onClick={() => {
                      setVoidRow(row);
                      setVoidReason("");
                    }}
                    className="inline-flex h-8 items-center gap-1 rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 text-xs font-medium text-red-300 hover:bg-red-500/20"
                  >
                    <Ban className="h-3.5 w-3.5" /> Void
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {addOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center"
          onClick={() => !saving && setAddOpen(false)}
        >
          <form
            onSubmit={handleAdd}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">Add journal entry</h2>
              <button type="button" onClick={() => setAddOpen(false)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-slate-400">
                Date *
                <input type="date" max={todayStr()} value={date} onChange={(e) => setDate(e.target.value)} className={inputClass} />
              </label>
              <label className="text-xs text-slate-400">
                Type *
                <select value={kind} onChange={(e) => setKind(e.target.value as "INCOME" | "EXPENSE")} className={inputClass}>
                  <option value="EXPENSE">Expense</option>
                  <option value="INCOME">Income</option>
                </select>
              </label>
            </div>
            <label className="mt-3 block text-xs text-slate-400">
              Amount (PKR) *
              <input type="number" min="1" value={amount} onChange={(e) => setAmount(e.target.value)} className={inputClass} />
            </label>
            <label className="mt-3 block text-xs text-slate-400">
              Description *
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. Shop rent or fiber cable reel"
                className={inputClass}
              />
            </label>
            <div className="mt-5 flex gap-2">
              <button type="button" onClick={() => setAddOpen(false)} disabled={saving} className="h-10 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving || !amount || Number(amount) <= 0 || !description.trim()}
                className="flex h-10 flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-600"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                Save Entry
              </button>
            </div>
          </form>
        </div>
      )}

      {voidRow && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center"
          onClick={() => !voiding && setVoidRow(null)}
        >
          <form
            onSubmit={handleVoid}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">Void journal entry</h2>
              <button type="button" onClick={() => setVoidRow(null)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-1 text-sm text-slate-400">
              {voidRow.description} · {pkr(voidRow.amount)}
            </p>
            <label className="mt-4 block text-xs text-slate-400">
              Reason *
              <input
                value={voidReason}
                onChange={(e) => setVoidReason(e.target.value)}
                placeholder="e.g. Entered twice by mistake"
                className={inputClass}
              />
            </label>
            <div className="mt-5 flex gap-2">
              <button type="button" onClick={() => setVoidRow(null)} disabled={voiding} className="h-10 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">
                Cancel
              </button>
              <button
                type="submit"
                disabled={voiding || !voidReason.trim()}
                className="flex h-10 flex-1 items-center justify-center gap-2 rounded-lg bg-red-600 text-sm font-semibold text-white hover:bg-red-500 disabled:cursor-not-allowed disabled:bg-slate-600"
              >
                {voiding && <Loader2 className="h-4 w-4 animate-spin" />}
                Confirm Void
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
