import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
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
  const content = (
    <div className={`group relative rounded-lg border border-[#202938] bg-[#0D1117] p-4 transition-all ${
      metric.href ? "hover:border-blue-500/40 hover:bg-[#121821] hover:shadow-lg hover:shadow-black/40 cursor-pointer" : ""
    }`}>
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-medium text-[var(--text-secondary)]">
          {metric.label}
        </p>
        {metric.href && (
          <ArrowUpRight className="h-3.5 w-3.5 text-slate-600 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-blue-400" />
        )}
      </div>

      <div className="mt-3 flex items-end justify-between gap-3">
        <p className="text-2xl font-semibold tracking-tight text-white font-mono">
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

      <p className="mt-2 text-[10px] text-[var(--text-muted)] truncate">
        {metric.helper}
      </p>
    </div>
  );

  if (metric.href) {
    return (
      <Link href={metric.href} className="block">
        {content}
      </Link>
    );
  }

  return content;
}