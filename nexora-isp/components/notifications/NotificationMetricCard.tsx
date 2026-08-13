import type { NotificationMetric } from "@/types/notifications";

interface NotificationMetricCardProps {
  metric: NotificationMetric;
}

const toneStyles = {
  PRIMARY: "text-blue-400",
  HEALTHY: "text-emerald-400",
  WARNING: "text-amber-400",
  CRITICAL: "text-red-400",
};

export default function NotificationMetricCard({
  metric,
}: NotificationMetricCardProps) {
  return (
    <div className="border border-[#202938] bg-[#0D1117] px-3 py-3">
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-[9px] font-semibold uppercase tracking-[0.08em] text-slate-500">
            {metric.label}
          </p>

          <p
            className={`mt-2 text-xl font-semibold tracking-tight ${
              toneStyles[metric.tone]
            }`}
          >
            {metric.value}
          </p>
        </div>
      </div>

      <p className="mt-1 truncate text-[10px] text-slate-600">
        {metric.description}
      </p>
    </div>
  );
}