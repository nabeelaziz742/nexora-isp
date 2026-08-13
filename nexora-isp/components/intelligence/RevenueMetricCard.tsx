import type { RevenueMetric } from "@/types/revenue-intelligence";

interface RevenueMetricCardProps {
  metric: RevenueMetric;
}

const toneStyles = {
  PRIMARY: "text-blue-400",
  HEALTHY: "text-emerald-400",
  WARNING: "text-amber-400",
  CRITICAL: "text-red-400",
  INTELLIGENCE: "text-violet-400",
};

export default function RevenueMetricCard({
  metric,
}: RevenueMetricCardProps) {
  return (
    <div className="border border-[#202938] bg-[#0D1117] p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
        {metric.label}
      </p>

      <p
        className={`mt-3 text-2xl font-semibold tracking-tight ${toneStyles[metric.tone]}`}
      >
        {metric.value}
      </p>

      <p className="mt-2 text-xs text-slate-500">
        {metric.description}
      </p>

      <div className="mt-4 border-t border-[#202938] pt-3">
        <p className="text-[11px] text-slate-600">
          {metric.change}
        </p>
      </div>
    </div>
  );
}