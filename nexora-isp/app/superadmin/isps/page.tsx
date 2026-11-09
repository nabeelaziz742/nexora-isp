"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Search } from "lucide-react";

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

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "ACTIVE", label: "Active" },
  { value: "EXPIRING", label: "Expiring soon" },
  { value: "OVERDUE", label: "Overdue" },
  { value: "SUSPENDED", label: "Suspended" },
  { value: "PENDING", label: "Pending approval" },
  { value: "REJECTED", label: "Rejected" },
];

export default function AllISPsPage() {
  const [items, setItems] = useState<ISPSummary[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const handleError = useSuperAdminErrorHandler(setError);

  // Dashboard cards link here with ?status=...; read it once on mount.
  useEffect(() => {
    setStatus(new URLSearchParams(window.location.search).get("status") ?? "");
  }, []);

  const load = useCallback(
    async (query: string, statusFilter: string) => {
      setLoading(true);
      try {
        setItems((await getISPs({ search: query, status: statusFilter })).results);
        setError("");
      } catch (err) {
        handleError(err, "Unable to load ISPs.");
      } finally {
        setLoading(false);
      }
    },
    [handleError],
  );

  useEffect(() => {
    if (status === null) return;
    const timer = setTimeout(() => void load(search.trim(), status), 300);
    return () => clearTimeout(timer);
  }, [search, status, load]);

  return (
    <>
      <PageHeader title="All ISPs" subtitle="Every organization on the platform, with its size and subscription." />
      <ErrorBanner message={error} />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by name, code or city"
            className="h-10 w-full rounded-lg border border-[#263142] bg-[#0D1117] pl-9 pr-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <select
          value={status ?? ""}
          onChange={(event) => setStatus(event.target.value)}
          className="h-10 rounded-lg border border-[#263142] bg-[#0D1117] px-3 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-[#1C2431] bg-[#0D1117]">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="border-b border-[#1C2431] text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3">ISP</th>
              <th className="px-4 py-3">Owner</th>
              <th className="px-4 py-3 text-right">Customers</th>
              <th className="px-4 py-3 text-right">Active</th>
              <th className="px-4 py-3 text-right">Staff</th>
              <th className="px-4 py-3">Fee / Paid until</th>
              <th className="px-4 py-3">Joined</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1C2431]">
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center">
                  <Loader2 className="mx-auto h-5 w-5 animate-spin text-blue-500" />
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-500">No ISPs match these filters.</td>
              </tr>
            ) : (
              items.map((isp) => (
                <tr key={isp.id} className="hover:bg-[#121821]">
                  <td className="px-4 py-3">
                    <Link href={`/superadmin/isps/${isp.id}`} className="font-medium text-blue-400 hover:underline">
                      {isp.name}
                    </Link>
                    <p className="text-xs text-slate-500">{isp.code}{isp.city ? ` · ${isp.city}` : ""}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-slate-200">{isp.owner_name || "—"}</p>
                    <p className="text-xs text-slate-500">{isp.owner_email}</p>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-200">{isp.customer_count}</td>
                  <td className="px-4 py-3 text-right text-slate-200">{isp.active_service_count}</td>
                  <td className="px-4 py-3 text-right text-slate-200">{isp.staff_count}</td>
                  <td className="px-4 py-3">
                    <p className="text-slate-200">{formatPKR(isp.monthly_fee)}/mo</p>
                    <p className="text-xs text-slate-500">
                      {isp.paid_until ? `${formatDate(isp.paid_until)} · ${daysLeftLabel(isp.days_left)}` : "Not tracked"}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{formatDate(isp.joined_at)}</td>
                  <td className="px-4 py-3"><StatusBadge status={isp.status} /></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-slate-500">
        Customer counts only. Nexora staff never see an ISP&apos;s customer records.
      </p>
    </>
  );
}
