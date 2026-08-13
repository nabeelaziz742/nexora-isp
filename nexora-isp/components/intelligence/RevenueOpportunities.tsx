import {
  BadgeDollarSign,
  RefreshCcw,
  TrendingUp,
} from "lucide-react";

import type {
  RevenueOpportunity,
  RevenueOpportunityType,
} from "@/types/revenue-intelligence";

interface RevenueOpportunitiesProps {
  opportunities: RevenueOpportunity[];
}

const opportunityConfig: Record<
  RevenueOpportunityType,
  {
    label: string;
    icon: typeof TrendingUp;
    iconClassName: string;
    backgroundClassName: string;
  }
> = {
  PACKAGE_UPGRADE: {
    label: "Package Upgrade",
    icon: TrendingUp,
    iconClassName: "text-violet-400",
    backgroundClassName: "bg-violet-500/10",
  },
  COLLECTION_RECOVERY: {
    label: "Collection Recovery",
    icon: RefreshCcw,
    iconClassName: "text-emerald-400",
    backgroundClassName: "bg-emerald-500/10",
  },
  REVENUE_LEAKAGE: {
    label: "Revenue Leakage",
    icon: BadgeDollarSign,
    iconClassName: "text-amber-400",
    backgroundClassName: "bg-amber-500/10",
  },
};

function formatCurrency(value: number) {
  return `PKR ${value.toLocaleString("en-PK")}`;
}

export default function RevenueOpportunities({
  opportunities,
}: RevenueOpportunitiesProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-slate-100">
          Revenue Opportunities
        </h2>

        <p className="mt-1 text-xs text-slate-500">
          Potential recurring revenue and collection improvement signals
        </p>
      </div>

      <div className="divide-y divide-[#202938]">
        {opportunities.map((opportunity) => {
          const config =
            opportunityConfig[opportunity.type];

          const Icon = config.icon;

          return (
            <article
              key={opportunity.id}
              className="px-5 py-5"
            >
              <div className="flex items-start gap-3">
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center ${config.backgroundClassName}`}
                >
                  <Icon
                    className={`h-4 w-4 ${config.iconClassName}`}
                  />
                </div>

                <div className="min-w-0 flex-1">
                  <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-600">
                    {config.label}
                  </span>

                  <h3 className="mt-2 text-sm font-medium text-slate-200">
                    {opportunity.title}
                  </h3>

                  <p className="mt-2 text-[11px] leading-5 text-slate-500">
                    {opportunity.description}
                  </p>

                  <div className="mt-4 space-y-3">
                    <OpportunityValue
                      label="Estimated Monthly Impact"
                      value={formatCurrency(
                        opportunity.estimatedMonthlyImpact
                      )}
                      valueClassName="text-emerald-400"
                    />

                    <OpportunityValue
                      label="Customer Segment"
                      value={opportunity.customerSegment}
                    />

                    <div className="grid grid-cols-2 gap-3">
                      <OpportunityValue
                        label="Customers"
                        value={String(
                          opportunity.customerCount
                        )}
                      />

                      <OpportunityValue
                        label="Confidence"
                        value={`${opportunity.confidence}%`}
                        valueClassName="text-violet-400"
                      />
                    </div>
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

interface OpportunityValueProps {
  label: string;
  value: string;
  valueClassName?: string;
}

function OpportunityValue({
  label,
  value,
  valueClassName = "text-slate-300",
}: OpportunityValueProps) {
  return (
    <div className="bg-[#121821] px-3 py-3">
      <p className="text-[10px] uppercase tracking-[0.08em] text-slate-600">
        {label}
      </p>

      <p
        className={`mt-1 text-xs font-semibold ${valueClassName}`}
      >
        {value}
      </p>
    </div>
  );
}