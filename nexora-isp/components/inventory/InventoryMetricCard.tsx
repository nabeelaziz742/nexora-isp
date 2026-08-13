import type { InventoryMetric } from "@/types/inventory";

interface InventoryMetricCardProps {
  metric: InventoryMetric;
}

const toneStyles = {
  primary: {
    icon: "text-blue-400",
    iconBackground: "bg-blue-500/10",
    value: "text-slate-50",
  },
  healthy: {
    icon: "text-emerald-400",
    iconBackground: "bg-emerald-500/10",
    value: "text-emerald-400",
  },
  warning: {
    icon: "text-amber-400",
    iconBackground: "bg-amber-500/10",
    value: "text-amber-400",
  },
  critical: {
    icon: "text-red-400",
    iconBackground: "bg-red-500/10",
    value: "text-red-400",
  },
};

export default function InventoryMetricCard({
  metric,
}: InventoryMetricCardProps) {
  const Icon = metric.icon;
  const styles = toneStyles[metric.tone];

  return (
    <div className="border border-[#202938] bg-[#0D1117] p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            {metric.label}
          </p>

          <p className={`mt-3 text-2xl font-semibold ${styles.value}`}>
            {metric.value}
          </p>
        </div>

        <div
          className={`flex h-9 w-9 items-center justify-center ${styles.iconBackground}`}
        >
          <Icon className={`h-4 w-4 ${styles.icon}`} />
        </div>
      </div>

      <p className="mt-2 text-xs text-slate-500">{metric.description}</p>
    </div>
  );
}