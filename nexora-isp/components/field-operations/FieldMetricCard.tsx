import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Navigation,
  UserCheck,
  Wrench,
} from "lucide-react";

import { FieldMetric } from "@/types/field-operations";

interface FieldMetricCardProps {
  metric: FieldMetric;
}

const metricIcons = {
  "active-jobs": Wrench,
  "available-technicians": UserCheck,
  "sla-risk": AlertTriangle,
  "en-route": Navigation,
  "completed-today": CheckCircle2,
  "avg-resolution": Clock3,
};

const statusStyles = {
  healthy: "text-[#22C55E]",
  warning: "text-[#F59E0B]",
  critical: "text-[#EF4444]",
  neutral: "text-[#3B82F6]",
};

export default function FieldMetricCard({
  metric,
}: FieldMetricCardProps) {
  const Icon =
    metricIcons[metric.id as keyof typeof metricIcons] ?? Wrench;

  return (
    <div className="border border-[#202938] bg-[#0D1117] p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#64748B]">
            {metric.label}
          </p>

          <div className="mt-3 flex items-end gap-2">
            <p className="text-2xl font-semibold tracking-tight text-[#F8FAFC]">
              {metric.value}
            </p>

            {metric.trend && (
              <span className="mb-1 text-[11px] text-[#94A3B8]">
                {metric.trend}
              </span>
            )}
          </div>
        </div>

        <div className="flex h-9 w-9 items-center justify-center border border-[#202938] bg-[#121821]">
          <Icon
            className={`h-4 w-4 ${statusStyles[metric.status]}`}
          />
        </div>
      </div>

      <p className="mt-4 border-t border-[#202938] pt-3 text-xs text-[#64748B]">
        {metric.description}
      </p>
    </div>
  );
}