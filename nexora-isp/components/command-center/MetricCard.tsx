import type { CommandMetric } from "@/types/command-center";

const toneStyles: Record<string, string> = {
  primary: "text-blue-400",
  success: "text-green-400",
  warning: "text-amber-400",
  danger: "text-red-400",
  intelligence: "text-violet-400",
};

interface MetricCardProps {
  metric: CommandMetric;
}

export default function MetricCard({ metric }: MetricCardProps) {
  return (
    <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
      <p className="text-[11px] font-medium text-[var(--text-secondary)]">
        {metric.label}
      </p>

      <div className="mt-3 flex items-end justify-between gap-3">
        <p className="text-2xl font-semibold tracking-tight text-white">
          {metric.value}
        </p>

        {metric.change && (
          <span
            className={`text-[11px] font-semibold ${toneStyles[metric.tone] ?? "text-slate-400"}`}
          >
            {metric.change}
          </span>
        )}
      </div>

      <p className="mt-2 text-[10px] text-[var(--text-muted)]">
        {metric.helper}
      </p>
    </div>
  );
}