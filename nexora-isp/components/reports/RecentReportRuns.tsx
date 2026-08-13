import type {
  RecentReportRun,
  ReportDomain,
  ReportRunStatus,
} from "@/types/reports";

interface RecentReportRunsProps {
  runs: RecentReportRun[];
}

const domainLabels: Record<ReportDomain, string> = {
  CUSTOMERS: "Customers",
  NETWORK: "Network",
  BILLING: "Billing",
  SUPPORT: "Support",
  FIELD_OPERATIONS: "Field Operations",
  INVENTORY: "Inventory",
};

const statusStyles: Record<ReportRunStatus, string> = {
  COMPLETED:
    "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
  PROCESSING:
    "border-blue-500/20 bg-blue-500/10 text-blue-400",
  FAILED:
    "border-red-500/20 bg-red-500/10 text-red-400",
};

const statusLabels: Record<ReportRunStatus, string> = {
  COMPLETED: "Completed",
  PROCESSING: "Processing",
  FAILED: "Failed",
};

export default function RecentReportRuns({
  runs,
}: RecentReportRunsProps) {
  return (
    <section className="overflow-hidden border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-slate-100">
          Recent Report Runs
        </h2>

        <p className="mt-1 text-xs text-slate-500">
          Report generation execution and delivery status
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1100px] border-collapse">
          <thead>
            <tr className="border-b border-[#202938] bg-[#0A0E14]">
              <TableHead>Report</TableHead>
              <TableHead>Domain</TableHead>
              <TableHead>Period</TableHead>
              <TableHead>Format</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Requested By</TableHead>
              <TableHead>Generated</TableHead>
            </tr>
          </thead>

          <tbody>
            {runs.map((run) => (
              <tr
                key={run.id}
                className="border-b border-[#202938] last:border-b-0 hover:bg-[#121821]/60"
              >
                <TableCell>
                  <p className="text-xs font-medium text-slate-200">
                    {run.reportName}
                  </p>

                  <p className="mt-1 font-mono text-[11px] text-blue-400">
                    {run.reportCode}
                  </p>
                </TableCell>

                <TableCell>
                  <span className="text-xs text-slate-400">
                    {domainLabels[run.domain]}
                  </span>
                </TableCell>

                <TableCell>
                  <span className="text-xs text-slate-400">
                    {run.period}
                  </span>
                </TableCell>

                <TableCell>
                  <span className="border border-[#202938] bg-[#121821] px-2 py-1 font-mono text-[10px] text-slate-400">
                    {run.format}
                  </span>
                </TableCell>

                <TableCell>
                  <span
                    className={`inline-flex border px-2 py-1 text-[10px] font-semibold ${
                      statusStyles[run.status]
                    }`}
                  >
                    {statusLabels[run.status]}
                  </span>
                </TableCell>

                <TableCell>
                  <span className="text-xs text-slate-400">
                    {run.requestedBy}
                  </span>
                </TableCell>

                <TableCell>
                  <span className="text-xs text-slate-500">
                    {run.generatedAt}
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