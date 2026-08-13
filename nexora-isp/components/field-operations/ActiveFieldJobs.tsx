import {
  AlertTriangle,
  ArrowUpRight,
  Link2,
} from "lucide-react";

import { FieldJob } from "@/types/field-operations";

interface ActiveFieldJobsProps {
  jobs: FieldJob[];
}

const priorityStyles = {
  LOW:
    "border-[#64748B]/20 bg-[#64748B]/10 text-[#94A3B8]",
  MEDIUM:
    "border-[#3B82F6]/20 bg-[#3B82F6]/10 text-[#60A5FA]",
  HIGH:
    "border-[#F59E0B]/20 bg-[#F59E0B]/10 text-[#F59E0B]",
  CRITICAL:
    "border-[#EF4444]/20 bg-[#EF4444]/10 text-[#EF4444]",
};

const statusStyles = {
  UNASSIGNED: "text-[#64748B]",
  ASSIGNED: "text-[#A78BFA]",
  EN_ROUTE: "text-[#F59E0B]",
  ON_SITE: "text-[#3B82F6]",
  COMPLETED: "text-[#22C55E]",
};

export default function ActiveFieldJobs({
  jobs,
}: ActiveFieldJobsProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-[#F8FAFC]">
          Active Field Jobs
        </h2>

        <p className="mt-1 text-xs text-[#64748B]">
          Technician assignments, SLA exposure and field progress
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1050px] text-left">
          <thead>
            <tr className="border-b border-[#202938] bg-[#121821]/50">
              <th className="px-5 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Job
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Customer / Area
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Priority
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Status
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Technician
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Network Context
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                SLA
              </th>

              <th className="px-4 py-3" />
            </tr>
          </thead>

          <tbody>
            {jobs.map((job) => (
              <tr
                key={job.id}
                className="border-b border-[#202938] last:border-b-0 hover:bg-[#121821]/60"
              >
                <td className="px-5 py-4">
                  <p className="font-mono text-xs font-medium text-[#3B82F6]">
                    {job.jobCode}
                  </p>

                  <p className="mt-1 max-w-[220px] text-sm text-[#F8FAFC]">
                    {job.title}
                  </p>

                  <p className="mt-1 text-[10px] text-[#64748B]">
                    {job.ticketCode}
                  </p>
                </td>

                <td className="px-4 py-4">
                  <p className="text-sm text-[#CBD5E1]">
                    {job.customerName}
                  </p>

                  <p className="mt-1 text-[11px] text-[#64748B]">
                    {job.area}
                  </p>
                </td>

                <td className="px-4 py-4">
                  <span
                    className={`border px-2 py-1 text-[10px] font-medium ${priorityStyles[job.priority]}`}
                  >
                    {job.priority}
                  </span>
                </td>

                <td className="px-4 py-4">
                  <span
                    className={`text-xs font-medium ${statusStyles[job.status]}`}
                  >
                    {job.status.replace("_", " ")}
                  </span>
                </td>

                <td className="px-4 py-4">
                  <p className="text-sm text-[#CBD5E1]">
                    {job.technicianName ?? "Unassigned"}
                  </p>

                  <p className="mt-1 text-[10px] text-[#64748B]">
                    {job.scheduledWindow}
                  </p>
                </td>

                <td className="px-4 py-4">
                  <p className="font-mono text-xs text-[#CBD5E1]">
                    {job.connectedNode}
                  </p>

                  {job.incidentCode && (
                    <div className="mt-1 flex items-center gap-1 text-[10px] text-[#A78BFA]">
                      <Link2 className="h-3 w-3" />
                      {job.incidentCode}
                    </div>
                  )}
                </td>

                <td className="px-4 py-4">
                  <div
                    className={
                      job.slaAtRisk
                        ? "text-[#EF4444]"
                        : "text-[#22C55E]"
                    }
                  >
                    <div className="flex items-center gap-1.5">
                      {job.slaAtRisk && (
                        <AlertTriangle className="h-3.5 w-3.5" />
                      )}

                      <span className="text-xs font-medium">
                        {job.slaRemaining}
                      </span>
                    </div>
                  </div>
                </td>

                <td className="px-4 py-4">
                  <button className="flex h-8 w-8 items-center justify-center text-[#64748B] transition-colors hover:bg-[#202938] hover:text-[#F8FAFC]">
                    <ArrowUpRight className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}