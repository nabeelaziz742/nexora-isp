"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";

import {
  ErrorBanner,
  PageHeader,
  StatusBadge,
  daysLeftLabel,
  formatDate,
  formatPKR,
  useSuperAdminErrorHandler,
} from "@/components/superadmin/ui";
import { getISPs, type ISPSummary } from "@/services/onboarding.service";

const VIEWS = [
  { value: "expiring", label: "Expiring in 7 days" },
  { value: "expired", label: "Overdue" },
  { value: "untracked", label: "Not tracked" },
  { value: "all", label: "All" },
];

export default function SubscriptionsPage() {
  const [view, setView] = useState<string | null>(null);
  const [items, setItems] = useState<ISPSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const handleError = useSuperAdminErrorHandler(setError);

  // Dashboard cards link here with ?view=...; read it once on mount.
  useEffect(() => {
    const initial = new URLSearchParams(window.location.search).get("view");
    setView(VIEWS.some((v) => v.value === initial) ? initial : "expiring");
  }, []);

  const load = useCallback(
    async (current: string) => {
      setLoading(true);
      try {
        const data = await getISPs({ subscription: current === "all" ? "" : current });
        const rows = current === "all"
          ? data.results
              .filter((isp) => isp.status !== "PENDING" && isp.status !== "REJECTED")
              .sort((a, b) => (a.paid_until ?? "9999").localeCompare(b.paid_until ?? "9999"))
          : data.results;
        setItems(rows);
        setError("");
      } catch (err) {
        handleError(err, "Unable to load subscriptions.");
      } finally {
        setLoading(false);
      }
    },
    [handleError],
  );

  useEffect(() => {
    if (view) void load(view);
  }, [view, load]);

  const totalDue = items.reduce((sum, isp) => sum + Number(isp.monthly_fee || 0), 0);

  return (
    <>
      <PageHeader
        title="Subscriptions & Renewals"
        subtitle="Who pays Nexora when. ISPs unpaid past the grace period are locked automatically every night; recording a payment unlocks them."
      />
      <ErrorBanner message={error} />

      <div className="mb-4 flex flex-wrap gap-2">
        {VIEWS.map((option) => (
          <button
            key={option.value}
            onClick={() => setView(option.value)}
            className={`h-9 rounded-lg border px-3 text-sm ${
              view === option.value
                ? "border-blue-600 bg-blue-600 font-semibold text-white"
                : "border-[#263142] text-slate-300 hover:bg-[#121821]"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-xl border border-[#1C2431] bg-[#0D1117]">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-[#1C2431] text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3">ISP</th>
              <th className="px-4 py-3">Owner</th>
              <th className="px-4 py-3">Monthly fee</th>
              <th className="px-4 py-3">Paid until</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1C2431]">
            {loading ? (
              <tr><td colSpan={6} className="py-12 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin text-blue-500" /></td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={6} className="py-12 text-center text-slate-500">Nothing here right now.</td></tr>
            ) : (
              items.map((isp) => (
                <tr key={isp.id} className="hover:bg-[#121821]">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-200">{isp.name}</p>
                    <p className="text-xs text-slate-500">{isp.code}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-slate-200">{isp.owner_name || "—"}</p>
                    <p className="text-xs text-slate-500">{isp.owner_email}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-200">{formatPKR(isp.monthly_fee)}</td>
                  <td className="px-4 py-3">
                    <p className="text-slate-200">{formatDate(isp.paid_until)}</p>
                    <p className={`text-xs ${isp.days_left !== null && isp.days_left < 0 ? "text-orange-400" : "text-slate-500"}`}>
                      {daysLeftLabel(isp.days_left)}
                    </p>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={isp.status} /></td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/superadmin/isps/${isp.id}`} className="text-sm font-medium text-blue-400 hover:underline">
                      Manage
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {!loading && items.length > 0 && (
        <p className="mt-3 text-xs text-slate-500">
          {items.length} ISP{items.length === 1 ? "" : "s"} · {formatPKR(totalDue)} in monthly fees
        </p>
      )}
    </>
  );
}
