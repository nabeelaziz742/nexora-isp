import type { ReportMetric } from "@/types/reports";

interface ReportMetricCardProps {
  metric: ReportMetric;
}

const toneStyles = {
  PRIMARY: "text-blue-400",
  HEALTHY: "text-emerald-400",
  WARNING: "text-amber-400",
  INTELLIGENCE: "text-violet-400",
};

export default function ReportMetricCard({
  metric,
}: ReportMetricCardProps) {
  return (
    <div className="border border-[#202938] bg-[#0D1117] p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
        {metric.label}
      </p>

      <p
        className={`mt-3 text-2xl font-semibold tracking-tight ${
          toneStyles[metric.tone]
        }`}
      >
        {metric.value}
      </p>

      <p className="mt-2 text-xs text-slate-500">
        {metric.description}
      </p>
    </div>
  );
}