"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Loader2, RefreshCw } from "lucide-react";

import {
  ErrorBanner,
  PageHeader,
  StatusBadge,
  daysLeftLabel,
  formatDate,
  formatPKR,
  useSuperAdminErrorHandler,
} from "@/components/superadmin/ui";
import { getPlatformDashboard, type PlatformDashboard } from "@/services/onboarding.service";

function Stat({ label, value, hint, tone = "text-white", href }: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: string;
  href?: string;
}) {
  const body = (
    <div className="h-full rounded-xl border border-[#1C2431] bg-[#0D1117] p-4 transition hover:border-[#263142]">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-bold ${tone}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

export default function SuperAdminDashboardPage() {
  const [data, setData] = useState<PlatformDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const handleError = useSuperAdminErrorHandler(setError);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await getPlatformDashboard());
      setError("");
    } catch (err) {
      handleError(err, "Unable to load the platform dashboard.");
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <PageHeader
        title="Platform Dashboard"
        subtitle="Every ISP on Nexora at a glance."
        action={
          <button
            onClick={() => void load()}
            className="flex h-9 items-center gap-2 rounded-lg border border-[#263142] px-3 text-sm text-slate-300 hover:bg-[#121821]"
          >
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
        }
      />
      <ErrorBanner message={error} />

      {loading && !data ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
        </div>
      ) : data ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Registered ISPs" value={data.total_isps} hint={`${data.new_isps_this_month} joined this month`} href="/superadmin/isps" />
            <Stat label="Active ISPs" value={data.active_isps} tone="text-emerald-400" href="/superadmin/isps?status=ACTIVE" />
            <Stat label="Suspended ISPs" value={data.suspended_isps} tone="text-red-400" href="/superadmin/isps?status=SUSPENDED" />
            <Stat label="Awaiting Verification" value={data.pending_verification} hint={`${data.pending_payment} have not paid yet`} tone="text-blue-400" href="/superadmin/verifications" />
            <Stat label="Monthly Recurring Revenue" value={formatPKR(data.monthly_recurring_revenue)} hint="Sum of active ISPs' monthly fees" />
            <Stat label="Collected This Month" value={formatPKR(data.collected_this_month)} tone="text-emerald-400" />
            <Stat label="Expiring in 7 Days" value={data.expiring_soon} tone="text-amber-400" href="/superadmin/subscriptions?view=expiring" />
            <Stat label="Overdue" value={data.overdue} hint={`Locked after ${data.grace_days} days`} tone="text-orange-400" href="/superadmin/subscriptions?view=expired" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Stat label="Customers across all ISPs" value={data.total_customers.toLocaleString()} />
            <Stat label="Active connections" value={data.total_active_services.toLocaleString()} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-xl border border-[#1C2431] bg-[#0D1117]">
              <div className="flex items-center justify-between border-b border-[#1C2431] px-4 py-3">
                <h2 className="text-sm font-semibold text-white">Needs attention</h2>
                <Link href="/superadmin/subscriptions" className="flex items-center gap-1 text-xs text-blue-400">
                  Subscriptions <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
              {data.attention.length === 0 ? (
                <p className="p-6 text-center text-sm text-slate-500">No subscriptions due or overdue.</p>
              ) : (
                <ul className="divide-y divide-[#1C2431]">
                  {data.attention.map((isp) => (
                    <li key={isp.id}>
                      <Link href={`/superadmin/isps/${isp.id}`} className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-[#121821]">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-slate-200">{isp.name}</p>
                          <p className="text-xs text-slate-500">{isp.code} · {daysLeftLabel(isp.days_left)}</p>
                        </div>
                        <StatusBadge status={isp.status} />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-xl border border-[#1C2431] bg-[#0D1117]">
              <div className="flex items-center justify-between border-b border-[#1C2431] px-4 py-3">
                <h2 className="text-sm font-semibold text-white">Recently joined</h2>
                <Link href="/superadmin/isps" className="flex items-center gap-1 text-xs text-blue-400">
                  All ISPs <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
              {data.recent_isps.length === 0 ? (
                <p className="p-6 text-center text-sm text-slate-500">No ISPs yet.</p>
              ) : (
                <ul className="divide-y divide-[#1C2431]">
                  {data.recent_isps.map((isp) => (
                    <li key={isp.id}>
                      <Link href={`/superadmin/isps/${isp.id}`} className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-[#121821]">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-slate-200">{isp.name}</p>
                          <p className="text-xs text-slate-500">
                            {isp.city || "—"} · {isp.customer_count} customers · joined {formatDate(isp.joined_at)}
                          </p>
                        </div>
                        <StatusBadge status={isp.status} />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      ) : null}
    </>
  );
}
