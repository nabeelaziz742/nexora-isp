import {
  ArrowUpRight,
  CalendarClock,
  Download,
} from "lucide-react";

import type {
  ReportDefinition,
  ReportDomain,
} from "@/types/reports";

interface ReportCatalogProps {
  reports: ReportDefinition[];
}

const domainLabels: Record<ReportDomain, string> = {
  CUSTOMERS: "Customers",
  NETWORK: "Network",
  BILLING: "Billing",
  SUPPORT: "Support",
  FIELD_OPERATIONS: "Field Operations",
  INVENTORY: "Inventory",
};

const domainStyles: Record<ReportDomain, string> = {
  CUSTOMERS: "bg-blue-500/10 text-blue-400",
  NETWORK: "bg-emerald-500/10 text-emerald-400",
  BILLING: "bg-amber-500/10 text-amber-400",
  SUPPORT: "bg-red-500/10 text-red-400",
  FIELD_OPERATIONS: "bg-violet-500/10 text-violet-400",
  INVENTORY: "bg-cyan-500/10 text-cyan-400",
};

export default function ReportCatalog({
  reports,
}: ReportCatalogProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="flex flex-col gap-3 border-b border-[#202938] px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">
            Operational Report Catalog
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Generate structured reports across ISP operational domains
          </p>
        </div>

        <button className="border border-[#202938] bg-[#121821] px-3 py-2 text-xs font-medium text-slate-300 transition hover:border-slate-600">
          Report Filters
        </button>
      </div>

      <div className="grid gap-px bg-[#202938] lg:grid-cols-2">
        {reports.map((report) => (
          <article
            key={report.id}
            className="bg-[#0D1117] p-5"
          >
            <div className="flex items-start justify-between gap-4">
              <span
                className={`px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] ${
                  domainStyles[report.domain]
                }`}
              >
                {domainLabels[report.domain]}
              </span>

              <button className="text-slate-600 transition hover:text-blue-400">
                <ArrowUpRight className="h-4 w-4" />
              </button>
            </div>

            <h3 className="mt-4 text-sm font-semibold text-slate-200">
              {report.name}
            </h3>

            <p className="mt-2 min-h-10 text-xs leading-5 text-slate-500">
              {report.description}
            </p>

            <div className="mt-5 flex flex-wrap items-center gap-2">
              {report.availableFormats.map((format) => (
                <span
                  key={format}
                  className="border border-[#202938] bg-[#121821] px-2 py-1 font-mono text-[10px] text-slate-400"
                >
                  {format}
                </span>
              ))}
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="bg-[#121821] px-3 py-3">
                <p className="text-[10px] uppercase tracking-[0.08em] text-slate-600">
                  Last Generated
                </p>

                <p className="mt-1 text-xs font-medium text-slate-300">
                  {report.lastGenerated}
                </p>
              </div>

              <div className="bg-[#121821] px-3 py-3">
                <p className="text-[10px] uppercase tracking-[0.08em] text-slate-600">
                  Schedule
                </p>

                <div className="mt-1 flex items-center gap-1.5">
                  <CalendarClock className="h-3.5 w-3.5 text-slate-600" />

                  <p className="text-xs font-medium text-slate-300">
                    {report.scheduleLabel ?? "Not Scheduled"}
                  </p>
                </div>
              </div>
            </div>

            <button className="mt-4 flex w-full items-center justify-center gap-2 bg-blue-600 px-4 py-2.5 text-xs font-medium text-white transition hover:bg-blue-500">
              <Download className="h-3.5 w-3.5" />
              Generate Report
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}