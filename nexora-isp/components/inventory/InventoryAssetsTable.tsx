import type {
  InventoryAsset,
  InventoryCategory,
  InventoryStockStatus,
} from "@/types/inventory";

interface InventoryAssetsTableProps {
  assets: InventoryAsset[];
}

const categoryLabels: Record<InventoryCategory, string> = {
  ONU_ONT: "ONU / ONT",
  ROUTER: "Router",
  NETWORK_EQUIPMENT: "Network Equipment",
  FIBER_EQUIPMENT: "Fiber Equipment",
};

const stockStatusStyles: Record<
  InventoryStockStatus,
  string
> = {
  AVAILABLE:
    "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
  ASSIGNED:
    "border-blue-500/20 bg-blue-500/10 text-blue-400",
  TECHNICIAN_CUSTODY:
    "border-amber-500/20 bg-amber-500/10 text-amber-400",
  IN_REPAIR:
    "border-orange-500/20 bg-orange-500/10 text-orange-400",
  FAULTY:
    "border-red-500/20 bg-red-500/10 text-red-400",
};

const stockStatusLabels: Record<
  InventoryStockStatus,
  string
> = {
  AVAILABLE: "Available",
  ASSIGNED: "Assigned",
  TECHNICIAN_CUSTODY: "Technician Custody",
  IN_REPAIR: "In Repair",
  FAULTY: "Faulty",
};

export default function InventoryAssetsTable({
  assets,
}: InventoryAssetsTableProps) {
  return (
    <section className="overflow-hidden border border-[#202938] bg-[#0D1117]">
      <div className="flex flex-col gap-4 border-b border-[#202938] px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">
            Asset & Device Registry
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Serialized subscriber devices and ISP infrastructure assets
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button className="border border-[#202938] bg-[#121821] px-3 py-2 text-xs font-medium text-slate-300 transition hover:border-slate-600">
            Filter Assets
          </button>

          <button className="bg-blue-600 px-3 py-2 text-xs font-medium text-white transition hover:bg-blue-500">
            Register Asset
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1380px] border-collapse">
          <thead>
            <tr className="border-b border-[#202938] bg-[#0A0E14]">
              <TableHead>Asset</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Serial / MAC</TableHead>
              <TableHead>Stock State</TableHead>
              <TableHead>Assignment Context</TableHead>
              <TableHead>Network Context</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Last Updated</TableHead>
            </tr>
          </thead>

          <tbody>
            {assets.map((asset) => (
              <tr
                key={asset.id}
                className="border-b border-[#202938] last:border-b-0 hover:bg-[#121821]/60"
              >
                <TableCell>
                  <div>
                    <p className="font-medium text-slate-200">
                      {asset.deviceName}
                    </p>

                    <p className="mt-1 font-mono text-[11px] text-blue-400">
                      {asset.assetCode}
                    </p>

                    <p className="mt-1 text-[11px] text-slate-600">
                      {asset.manufacturer} · {asset.model}
                    </p>
                  </div>
                </TableCell>

                <TableCell>
                  <span className="text-xs text-slate-300">
                    {categoryLabels[asset.category]}
                  </span>
                </TableCell>

                <TableCell>
                  <div className="space-y-1">
                    <p className="font-mono text-[11px] text-slate-300">
                      SN: {asset.serialNumber}
                    </p>

                    <p className="font-mono text-[11px] text-slate-500">
                      MAC: {asset.macAddress ?? "N/A"}
                    </p>
                  </div>
                </TableCell>

                <TableCell>
                  <span
                    className={`inline-flex border px-2 py-1 text-[10px] font-semibold ${stockStatusStyles[asset.stockStatus]}`}
                  >
                    {stockStatusLabels[asset.stockStatus]}
                  </span>
                </TableCell>

                <TableCell>
                  {asset.assignedCustomer ? (
                    <div>
                      <p className="text-xs font-medium text-slate-200">
                        {asset.assignedCustomer}
                      </p>

                      <p className="mt-1 font-mono text-[11px] text-blue-400">
                        {asset.customerCode}
                      </p>
                    </div>
                  ) : asset.assignedTechnician ? (
                    <div>
                      <p className="text-xs font-medium text-amber-400">
                        {asset.assignedTechnician}
                      </p>

                      <p className="mt-1 font-mono text-[11px] text-slate-500">
                        {asset.technicianCode}
                      </p>
                    </div>
                  ) : (
                    <span className="text-xs text-slate-600">
                      Unassigned
                    </span>
                  )}
                </TableCell>

                <TableCell>
                  {asset.connectedNode ? (
                    <span className="font-mono text-[11px] text-blue-400">
                      {asset.connectedNode}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-600">
                      No node context
                    </span>
                  )}
                </TableCell>

                <TableCell>
                  <span className="text-xs text-slate-400">
                    {asset.warehouseLocation}
                  </span>
                </TableCell>

                <TableCell>
                  <span className="text-xs text-slate-500">
                    {asset.lastUpdated}
                  </span>
                </TableCell>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

interface TableHeadProps {
  children: React.ReactNode;
}

function TableHead({ children }: TableHeadProps) {
  return (
    <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
      {children}
    </th>
  );
}

interface TableCellProps {
  children: React.ReactNode;
}

function TableCell({ children }: TableCellProps) {
  return (
    <td className="px-5 py-4 align-middle">
      {children}
    </td>
  );
}