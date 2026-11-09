"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Loader2, Printer } from "lucide-react";

import { ApiError } from "@/services/api-error";
import { recoveryService, type RecoverySheet } from "@/services/recovery.service";

// Paper-style page on purpose: it looks the same in light and dark mode and
// prints on A4 landscape without the app's sidebar or header.

const AGING = [
  { value: "", label: "All overdue" },
  { value: "0-30", label: "0–30 days" },
  { value: "31-60", label: "31–60 days" },
  { value: "61-90", label: "61–90 days" },
  { value: "90+", label: "90+ days" },
];

const pkr = (value: string | number) => Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 });

function shortDate(value: string | null) {
  if (!value) return "—";
  return new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "2-digit" });
}

export default function RecoverySheetPage() {
  const [filters, setFilters] = useState<{ area: string; aging_bucket: string; officer_id: string } | null>(null);
  const [sheet, setSheet] = useState<RecoverySheet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // The Defaulters page opens this with its current filters in the URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setFilters({
      area: params.get("area") ?? "",
      aging_bucket: params.get("aging_bucket") ?? "",
      officer_id: params.get("officer_id") ?? "",
    });
  }, []);

  const load = useCallback(async (current: { area: string; aging_bucket: string; officer_id: string }) => {
    setLoading(true);
    try {
      setSheet(await recoveryService.getRecoverySheet(current));
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load the recovery sheet.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (filters) void load(filters);
  }, [filters, load]);

  const update = (key: "area" | "aging_bucket" | "officer_id", value: string) =>
    setFilters((current) => (current ? { ...current, [key]: value } : current));

  const selectClass = "h-9 rounded border border-slate-300 bg-white px-2 text-sm text-slate-900";
  // Row numbers run across area groups.
  const groupStarts = (sheet?.groups ?? []).reduce<number[]>(
    (starts, group, index, all) => [...starts, index === 0 ? 0 : starts[index - 1] + all[index - 1].count],
    [],
  );

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 print:bg-white">
      <style>{`@media print { @page { size: A4 landscape; margin: 10mm; } }`}</style>

      <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 border-b border-slate-300 bg-white px-4 py-3 print:hidden">
        <a href="/defaulters" className="mr-2 inline-flex items-center gap-1 text-sm text-blue-700 hover:underline">
          <ArrowLeft className="h-4 w-4" /> Defaulters
        </a>
        <select value={filters?.area ?? ""} onChange={(e) => update("area", e.target.value)} className={selectClass}>
          <option value="">All areas</option>
          {sheet?.areas.map((area) => <option key={area} value={area}>{area}</option>)}
        </select>
        <select value={filters?.aging_bucket ?? ""} onChange={(e) => update("aging_bucket", e.target.value)} className={selectClass}>
          {AGING.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
        </select>
        <select value={filters?.officer_id ?? ""} onChange={(e) => update("officer_id", e.target.value)} className={selectClass}>
          <option value="">All (any officer)</option>
          {sheet?.officers.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
        <button
          onClick={() => window.print()}
          disabled={loading || !sheet || sheet.total_customers === 0}
          className="ml-auto inline-flex h-9 items-center gap-2 rounded bg-blue-700 px-4 text-sm font-semibold text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          <Printer className="h-4 w-4" /> Print
        </button>
      </div>

      <div className="mx-auto max-w-[1400px] bg-white p-6 shadow print:max-w-none print:p-0 print:shadow-none">
        {error && <p className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        {loading && !sheet ? (
          <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-blue-700" /></div>
        ) : sheet ? (
          <>
            <header className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b-2 border-slate-900 pb-3">
              <div>
                <p className="text-xl font-bold">{sheet.organization_name}</p>
                <p className="text-sm font-semibold uppercase tracking-wide">Recovery Sheet</p>
              </div>
              <div className="text-right text-xs leading-5">
                <p>Printed: {new Date(sheet.generated_at).toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}</p>
                <p>Area: <b>{sheet.filters.area || "All"}</b> · Overdue: <b>{AGING.find((a) => a.value === sheet.filters.aging_bucket)?.label ?? "All"}</b></p>
                <p>Officer: <b>{sheet.filters.officer || "________________"}</b></p>
                <p>Customers: <b>{sheet.total_customers}</b> · Total due: <b>PKR {pkr(sheet.total_overdue)}</b></p>
              </div>
            </header>

            {sheet.total_customers === 0 ? (
              <p className="py-12 text-center text-sm text-slate-500">No overdue customers match these filters.</p>
            ) : (
              <table className="w-full border-collapse text-[11px] leading-tight">
                <thead>
                  <tr className="bg-slate-200 text-left">
                    {["#", "Customer", "Phone", "Address", "Package", "Due since", "Amount due", "Last paid", "Promise", "Received", "Remarks / Sign"].map((h) => (
                      <th key={h} className="border border-slate-400 px-1.5 py-1 font-semibold">{h}</th>
                    ))}
                  </tr>
                </thead>
                {sheet.groups.map((group, groupIndex) => (
                  <tbody key={group.area} className="break-inside-avoid-page">
                    <tr className="bg-slate-100">
                      <td colSpan={11} className="border border-slate-400 px-1.5 py-1 font-bold">
                        {group.area} — {group.count} customer{group.count === 1 ? "" : "s"} · PKR {pkr(group.total)}
                      </td>
                    </tr>
                    {group.rows.map((row, rowIndex) => {
                      const serial = groupStarts[groupIndex] + rowIndex + 1;
                      return (
                        <tr key={`${group.area}-${row.customer_number}`} className="break-inside-avoid align-top">
                          <td className="border border-slate-400 px-1.5 py-1.5 text-center">{serial}</td>
                          <td className="border border-slate-400 px-1.5 py-1.5">
                            <b>{row.full_name}</b>
                            <br /><span className="text-slate-600">{row.customer_number} · {row.internet_id}</span>
                          </td>
                          <td className="border border-slate-400 px-1.5 py-1.5 whitespace-nowrap">
                            {row.phone}{row.alternate_phone ? <><br />{row.alternate_phone}</> : null}
                          </td>
                          <td className="border border-slate-400 px-1.5 py-1.5">{row.address}</td>
                          <td className="border border-slate-400 px-1.5 py-1.5">{row.package_name}</td>
                          <td className="border border-slate-400 px-1.5 py-1.5 whitespace-nowrap">
                            {shortDate(row.oldest_due_date)}
                            <br /><span className="text-slate-600">{row.max_days_overdue} days</span>
                          </td>
                          <td className="border border-slate-400 px-1.5 py-1.5 text-right font-bold whitespace-nowrap">{pkr(row.total_overdue)}</td>
                          <td className="border border-slate-400 px-1.5 py-1.5 whitespace-nowrap">
                            {row.last_payment_date ? <>{shortDate(row.last_payment_date)}<br /><span className="text-slate-600">{pkr(row.last_payment_amount ?? 0)}</span></> : "Never"}
                          </td>
                          <td className="border border-slate-400 px-1.5 py-1.5">{row.promise}</td>
                          <td className="w-20 border border-slate-400 px-1.5 py-1.5" />
                          <td className="w-32 border border-slate-400 px-1.5 py-1.5" />
                        </tr>
                      );
                    })}
                  </tbody>
                ))}
              </table>
            )}

            <footer className="mt-8 grid grid-cols-3 gap-8 text-xs">
              <div className="border-t border-slate-900 pt-1">Total collected: PKR ____________</div>
              <div className="border-t border-slate-900 pt-1">Recovery officer signature</div>
              <div className="border-t border-slate-900 pt-1">Checked by (manager)</div>
            </footer>
          </>
        ) : null}
      </div>
    </div>
  );
}
