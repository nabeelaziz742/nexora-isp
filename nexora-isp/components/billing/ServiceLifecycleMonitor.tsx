import {
  CheckCircle2,
  Clock3,
  RefreshCw,
  ShieldAlert,
  ShieldOff,
} from "lucide-react";

import { BillingLifecycleSummary } from "@/types/billing";

interface ServiceLifecycleMonitorProps {
  lifecycle: BillingLifecycleSummary[];
}

const lifecycleStyles = {
  ACTIVE: {
    icon: CheckCircle2,
    color: "text-[#22C55E]",
    border: "border-[#22C55E]/30",
    background: "bg-[#22C55E]/10",
    line: "bg-[#22C55E]",
  },
  GRACE_PERIOD: {
    icon: Clock3,
    color: "text-[#F59E0B]",
    border: "border-[#F59E0B]/30",
    background: "bg-[#F59E0B]/10",
    line: "bg-[#F59E0B]",
  },
  SUSPENSION_PENDING: {
    icon: ShieldAlert,
    color: "text-[#F59E0B]",
    border: "border-[#F59E0B]/30",
    background: "bg-[#F59E0B]/10",
    line: "bg-[#F59E0B]",
  },
  SUSPENDED_NON_PAYMENT: {
    icon: ShieldOff,
    color: "text-[#EF4444]",
    border: "border-[#EF4444]/30",
    background: "bg-[#EF4444]/10",
    line: "bg-[#EF4444]",
  },
  RESTORE_PENDING: {
    icon: RefreshCw,
    color: "text-[#3B82F6]",
    border: "border-[#3B82F6]/30",
    background: "bg-[#3B82F6]/10",
    line: "bg-[#3B82F6]",
  },
};

export default function ServiceLifecycleMonitor({
  lifecycle,
}: ServiceLifecycleMonitorProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-[#F8FAFC]">
          Service Lifecycle Monitor
        </h2>

        <p className="mt-1 text-xs text-[#64748B]">
          Billing-driven customer service states and automation exposure
        </p>
      </div>

      <div className="overflow-x-auto p-5">
        <div className="grid min-w-[900px] grid-cols-5 gap-0">
          {lifecycle.map((item, index) => {
            const style = lifecycleStyles[item.status];
            const Icon = style.icon;
            const isLast = index === lifecycle.length - 1;

            return (
              <div key={item.status} className="relative">
                {!isLast && (
                  <div className="absolute left-[calc(50%+24px)] right-[-50%] top-6 h-px bg-[#334155]" />
                )}

                <div className="relative z-10 px-3 text-center">
                  <div
                    className={`mx-auto flex h-12 w-12 items-center justify-center border ${style.border} ${style.background}`}
                  >
                    <Icon className={`h-5 w-5 ${style.color}`} />
                  </div>

                  <p
                    className={`mt-3 text-xs font-semibold ${style.color}`}
                  >
                    {item.label}
                  </p>

                  <p className="mt-2 text-2xl font-semibold text-[#F8FAFC]">
                    {item.customerCount.toLocaleString()}
                  </p>

                  <p className="mx-auto mt-2 max-w-[170px] text-[11px] leading-5 text-[#64748B]">
                    {item.description}
                  </p>

                  <div className="mt-4 h-1 overflow-hidden bg-[#202938]">
                    <div className={`h-full w-full ${style.line}`} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-5 border border-[#202938] bg-[#121821] px-4 py-3">
          <p className="text-xs leading-5 text-[#94A3B8]">
            Payment verification can move a suspended customer into{" "}
            <span className="font-medium text-[#3B82F6]">
              RESTORE_PENDING
            </span>
            . After network restoration confirmation, service returns to{" "}
            <span className="font-medium text-[#22C55E]">
              ACTIVE
            </span>
            .
          </p>
        </div>
      </div>
    </section>
  );
}