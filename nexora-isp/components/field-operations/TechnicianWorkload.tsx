import {
  CircleDot,
  Navigation,
  UserCheck,
  Wrench,
} from "lucide-react";

import { Technician } from "@/types/field-operations";

interface TechnicianWorkloadProps {
  technicians: Technician[];
}

const statusStyles = {
  AVAILABLE: {
    label: "Available",
    color: "text-[#22C55E]",
    dot: "bg-[#22C55E]",
  },
  EN_ROUTE: {
    label: "En Route",
    color: "text-[#F59E0B]",
    dot: "bg-[#F59E0B]",
  },
  ON_SITE: {
    label: "On Site",
    color: "text-[#3B82F6]",
    dot: "bg-[#3B82F6]",
  },
  OFF_DUTY: {
    label: "Off Duty",
    color: "text-[#64748B]",
    dot: "bg-[#64748B]",
  },
};

export default function TechnicianWorkload({
  technicians,
}: TechnicianWorkloadProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-[#F8FAFC]">
          Technician Workload
        </h2>

        <p className="mt-1 text-xs text-[#64748B]">
          Field team availability and active assignments
        </p>
      </div>

      <div>
        {technicians.map((technician) => {
          const status = statusStyles[technician.status];

          return (
            <div
              key={technician.id}
              className="border-b border-[#202938] p-4 last:border-b-0 hover:bg-[#121821]/50"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-[#202938] bg-[#121821]">
                    {technician.status === "AVAILABLE" ? (
                      <UserCheck className="h-4 w-4 text-[#22C55E]" />
                    ) : technician.status === "EN_ROUTE" ? (
                      <Navigation className="h-4 w-4 text-[#F59E0B]" />
                    ) : (
                      <Wrench className="h-4 w-4 text-[#3B82F6]" />
                    )}
                  </div>

                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[#F8FAFC]">
                      {technician.name}
                    </p>

                    <p className="mt-1 font-mono text-[10px] text-[#64748B]">
                      {technician.technicianCode}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${status.dot}`}
                  />

                  <span
                    className={`text-[10px] font-medium ${status.color}`}
                  >
                    {status.label}
                  </span>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-3 gap-3 border-t border-[#202938] pt-3">
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-[#64748B]">
                    Area
                  </p>

                  <p className="mt-1 truncate text-xs text-[#CBD5E1]">
                    {technician.currentArea}
                  </p>
                </div>

                <div>
                  <p className="text-[9px] uppercase tracking-wider text-[#64748B]">
                    Active Jobs
                  </p>

                  <p className="mt-1 text-xs text-[#CBD5E1]">
                    {technician.activeJobs}
                  </p>
                </div>

                <div>
                  <p className="text-[9px] uppercase tracking-wider text-[#64748B]">
                    Completed
                  </p>

                  <p className="mt-1 text-xs text-[#CBD5E1]">
                    {technician.completedToday}
                  </p>
                </div>
              </div>

              {technician.currentJobCode && (
                <div className="mt-3 flex items-center gap-2 text-[10px] text-[#64748B]">
                  <CircleDot className="h-3 w-3" />
                  Current job
                  <span className="font-mono text-[#3B82F6]">
                    {technician.currentJobCode}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}