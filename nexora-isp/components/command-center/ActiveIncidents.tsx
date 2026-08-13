"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowUpRight,
} from "lucide-react";

import { commandCenterService } from "@/services/command-center-service";
import { CommandCenterAlert } from "@/types/command-center";

export default function ActiveIncidents() {
  const [alerts, setAlerts] = useState<CommandCenterAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAlerts() {
      try {
        setError(null);

        const data = await commandCenterService.getAlerts();

        setAlerts(data);
      } catch (error) {
        console.error(
          "Failed to load Command Center alerts:",
          error,
        );

        setError("Unable to load active incidents.");
      } finally {
        setLoading(false);
      }
    }

    loadAlerts();
  }, []);

  return (
    <section className="border border-[var(--border)] bg-[var(--surface)]">
      <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
        <div>
          <h3 className="text-sm font-semibold text-white">
            Active Incidents
          </h3>

          <p className="mt-0.5 text-[10px] text-[var(--text-muted)]">
            Network events currently affecting service
          </p>
        </div>

        <button
          type="button"
          className="text-[11px] font-medium text-blue-400 transition-colors hover:text-blue-300"
        >
          View all
        </button>
      </div>

      {loading ? (
        <div className="space-y-0 divide-y divide-[var(--border)]">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="px-5 py-4"
            >
              <div className="h-16 animate-pulse bg-white/[0.03]" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="px-5 py-8 text-center">
          <p className="text-[11px] text-red-400">
            {error}
          </p>
        </div>
      ) : alerts.length === 0 ? (
        <div className="px-5 py-10 text-center">
          <div className="mx-auto flex size-9 items-center justify-center rounded-md border border-green-500/20 bg-green-500/10">
            <AlertTriangle className="size-4 text-green-400" />
          </div>

          <p className="mt-3 text-[12px] font-semibold text-white">
            No active incidents
          </p>

          <p className="mt-1 text-[10px] text-[var(--text-muted)]">
            No operational alerts are currently active.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-[var(--border)]">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="px-5 py-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex min-w-0 gap-3">
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-md border border-red-500/20 bg-red-500/10">
                    <AlertTriangle className="size-4 text-red-400" />
                  </div>

                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-[12px] font-semibold text-white">
                        {alert.title}
                      </p>

                      <span className="border border-red-500/20 bg-red-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-red-400">
                        {alert.severity}
                      </span>
                    </div>

                    <p className="mt-1 text-[10px] text-[var(--text-secondary)]">
                      {new Date(
                        alert.created_at,
                      ).toLocaleString()}
                    </p>
                  </div>
                </div>

                <ArrowUpRight className="size-4 shrink-0 text-[var(--text-muted)]" />
              </div>

              <div className="mt-4 flex items-center pl-11">
                <span className="ml-auto text-[9px] font-medium text-[var(--text-muted)]">
                  {alert.id}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}