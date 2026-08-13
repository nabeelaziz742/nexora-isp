import {
  Activity,
  AlertTriangle,
  RadioTower,
  Router,
  Users,
} from "lucide-react";

import type { NetworkMetric } from "@/types/network";

interface NetworkMetricCardProps {
  metric: NetworkMetric;
}

const metricIcons = {
  "total-nodes": RadioTower,
  "active-nodes": Activity,
  "active-assignments": Users,
  "provisioning-pending": Router,
  "provisioning-failed": AlertTriangle,
  "total-provisioning": Activity,
};

const statusStyles = {
  healthy: {
    icon: "text-[#22C55E]",
    indicator: "bg-[#22C55E]",
  },
  warning: {
    icon: "text-[#F59E0B]",
    indicator: "bg-[#F59E0B]",
  },
  critical: {
    icon: "text-[#EF4444]",
    indicator: "bg-[#EF4444]",
  },
  neutral: {
    icon: "text-[#3B82F6]",
    indicator: "bg-[#3B82F6]",
  },
};

export default function NetworkMetricCard({
  metric,
}: NetworkMetricCardProps) {
  const Icon =
    metricIcons[
      metric.id as keyof typeof metricIcons
    ] ?? Activity;

  const styles = statusStyles[metric.status];

  return (
    <div className="border border-[#202938] bg-[#0D1117] p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.08em] text-[#64748B]">
            {metric.label}
          </p>

          <div className="mt-3 flex items-end gap-2">
            <p className="text-2xl font-semibold tracking-tight text-[#F8FAFC]">
              {metric.value}
            </p>

            {metric.trend && (
              <span className="mb-1 text-xs font-medium text-[#22C55E]">
                {metric.trend}
              </span>
            )}
          </div>
        </div>

        <div className="flex h-9 w-9 items-center justify-center border border-[#202938] bg-[#121821]">
          <Icon className={`h-4 w-4 ${styles.icon}`} />
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 border-t border-[#202938] pt-3">
        <span
          className={`h-1.5 w-1.5 rounded-full ${styles.indicator}`}
        />

        <p className="text-xs text-[#64748B]">
          {metric.description}
        </p>
      </div>
    </div>
  );
}