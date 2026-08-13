"use client";

import { useEffect, useState } from "react";
import { Activity, Clock3 } from "lucide-react";

import { commandCenterService } from "@/services/command-center-service";
import { RecentActivityItem } from "@/types/command-center";

export default function RecentActivity() {
  const [activities, setActivities] = useState<
    RecentActivityItem[]
  >([]);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(
    null,
  );

  useEffect(() => {
    async function loadRecentActivity() {
      try {
        setError(null);

        const data =
          await commandCenterService.getRecentActivity();

        setActivities(data);
      } catch (error) {
        console.error(
          "Failed to load Command Center recent activity:",
          error,
        );

        setError("Unable to load recent activity.");
      } finally {
        setLoading(false);
      }
    }

    loadRecentActivity();
  }, []);

  return (
    <section className="border border-[var(--border)] bg-[var(--surface)]">
      <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
        <div>
          <h3 className="text-sm font-semibold text-white">
            Recent Activity
          </h3>

          <p className="mt-0.5 text-[10px] text-[var(--text-muted)]">
            Latest operational activity across your ISP
          </p>
        </div>

        <div className="flex size-8 items-center justify-center rounded-md border border-blue-500/20 bg-blue-500/10">
          <Activity className="size-4 text-blue-400" />
        </div>
      </div>

      {loading ? (
        <div className="divide-y divide-[var(--border)]">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="flex gap-3 px-5 py-4"
            >
              <div className="size-8 shrink-0 animate-pulse bg-white/[0.04]" />

              <div className="flex-1 space-y-2">
                <div className="h-3 w-1/3 animate-pulse bg-white/[0.04]" />

                <div className="h-3 w-2/3 animate-pulse bg-white/[0.04]" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="px-5 py-10 text-center">
          <p className="text-[11px] text-red-400">
            {error}
          </p>
        </div>
      ) : activities.length === 0 ? (
        <div className="px-5 py-10 text-center">
          <div className="mx-auto flex size-9 items-center justify-center rounded-md border border-blue-500/20 bg-blue-500/10">
            <Clock3 className="size-4 text-blue-400" />
          </div>

          <p className="mt-3 text-[12px] font-semibold text-white">
            No recent activity
          </p>

          <p className="mt-1 text-[10px] text-[var(--text-muted)]">
            Operational activity will appear here as events
            are recorded.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-[var(--border)]">
          {activities.map((activity) => (
            <div
              key={activity.id}
              className="flex gap-3 px-5 py-4"
            >
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md border border-blue-500/20 bg-blue-500/10">
                <Activity className="size-4 text-blue-400" />
              </div>

              <div className="min-w-0 flex-1">
                <p className="text-[12px] font-medium text-white">
                  {activity.title}
                </p>

                <p className="mt-1 text-[11px] leading-5 text-[var(--text-secondary)]">
                  {activity.description}
                </p>

                <p className="mt-2 text-[9px] font-medium text-[var(--text-muted)]">
                  {new Date(
                    activity.created_at,
                  ).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}