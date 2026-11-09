"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { clearSuperAdminSession } from "@/components/superadmin/SuperAdminShell";
import type { ISPStatus } from "@/services/onboarding.service";

const STATUS_STYLE: Record<ISPStatus, { label: string; className: string }> = {
  ACTIVE: { label: "Active", className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" },
  EXPIRING: { label: "Expiring soon", className: "border-amber-500/30 bg-amber-500/10 text-amber-400" },
  OVERDUE: { label: "Overdue", className: "border-orange-500/30 bg-orange-500/10 text-orange-400" },
  SUSPENDED: { label: "Suspended", className: "border-red-500/30 bg-red-500/10 text-red-400" },
  PENDING: { label: "Pending approval", className: "border-blue-500/30 bg-blue-500/10 text-blue-400" },
  REJECTED: { label: "Rejected", className: "border-slate-600 bg-slate-800 text-slate-400" },
};

export function StatusBadge({ status }: { status: ISPStatus }) {
  const style = STATUS_STYLE[status] ?? STATUS_STYLE.ACTIVE;
  return (
    <span className={`inline-flex whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-semibold ${style.className}`}>
      {style.label}
    </span>
  );
}

export function formatPKR(value: string | number) {
  const amount = typeof value === "string" ? Number(value) : value;
  return `PKR ${Number.isFinite(amount) ? amount.toLocaleString("en-PK", { maximumFractionDigits: 0 }) : value}`;
}

export function formatDate(value: string | null) {
  if (!value) return "—";
  const date = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function daysLeftLabel(daysLeft: number | null) {
  if (daysLeft === null) return "Not tracked";
  if (daysLeft < 0) return `${Math.abs(daysLeft)} day${daysLeft === -1 ? "" : "s"} overdue`;
  if (daysLeft === 0) return "Due today";
  return `${daysLeft} day${daysLeft === 1 ? "" : "s"} left`;
}

// Sends the admin back to login when the session has expired.
export function useSuperAdminErrorHandler(setError: (message: string) => void) {
  const router = useRouter();
  return useCallback(
    (err: unknown, fallback: string) => {
      if ((err as { status?: number })?.status === 401) {
        clearSuperAdminSession();
        router.replace("/superadmin/login");
        return;
      }
      setError(err instanceof Error ? err.message : fallback);
    },
    [router, setError],
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{message}</div>;
}
