"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, Loader2, RefreshCw, RotateCcw, ShieldAlert } from "lucide-react";

import { useToast } from "@/hooks/useToast";
import {
  reportsService,
  type ReversalEventType,
  type ReversalsFilters,
  type ReversalsReport,
} from "@/services/reports.service";

const EVENT_STYLES: Record<ReversalEventType, string> = {
  PAYMENT_REVERSED: "border-rose-500/20 bg-rose-500/10 text-rose-400",
  INVOICE_VOIDED: "border-amber-500/20 bg-amber-500/10 text-amber-400",
  INVOICE_WRITTEN_OFF: "border-violet-500/20 bg-violet-500/10 text-violet-400",
  POS_SALE_CANCELLED: "border-orange-500/20 bg-orange-500/10 text-orange-400",
  CUSTOMER_DEACTIVATED: "border-zinc-500/20 bg-zinc-500/10 text-zinc-300",
};

const EVENT_OPTIONS: { value: ReversalEventType; label: string }[] = [
  { value: "PAYMENT_REVERSED", label: "Payment reversed" },
  { value: "INVOICE_VOIDED", label: "Invoice voided" },
  { value: "INVOICE_WRITTEN_OFF", label: "Written off as bad debt" },
  { value: "POS_SALE_CANCELLED", label: "POS sale cancelled" },
  { value: "CUSTOMER_DEACTIVATED", label: "Customer deactivated" },
];

function formatMoney(value: string | number) {
  const amount = Number(value);
  return `PKR ${(Number.isNaN(amount) ? 0 : amount).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("en-PK", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ReversalsReportPage() {
  const toast = useToast();
  const [filters, setFilters] = useState<ReversalsFilters>({});
  const [report, setReport] = useState<ReversalsReport | null>(null);
  const [staffOptions, setStaffOptions] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const data = await reportsService.getReversalsReport(filters);
      setReport(data);
      if (!filters.actor_id) {
        // Staff list comes from the unfiltered summary so it never narrows itself.
        setStaffOptions(
          data.by_actor
            .filter((row) => row.actor_id)
            .map((row) => ({ id: row.actor_id as string, name: row.actor_name })),
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load the report.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  function updateFilter(key: keyof ReversalsFilters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  async function exportCsv() {
    try {
      setExporting(true);
      const blob = await reportsService.downloadReversalsCsv(filters);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "reversals_report.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[#F8FAFC] sm:text-2xl">
            Reversals &amp; Voids
          </h1>
          <p className="mt-0.5 text-xs text-[#64748B] sm:text-sm">
            Every payment reversed, invoice voided or written off, POS sale cancelled and customer deactivated,
            with who did it and why.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={exportCsv}
            disabled={exporting || !report?.total_count}
            className="flex h-8.5 items-center gap-1.5 rounded-md border border-[#202938] bg-[#111827] px-3 text-xs font-medium text-[#CBD5E1] hover:bg-[#182131] disabled:opacity-50"
          >
            {exporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
            Export CSV
          </button>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="flex h-8.5 items-center gap-1.5 rounded-md border border-[#202938] bg-[#111827] px-3 text-xs font-medium text-[#CBD5E1] hover:bg-[#182131] disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid gap-2 border border-[#202938] bg-[#0D1117] p-4 sm:grid-cols-2 xl:grid-cols-4">
        <label className="text-xs text-[#64748B]">
          From
          <input
            type="date"
            value={filters.start_date ?? ""}
            onChange={(e) => updateFilter("start_date", e.target.value)}
            className="mt-1 h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-xs text-[#CBD5E1] outline-none focus:border-[#3B82F6]"
          />
        </label>
        <label className="text-xs text-[#64748B]">
          To
          <input
            type="date"
            value={filters.end_date ?? ""}
            onChange={(e) => updateFilter("end_date", e.target.value)}
            className="mt-1 h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-xs text-[#CBD5E1] outline-none focus:border-[#3B82F6]"
          />
        </label>
        <label className="text-xs text-[#64748B]">
          Staff
          <select
            value={filters.actor_id ?? ""}
            onChange={(e) => updateFilter("actor_id", e.target.value)}
            className="mt-1 h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-xs text-[#CBD5E1] outline-none focus:border-[#3B82F6]"
          >
            <option value="">All staff</option>
            {staffOptions.map((staff) => (
              <option key={staff.id} value={staff.id}>
                {staff.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-[#64748B]">
          Type
          <select
            value={filters.event_type ?? ""}
            onChange={(e) => updateFilter("event_type", e.target.value)}
            className="mt-1 h-10 w-full border border-[#202938] bg-[#080B10] px-3 text-xs text-[#CBD5E1] outline-none focus:border-[#3B82F6]"
          >
            <option value="">All types</option>
            {EVENT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? (
        <div className="flex items-center gap-2 border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          {error}
        </div>
      ) : null}

      {report && (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <div className="border border-[#202938] bg-[#0D1117] p-4">
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-[#64748B]">Total Events</p>
              <p className="mt-3 text-xl font-semibold text-[#F8FAFC]">{report.total_count}</p>
              <p className="mt-2 text-xs text-[#64748B]">{formatMoney(report.total_amount)} taken off the books</p>
            </div>
            {report.by_type.map((row) => (
              <div key={row.event_type} className="border border-[#202938] bg-[#0D1117] p-4">
                <p className="text-xs font-medium uppercase tracking-[0.12em] text-[#64748B]">{row.event_label}</p>
                <p className="mt-3 text-xl font-semibold text-[#F8FAFC]">{row.count}</p>
                <p className="mt-2 text-xs text-[#64748B]">{formatMoney(row.amount)}</p>
              </div>
            ))}
          </div>

          {report.by_actor.length > 0 && (
            <div className="border border-[#202938] bg-[#0D1117]">
              <div className="border-b border-[#202938] p-4">
                <h2 className="text-sm font-semibold text-[#F8FAFC]">By Staff Member</h2>
                <p className="mt-1 text-xs text-[#64748B]">Highest amount first. Unusual totals are worth a closer look.</p>
              </div>
              <div className="divide-y divide-[#202938]">
                {report.by_actor.map((row) => (
                  <div key={row.actor_id ?? "system"} className="flex items-center justify-between px-4 py-3 text-xs">
                    <span className="font-medium text-[#E2E8F0]">{row.actor_name}</span>
                    <span className="text-[#94A3B8]">
                      {row.count} {row.count === 1 ? "event" : "events"} ·{" "}
                      <span className="font-mono text-[#F8FAFC]">{formatMoney(row.amount)}</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="border border-[#202938] bg-[#0D1117]">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px]">
                <thead>
                  <tr className="border-b border-[#202938] bg-[#0A0E14] text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                    <th className="px-4 py-3">When</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Reference</th>
                    <th className="px-4 py-3">Customer</th>
                    <th className="px-4 py-3 text-right">Amount</th>
                    <th className="px-4 py-3">Reason</th>
                    <th className="px-4 py-3">Done By</th>
                  </tr>
                </thead>
                <tbody>
                  {report.records.map((record) => (
                    <tr key={record.id} className="border-b border-[#202938] last:border-b-0 hover:bg-[#121821]">
                      <td className="whitespace-nowrap px-4 py-3 text-[11px] text-[#94A3B8]">
                        {formatDateTime(record.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 border px-2 py-0.5 text-[10px] font-semibold ${EVENT_STYLES[record.event_type]}`}>
                          <RotateCcw className="h-3 w-3" />
                          {record.event_label}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-[#CBD5E1]">{record.reference || "—"}</td>
                      <td className="px-4 py-3">
                        <p className="text-xs text-[#E2E8F0]">{record.customer_name || "—"}</p>
                        {record.customer_number && (
                          <p className="font-mono text-[10px] text-[#64748B]">{record.customer_number}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-[#F8FAFC]">
                        {Number(record.amount) ? formatMoney(record.amount) : "—"}
                      </td>
                      <td className="max-w-64 px-4 py-3">
                        <span title={record.reason} className="block truncate text-[11px] text-[#94A3B8]">
                          {record.reason || "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-[#E2E8F0]">{record.actor_name}</td>
                    </tr>
                  ))}

                  {!loading && report.records.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-sm text-[#64748B]">
                        Nothing was reversed, voided or deactivated for these filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
