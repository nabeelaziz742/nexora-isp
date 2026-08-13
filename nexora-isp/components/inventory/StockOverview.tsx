import type {
  InventoryCategory,
  InventoryStockItem,
} from "@/types/inventory";

interface StockOverviewProps {
  items: InventoryStockItem[];
}

const categoryLabels: Record<InventoryCategory, string> = {
  ONU_ONT: "ONU / ONT",
  ROUTER: "Router",
  NETWORK_EQUIPMENT: "Network",
  FIBER_EQUIPMENT: "Fiber",
};

export default function StockOverview({ items }: StockOverviewProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Stock Operations Overview
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Operational equipment availability and deployment distribution
            </p>
          </div>

          <span className="text-xs text-slate-500">
            Configured thresholds
          </span>
        </div>
      </div>

      <div className="divide-y divide-[#202938]">
        {items.map((item) => {
          const isLowStock =
            item.availableUnits < item.minimumStockLevel;

          const availabilityPercentage = Math.round(
            (item.availableUnits / item.totalUnits) * 100
          );

          return (
            <div key={item.id} className="px-5 py-4">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="min-w-0 xl:w-56">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-slate-200">
                      {item.itemName}
                    </p>

                    {isLowStock && (
                      <span className="bg-red-500/10 px-2 py-1 text-[10px] font-semibold text-red-400">
                        LOW STOCK
                      </span>
                    )}
                  </div>

                  <p className="mt-1 text-xs text-slate-500">
                    {categoryLabels[item.category]} · Minimum{" "}
                    {item.minimumStockLevel} units
                  </p>
                </div>

                <div className="grid flex-1 grid-cols-2 gap-4 sm:grid-cols-5">
                  <StockValue
                    label="Total"
                    value={item.totalUnits}
                  />

                  <StockValue
                    label="Available"
                    value={item.availableUnits}
                    valueClassName={
                      isLowStock
                        ? "text-red-400"
                        : "text-emerald-400"
                    }
                  />

                  <StockValue
                    label="Assigned"
                    value={item.assignedUnits}
                  />

                  <StockValue
                    label="Field"
                    value={item.technicianUnits}
                    valueClassName="text-amber-400"
                  />

                  <StockValue
                    label="Repair"
                    value={item.repairUnits}
                    valueClassName="text-amber-400"
                  />
                </div>

                <div className="xl:w-44">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-500">
                      Availability
                    </span>

                    <span
                      className={
                        isLowStock
                          ? "font-medium text-red-400"
                          : "font-medium text-slate-300"
                      }
                    >
                      {availabilityPercentage}%
                    </span>
                  </div>

                  <div className="mt-2 h-1.5 overflow-hidden bg-[#121821]">
                    <div
                      className={
                        isLowStock
                          ? "h-full bg-red-500"
                          : "h-full bg-emerald-500"
                      }
                      style={{
                        width: `${Math.max(
                          availabilityPercentage,
                          3
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

interface StockValueProps {
  label: string;
  value: number;
  valueClassName?: string;
}

function StockValue({
  label,
  value,
  valueClassName = "text-slate-200",
}: StockValueProps) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.08em] text-slate-600">
        {label}
      </p>

      <p className={`mt-1 text-sm font-semibold ${valueClassName}`}>
        {value}
      </p>
    </div>
  );
}