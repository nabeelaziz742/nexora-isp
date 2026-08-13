import {
  ArrowUpRight,
  CircleAlert,
  Info,
  Lightbulb,
  TriangleAlert,
} from "lucide-react";

import type {
  IntelligenceDomain,
  IntelligenceSeverity,
  OperationalInsight,
} from "@/types/intelligence";

interface OperationalInsightsProps {
  insights: OperationalInsight[];
}

const severityConfig: Record<
  IntelligenceSeverity,
  {
    icon: typeof CircleAlert;
    iconClassName: string;
    iconBackgroundClassName: string;
    badgeClassName: string;
  }
> = {
  CRITICAL: {
    icon: CircleAlert,
    iconClassName: "text-red-400",
    iconBackgroundClassName: "bg-red-500/10",
    badgeClassName: "bg-red-500/10 text-red-400",
  },
  WARNING: {
    icon: TriangleAlert,
    iconClassName: "text-amber-400",
    iconBackgroundClassName: "bg-amber-500/10",
    badgeClassName: "bg-amber-500/10 text-amber-400",
  },
  OPPORTUNITY: {
    icon: Lightbulb,
    iconClassName: "text-violet-400",
    iconBackgroundClassName: "bg-violet-500/10",
    badgeClassName: "bg-violet-500/10 text-violet-400",
  },
  INFO: {
    icon: Info,
    iconClassName: "text-blue-400",
    iconBackgroundClassName: "bg-blue-500/10",
    badgeClassName: "bg-blue-500/10 text-blue-400",
  },
};

const domainLabels: Record<IntelligenceDomain, string> = {
  NETWORK: "Network",
  BILLING: "Billing",
  CUSTOMER: "Customer",
  SUPPORT: "Support",
  FIELD_OPERATIONS: "Field Operations",
};

export default function OperationalInsights({
  insights,
}: OperationalInsightsProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="flex items-center justify-between gap-4 border-b border-[#202938] px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">
            Active Operational Intelligence
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Cross-module patterns detected across current ISP operations
          </p>
        </div>

        <span className="text-xs font-medium text-violet-400">
          AI Analysis
        </span>
      </div>

      <div className="divide-y divide-[#202938]">
        {insights.map((insight) => {
          const config = severityConfig[insight.severity];
          const Icon = config.icon;

          return (
            <article key={insight.id} className="px-5 py-5">
              <div className="flex items-start gap-4">
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center ${config.iconBackgroundClassName}`}
                >
                  <Icon
                    className={`h-4 w-4 ${config.iconClassName}`}
                  />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`px-2 py-1 text-[10px] font-semibold ${config.badgeClassName}`}
                        >
                          {insight.severity}
                        </span>

                        <span className="text-[10px] font-medium uppercase tracking-[0.08em] text-slate-600">
                          {domainLabels[insight.domain]}
                        </span>

                        <span className="text-[10px] text-slate-700">
                          ·
                        </span>

                        <span className="text-[10px] text-slate-600">
                          {insight.detectedAt}
                        </span>
                      </div>

                      <h3 className="mt-3 text-sm font-medium text-slate-200">
                        {insight.title}
                      </h3>
                    </div>

                    <button className="flex shrink-0 items-center gap-1 text-xs font-medium text-blue-400 transition hover:text-blue-300">
                      {insight.actionLabel}
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  <p className="mt-2 max-w-5xl text-xs leading-5 text-slate-500">
                    {insight.description}
                  </p>

                  <div className="mt-4 flex items-center gap-3">
                    <span className="text-[10px] uppercase tracking-[0.08em] text-slate-600">
                      Confidence
                    </span>

                    <div className="h-1.5 w-28 overflow-hidden bg-[#121821]">
                      <div
                        className="h-full bg-violet-500"
                        style={{
                          width: `${insight.confidence}%`,
                        }}
                      />
                    </div>

                    <span className="font-mono text-[11px] font-medium text-violet-400">
                      {insight.confidence}%
                    </span>
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