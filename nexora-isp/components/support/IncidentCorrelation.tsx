import {
  BrainCircuit,
  Link2,
  Network,
  Users,
} from "lucide-react";

import { ComplaintCorrelation } from "@/types/support";

interface IncidentCorrelationProps {
  correlation: ComplaintCorrelation;
}

export default function IncidentCorrelation({
  correlation,
}: IncidentCorrelationProps) {
  return (
    <section className="border border-[#8B5CF6]/30 bg-[#0D1117]">
      <div className="flex items-center justify-between border-b border-[#202938] px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center border border-[#8B5CF6]/30 bg-[#8B5CF6]/10">
            <BrainCircuit className="h-4 w-4 text-[#A78BFA]" />
          </div>

          <div>
            <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-[#8B5CF6]">
              Incident Correlation Engine
            </p>

            <h2 className="mt-1 text-sm font-semibold text-[#F8FAFC]">
              {correlation.title}
            </h2>
          </div>
        </div>

        <span className="border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-2.5 py-1 text-[11px] font-medium text-[#A78BFA]">
          {correlation.confidence}% correlation confidence
        </span>
      </div>

      <div className="p-5">
        <p className="max-w-4xl text-sm leading-6 text-[#94A3B8]">
          {correlation.description}
        </p>

        <div className="mt-5 grid grid-cols-2 gap-px border border-[#202938] bg-[#202938] lg:grid-cols-4">
          <div className="bg-[#121821] p-4">
            <div className="flex items-center gap-2 text-[#64748B]">
              <Network className="h-3.5 w-3.5" />
              <span className="text-[10px] uppercase tracking-wider">
                Common Node
              </span>
            </div>

            <p className="mt-2 font-mono text-sm font-medium text-[#F8FAFC]">
              {correlation.nodeCode}
            </p>
          </div>

          <div className="bg-[#121821] p-4">
            <div className="flex items-center gap-2 text-[#64748B]">
              <Link2 className="h-3.5 w-3.5" />
              <span className="text-[10px] uppercase tracking-wider">
                Complaints
              </span>
            </div>

            <p className="mt-2 text-sm font-medium text-[#F8FAFC]">
              {correlation.complaintCount} correlated
            </p>
          </div>

          <div className="bg-[#121821] p-4">
            <div className="flex items-center gap-2 text-[#64748B]">
              <Users className="h-3.5 w-3.5" />
              <span className="text-[10px] uppercase tracking-wider">
                Impact
              </span>
            </div>

            <p className="mt-2 text-sm font-medium text-[#F8FAFC]">
              {correlation.affectedCustomers} customers
            </p>
          </div>

          <div className="bg-[#121821] p-4">
            <p className="text-[10px] uppercase tracking-wider text-[#64748B]">
              Correlation Window
            </p>

            <p className="mt-2 text-sm font-medium text-[#F8FAFC]">
              {correlation.timeWindow}
            </p>
          </div>
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-[#202938] pt-4">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-[#64748B]">
              Linked Incident
            </p>

            <p className="mt-1 font-mono text-sm font-medium text-[#A78BFA]">
              {correlation.suggestedIncidentCode}
            </p>
          </div>

          <button className="h-9 border border-[#8B5CF6]/40 bg-[#8B5CF6]/10 px-4 text-xs font-medium text-[#C4B5FD] transition-colors hover:bg-[#8B5CF6]/20">
            Open Incident Intelligence
          </button>
        </div>
      </div>
    </section>
  );
}