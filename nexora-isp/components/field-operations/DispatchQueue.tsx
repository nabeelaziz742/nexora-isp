import {
  AlertTriangle,
  ArrowRight,
  Link2,
  MapPin,
} from "lucide-react";

import { DispatchJob } from "@/types/field-operations";

interface DispatchQueueProps {
  jobs: DispatchJob[];
}

const priorityStyles = {
  LOW: "text-[#64748B]",
  MEDIUM: "text-[#3B82F6]",
  HIGH: "text-[#F59E0B]",
  CRITICAL: "text-[#EF4444]",
};

export default function DispatchQueue({
  jobs,
}: DispatchQueueProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="flex items-center justify-between border-b border-[#202938] px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-[#F8FAFC]">
            Dispatch Queue
          </h2>

          <p className="mt-1 text-xs text-[#64748B]">
            Unassigned jobs waiting for technician dispatch
          </p>
        </div>

        <span className="border border-[#F59E0B]/20 bg-[#F59E0B]/10 px-2.5 py-1 text-[10px] font-medium text-[#F59E0B]">
          {jobs.length} WAITING
        </span>
      </div>

      <div>
        {jobs.map((job) => (
          <div
            key={job.id}
            className="border-b border-[#202938] p-4 last:border-b-0 hover:bg-[#121821]/50"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-[#3B82F6]">
                    {job.jobCode}
                  </span>

                  <span
                    className={`text-[10px] font-medium ${priorityStyles[job.priority]}`}
                  >
                    {job.priority}
                  </span>

                  {job.priority === "CRITICAL" && (
                    <AlertTriangle className="h-3 w-3 text-[#EF4444]" />
                  )}
                </div>

                <p className="mt-2 text-sm font-medium text-[#F8FAFC]">
                  {job.title}
                </p>

                <div className="mt-2 flex items-center gap-2 text-[11px] text-[#64748B]">
                  <MapPin className="h-3 w-3" />
                  {job.area}

                  <span>·</span>

                  <span className="font-mono">
                    {job.connectedNode}
                  </span>
                </div>
              </div>

              <span className="shrink-0 text-[11px] text-[#F59E0B]">
                Waiting {job.waitingTime}
              </span>
            </div>

            <div className="mt-3 flex items-center justify-between border-t border-[#202938] pt-3">
              <div className="flex items-center gap-3 text-[11px] text-[#64748B]">
                <span>{job.ticketCode}</span>

                {job.incidentCode && (
                  <span className="flex items-center gap-1 text-[#A78BFA]">
                    <Link2 className="h-3 w-3" />
                    {job.incidentCode}
                  </span>
                )}
              </div>

              <button className="flex items-center gap-2 text-xs font-medium text-[#3B82F6] transition-colors hover:text-[#60A5FA]">
                {job.suggestedTechnician
                  ? `Assign ${job.suggestedTechnician}`
                  : "Assign Technician"}

                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}