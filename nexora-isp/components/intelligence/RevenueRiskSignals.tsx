import {
  ArrowUpRight,
  CircleAlert,
  Info,
  TriangleAlert,
} from "lucide-react";

import type {
  RevenueRiskSignal,
  RevenueSignalSeverity,
} from "@/types/revenue-intelligence";

interface RevenueRiskSignalsProps {
  signals: RevenueRiskSignal[];
}

const severityConfig: Record<
  RevenueSignalSeverity,
  {
    icon: typeof CircleAlert;
    iconClassName: string;
    backgroundClassName: string;
    badgeClassName: string;
  }
> = {
  CRITICAL: {
    icon: CircleAlert,
    iconClassName: "text-red-400",
    backgroundClassName: "bg-red-500/10",
    badgeClassName: "bg-red-500/10 text-red-400",
  },
  WARNING: {
    icon: TriangleAlert,
    iconClassName: "text-amber-400",
    backgroundClassName: "bg-amber-500/10",
    badgeClassName: "bg-amber-500/10 text-amber-400",
  },
  INFO: {
    icon: Info,
    iconClassName: "text-blue-400",
    backgroundClassName: "bg-blue-500/10",
    badgeClassName: "bg-blue-500/10 text-blue-400",
  },
};

function formatCurrency(value: number) {
  return `PKR ${value.toLocaleString("en-PK")}`;
}

export default function RevenueRiskSignals({
  signals,
}: RevenueRiskSignalsProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-slate-100">
          Revenue Risk Intelligence
        </h2>

        <p className="mt-1 text-xs text-slate-500">
          Collection exposure and recurring revenue risk signals
        </p>
      </div>

      <div className="divide-y divide-[#202938]">
        {signals.map((signal) => {
          const config = severityConfig[signal.severity];
          const Icon = config.icon;

          return (
            <article
              key={signal.id}
              className="px-5 py-5"
            >
              <div className="flex items-start gap-4">
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center ${config.backgroundClassName}`}
                >
                  <Icon
                    className={`h-4 w-4 ${config.iconClassName}`}
                  />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                    <div>
                      <span
                        className={`inline-flex px-2 py-1 text-[10px] font-semibold ${config.badgeClassName}`}
                      >
                        {signal.severity}
                      </span>

                      <h3 className="mt-3 text-sm font-medium text-slate-200">
                        {signal.title}
                      </h3>
                    </div>

                    <button className="flex shrink-0 items-center gap-1 text-xs font-medium text-blue-400 transition hover:text-blue-300">
                      {signal.actionLabel}

                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  <p className="mt-2 max-w-4xl text-xs leading-5 text-slate-500">
                    {signal.description}
                  </p>

                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <SignalValue
                      label="Revenue Exposure"
                      value={formatCurrency(
                        signal.exposureAmount
                      )}
                    />

                    <SignalValue
                      label="Customers"
                      value={String(
                        signal.affectedCustomers
                      )}
                    />

                    <SignalValue
                      label="Confidence"
                      value={`${signal.confidence}%`}
                    />
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

interface SignalValueProps {
  label: string;
  value: string;
}

function SignalValue({
  label,
  value,
}: SignalValueProps) {
  return (
    <div className="bg-[#121821] px-3 py-3">
      <p className="text-[10px] uppercase tracking-[0.08em] text-slate-600">
        {label}
      </p>

      <p className="mt-1 text-xs font-semibold text-slate-300">
        {value}
      </p>
    </div>
  );
}