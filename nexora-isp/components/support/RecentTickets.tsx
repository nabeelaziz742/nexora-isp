import { Link2 } from "lucide-react";

import { SupportTicket } from "@/types/support";

interface RecentTicketsProps {
  tickets: SupportTicket[];
}

const priorityStyles = {
  LOW: "text-[#64748B]",
  MEDIUM: "text-[#3B82F6]",
  HIGH: "text-[#F59E0B]",
  CRITICAL: "text-[#EF4444]",
};

const statusStyles = {
  OPEN: "text-[#F59E0B]",
  INVESTIGATING: "text-[#A78BFA]",
  ASSIGNED: "text-[#3B82F6]",
  RESOLVED: "text-[#22C55E]",
};

export default function RecentTickets({
  tickets,
}: RecentTicketsProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-[#F8FAFC]">
          Recent Support Tickets
        </h2>

        <p className="mt-1 text-xs text-[#64748B]">
          Latest customer complaints and incident relationships
        </p>
      </div>

      <div>
        {tickets.map((ticket) => (
          <div
            key={ticket.id}
            className="border-b border-[#202938] p-4 last:border-b-0 hover:bg-[#121821]/50"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-[#3B82F6]">
                    {ticket.ticketCode}
                  </span>

                  <span className="text-[#334155]">·</span>

                  <span
                    className={`text-[10px] font-medium ${priorityStyles[ticket.priority]}`}
                  >
                    {ticket.priority}
                  </span>
                </div>

                <p className="mt-2 truncate text-sm font-medium text-[#F8FAFC]">
                  {ticket.subject}
                </p>

                <p className="mt-1 text-xs text-[#64748B]">
                  {ticket.customerName} · {ticket.customerCode}
                </p>
              </div>

              <span
                className={`shrink-0 text-[10px] font-medium ${statusStyles[ticket.status]}`}
              >
                {ticket.status}
              </span>
            </div>

            <div className="mt-3 flex items-center justify-between border-t border-[#202938] pt-3">
              <div className="flex items-center gap-3 text-[11px] text-[#64748B]">
                <span className="font-mono">
                  {ticket.connectedNode}
                </span>

                {ticket.incidentCode && (
                  <span className="flex items-center gap-1 text-[#A78BFA]">
                    <Link2 className="h-3 w-3" />
                    {ticket.incidentCode}
                  </span>
                )}
              </div>

              <span className="text-[11px] text-[#64748B]">
                {ticket.createdAt}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}