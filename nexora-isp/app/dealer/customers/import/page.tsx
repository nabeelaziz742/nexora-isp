"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Loader2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import type { ImportBatch, ImportPreview } from "@/services/customer-import.service";
import { dealerPortalService } from "@/services/dealer-portal.service";

function saveBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

function csvCell(value: string) {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
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

export default function DealerCustomerImportPage() {
  const me = useDealerMe();
  const canImport = me.is_dealer || me.rights.can_import_customers;

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [checking, setChecking] = useState(false);
  const [importing, setImporting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [result, setResult] = useState<ImportBatch | null>(null);
  const [history, setHistory] = useState<ImportBatch[]>([]);
  const [error, setError] = useState("");

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await dealerPortalService.getImportHistory());
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    if (canImport) void loadHistory();
  }, [canImport, loadHistory]);

  if (!canImport) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
        You do not have permission to import customers.
      </div>
    );
  }

  async function downloadTemplate() {
    try {
      setDownloading(true);
      saveBlob(await dealerPortalService.downloadImportTemplate(), "nexora_dealer_customer_import_template.xlsx");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to download the template.");
    } finally {
      setDownloading(false);
    }
  }

  function chooseFile(selected: File | null) {
    setFile(selected);
    setPreview(null);
    setResult(null);
    setError("");
  }

  async function checkFile() {
    if (!file) return;
    try {
      setChecking(true);
      setError("");
      setResult(null);
      setPreview(await dealerPortalService.previewImport(file));
    } catch (err) {
      setPreview(null);
      setError(err instanceof Error ? err.message : "The file could not be checked.");
    } finally {
      setChecking(false);
    }
  }

  async function runImport() {
    if (!file || !preview?.valid_count) return;
    const confirmed = window.confirm(
      `Import ${preview.valid_count} customer(s)?` +
        (preview.invalid_count ? ` ${preview.invalid_count} row(s) with errors will be skipped.` : ""),
    );
    if (!confirmed) return;
    try {
      setImporting(true);
      const batch = await dealerPortalService.runImport(file);
      setResult(batch);
      setPreview(null);
      setFile(null);
      toast.success(`${batch.imported_count} customer(s) imported.`);
      await loadHistory();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setImporting(false);
    }
  }

  function downloadErrorRows() {
    if (!preview) return;
    const bad = preview.rows.filter((row) => !row.valid);
    if (!bad.length) return;
    const keys = Object.keys(bad[0].values);
    const lines = [
      ["row", ...keys, "errors"].join(","),
      ...bad.map((row) =>
        [String(row.row), ...keys.map((key) => row.values[key] ?? ""), row.errors.join(" | ")]
          .map(csvCell)
          .join(","),
      ),
    ];
    saveBlob(new Blob([lines.join("\n")], { type: "text/csv" }), "dealer_customer_import_errors.csv");
  }

  const errorRows = preview?.rows.filter((row) => !row.valid) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/dealer/customers"
          className="mb-3 inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white"
        >
          <ArrowLeft className="size-3.5" />
          Customers
        </Link>
        <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">Import Customers</h1>
        <p className="mt-0.5 text-xs text-slate-400 sm:text-sm">
          Upload existing customers from Excel or CSV. Imported customers become active immediately under your dealer
          account, without changing anything on the router.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-400">Step 1</p>
          <h2 className="mt-1 text-sm font-semibold text-white">Download the template</h2>
          <p className="mt-1 text-xs text-slate-400">
            Includes the columns, an example row, package codes, your areas, and your employee emails.
          </p>
          <button
            type="button"
            onClick={downloadTemplate}
            disabled={downloading}
            className="mt-4 flex h-10 items-center gap-1.5 rounded-lg border border-[#263142] bg-[#070A0F] px-3.5 text-xs font-semibold text-white hover:border-blue-500 disabled:opacity-50"
          >
            {downloading ? <Loader2 className="size-3.5 animate-spin" /> : <Download className="size-3.5" />}
            Download Template (.xlsx)
          </button>
        </div>

        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-400">Step 2</p>
          <h2 className="mt-1 text-sm font-semibold text-white">Upload the filled file</h2>
          <p className="mt-1 text-xs text-slate-400">Excel (.xlsx) or CSV, up to 2,000 customers and 5 MB.</p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <input
              type="file"
              accept=".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
              onChange={(e) => chooseFile(e.target.files?.[0] ?? null)}
              className="block w-full text-xs text-slate-300 file:mr-3 file:rounded-lg file:border file:border-[#263142] file:bg-[#070A0F] file:px-3 file:py-1.5 file:text-xs file:text-slate-200 sm:w-auto"
            />
            <button
              type="button"
              onClick={checkFile}
              disabled={!file || checking}
              className="flex h-10 items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500"
            >
              {checking ? <Loader2 className="size-3.5 animate-spin" /> : <FileSpreadsheet className="size-3.5" />}
              Check File
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          <AlertTriangle className="size-4 shrink-0" />
          {error}
        </div>
      )}

      {preview && (
        <div className="space-y-4 rounded-xl border border-[#1C2431] bg-[#0D1117] p-5">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-400">Step 3</p>
            <h2 className="mt-1 text-sm font-semibold text-white">Review and import</h2>
          </div>

          <div className="grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-[#1C2431] bg-[#1C2431]">
            {[
              { label: "Rows in file", value: preview.total_rows, tone: "text-white" },
              { label: "Ready to import", value: preview.valid_count, tone: "text-emerald-400" },
              { label: "With errors", value: preview.invalid_count, tone: preview.invalid_count ? "text-rose-400" : "text-white" },
            ].map((stat) => (
              <div key={stat.label} className="bg-[#0D1117] p-4">
                <p className="text-[10px] uppercase tracking-wider text-slate-400">{stat.label}</p>
                <p className={`mt-2 text-2xl font-bold ${stat.tone}`}>{stat.value}</p>
              </div>
            ))}
          </div>

          {errorRows.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-rose-500/20">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rose-500/20 bg-rose-500/5 px-4 py-2.5">
                <p className="text-xs font-semibold text-rose-300">
                  These rows will be skipped. Fix them and upload again later.
                </p>
                <button
                  type="button"
                  onClick={downloadErrorRows}
                  className="flex items-center gap-1 text-xs font-semibold text-rose-300 hover:text-rose-200"
                >
                  <Download className="size-3.5" />
                  Download error rows (CSV)
                </button>
              </div>
              <div className="max-h-80 overflow-auto">
                <table className="w-full min-w-[540px] text-left text-xs">
                  <thead className="sticky top-0 bg-[#070A0F] text-[10px] uppercase tracking-wider text-slate-400">
                    <tr>
                      <th className="px-4 py-2">Row</th>
                      <th className="px-4 py-2">Name</th>
                      <th className="px-4 py-2">Phone</th>
                      <th className="px-4 py-2">Problem</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1C2431]">
                    {errorRows.map((row) => (
                      <tr key={row.row}>
                        <td className="px-4 py-2 font-mono text-slate-400">{row.row}</td>
                        <td className="px-4 py-2 text-white">
                          {[row.values.first_name, row.values.last_name].filter(Boolean).join(" ") || "—"}
                        </td>
                        <td className="px-4 py-2 font-mono text-slate-300">{row.values.phone || "—"}</td>
                        <td className="px-4 py-2 text-rose-300">{row.errors.join(" ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="button"
              onClick={runImport}
              disabled={importing || !preview.valid_count}
              className="flex h-10 items-center gap-1.5 rounded-lg bg-emerald-600 px-4 text-xs font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-500"
            >
              {importing ? <Loader2 className="size-3.5 animate-spin" /> : <Upload className="size-3.5" />}
              Import {preview.valid_count} Customer{preview.valid_count === 1 ? "" : "s"}
            </button>
          </div>
        </div>
      )}

      {result && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-5 py-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-5 text-emerald-400" />
            <p className="text-sm text-emerald-200">
              {result.imported_count} of {result.total_rows} customers imported
              {result.skipped_count ? `, ${result.skipped_count} skipped` : ""}.
            </p>
          </div>
          <Link href="/dealer/customers" className="text-xs font-semibold text-emerald-300 hover:text-emerald-200">
            View customers →
          </Link>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-[#1C2431] bg-[#0D1117]">
        <div className="border-b border-[#1C2431] px-5 py-3">
          <h2 className="text-sm font-semibold text-white">Import History</h2>
        </div>
        {history.length === 0 ? (
          <p className="px-5 py-8 text-center text-xs text-slate-500">No imports yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[540px] text-left text-xs">
              <thead className="bg-[#070A0F] text-[10px] uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-5 py-2.5">When</th>
                  <th className="px-5 py-2.5">File</th>
                  <th className="px-5 py-2.5">Imported</th>
                  <th className="px-5 py-2.5">Skipped</th>
                  <th className="px-5 py-2.5">By</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1C2431]">
                {history.map((batch) => (
                  <tr key={batch.id}>
                    <td className="whitespace-nowrap px-5 py-2.5 text-slate-300">{formatDateTime(batch.created_at)}</td>
                    <td className="px-5 py-2.5 text-white">{batch.file_name || "—"}</td>
                    <td className="px-5 py-2.5 font-mono text-emerald-400">
                      {batch.imported_count}/{batch.total_rows}
                    </td>
                    <td className={`px-5 py-2.5 font-mono ${batch.skipped_count ? "text-rose-400" : "text-slate-400"}`}>
                      {batch.skipped_count}
                    </td>
                    <td className="px-5 py-2.5 text-slate-300">{batch.created_by_name || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
