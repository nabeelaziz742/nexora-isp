import {
  ArrowUpRight,
  CircleAlert,
  Info,
  TriangleAlert,
} from "lucide-react";

import type { InventoryIntelligenceItem } from "@/types/inventory";

interface InventoryIntelligenceProps {
  items: InventoryIntelligenceItem[];
}

const severityConfig = {
  CRITICAL: {
    icon: CircleAlert,
    iconClassName: "text-red-400",
    backgroundClassName: "bg-red-500/10",
    labelClassName: "text-red-400",
  },
  WARNING: {
    icon: TriangleAlert,
    iconClassName: "text-amber-400",
    backgroundClassName: "bg-amber-500/10",
    labelClassName: "text-amber-400",
  },
  INFO: {
    icon: Info,
    iconClassName: "text-blue-400",
    backgroundClassName: "bg-blue-500/10",
    labelClassName: "text-blue-400",
  },
};

export default function InventoryIntelligence({
  items,
}: InventoryIntelligenceProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Inventory Intelligence
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Asset availability, stock exposure and field custody signals
            </p>
          </div>

          <span className="text-xs font-medium text-blue-400">
            Operational Analysis
          </span>
        </div>
      </div>

      <div className="divide-y divide-[#202938]">
        {items.map((item) => {
          const config = severityConfig[item.severity];
          const Icon = config.icon;

          return (
            <div key={item.id} className="px-5 py-4">
              <div className="flex items-start gap-4">
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center ${config.backgroundClassName}`}
                >
                  <Icon
                    className={`h-4 w-4 ${config.iconClassName}`}
                  />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <span
                        className={`text-[10px] font-semibold tracking-[0.08em] ${config.labelClassName}`}
                      >
                        {item.severity}
                      </span>

                      <h3 className="mt-1 text-sm font-medium text-slate-200">
                        {item.title}
                      </h3>
                    </div>

                    <button className="flex shrink-0 items-center gap-1 text-xs font-medium text-blue-400 transition hover:text-blue-300">
                      {item.actionLabel}
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  <p className="mt-2 max-w-4xl text-xs leading-5 text-slate-500">
                    {item.description}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}