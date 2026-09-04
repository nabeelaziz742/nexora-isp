"use client";

import { useEffect, useState } from "react";

import AIDailyBriefing from "@/components/command-center/AIDailyBriefing";
import ActiveIncidents from "@/components/command-center/ActiveIncidents";
import ISPHealthScore from "@/components/command-center/ISPHealthScore";
import MetricCard from "@/components/command-center/MetricCard";
import RecentActivity from "@/components/command-center/RecentActivity";

import { commandCenterService } from "@/services/command-center-service";
import {
  CommandCenterSummary,
  CommandMetric,
} from "@/types/command-center";

export default function CommandCenterPage() {
  const [summary, setSummary] =
    useState<CommandCenterSummary | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(
    null,
  );

  useEffect(() => {
    async function loadDashboard() {
      try {
        setError(null);

        const data =
          await commandCenterService.getSummary();

        setSummary(data);
      } catch (error) {
        console.error(
          "Failed to load Command Center summary:",
          error,
        );

        setError(
          "Unable to load Command Center metrics.",
        );
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  const metrics: CommandMetric[] = summary
    ? [
        {
          label: "Total Customers",
          value: summary.total_customers,
          tone: "primary",
          helper: "Registered subscriber directory",
          href: "/customers",
        },
        {
          label: "Active Services",
          value: summary.active_services,
          tone: "success",
          helper: "Currently provisioned active services",
          href: "/customers",
        },
        {
          label: "Outstanding Bills",
          value: summary.outstanding_amount,
          tone: "warning",
          helper: "Overdue accounts & receivables",
          href: "/defaulters",
        },
        {
          label: "Active Incidents",
          value: summary.active_incidents,
          tone: "danger",
          helper: "NOC incidents & fiber alerts",
          href: "/support",
        },
        {
          label: "Open Tickets",
          value: summary.open_complaints,
          tone: "warning",
          helper: "Open customer support complaints",
          href: "/support",
        },
        {
          label: "Work Orders",
          value: summary.open_work_orders,
          tone: "primary",
          helper: "Active technician field dispatches",
          href: "/field-operations",
        },
        {
          label: "Provisioning",
          value: summary.pending_provisioning_requests,
          tone: "intelligence",
          helper: "Network queues & node requests",
          href: "/network",
        },
        {
          label: "Notifications",
          value: summary.failed_notifications,
          tone: "danger",
          helper: "Failed message delivery operations",
          href: "/notifications",
        },
      ]
    : [];

  return (
    <div className="mx-auto w-full max-w-[1600px] px-8 py-7">
      <div className="flex items-end justify-between gap-6">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-blue-400">
            Command
          </p>

          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">
            Command Center
          </h2>

          <p className="mt-1.5 text-sm text-[var(--text-secondary)]">
            Real-time operational intelligence across
            your ISP network.
          </p>
        </div>

        <div className="hidden text-right md:block">
          <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--text-muted)]">
            Last synchronized
          </p>

          <p className="mt-1 text-[11px] font-medium text-green-400">
            Live · 12 seconds ago
          </p>
        </div>
      </div>

      <div className="mt-7">
        {error ? (
          <div className="border border-red-500/20 bg-red-500/10 px-5 py-4">
            <p className="text-sm font-medium text-red-400">
              {error}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {loading
              ? Array.from({ length: 8 }).map(
                  (_, index) => (
                    <div
                      key={index}
                      className="h-[128px] animate-pulse border border-[var(--border)] bg-[var(--surface)]"
                    />
                  ),
                )
              : metrics.map((metric) => (
                  <MetricCard
                    key={metric.label}
                    metric={metric}
                  />
                ))}
          </div>
        )}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
        {loading ? (
          <div className="min-h-[280px] animate-pulse border border-[var(--border)] bg-[var(--surface)]" />
        ) : summary ? (
          <ISPHealthScore
            score={summary.operational_health_score}
          />
        ) : null}

        <AIDailyBriefing />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <ActiveIncidents />

        <RecentActivity />
      </div>
    </div>
  );
}