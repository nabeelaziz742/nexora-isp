import { ArrowUpRight } from "lucide-react";

import { NetworkIncident } from "@/types/support";

interface ActiveIncidentsTableProps {
  incidents: NetworkIncident[];
}

const severityStyles = {
  MINOR:
    "border-[#3B82F6]/20 bg-[#3B82F6]/10 text-[#60A5FA]",
  MAJOR:
    "border-[#F59E0B]/20 bg-[#F59E0B]/10 text-[#F59E0B]",
  CRITICAL:
    "border-[#EF4444]/20 bg-[#EF4444]/10 text-[#EF4444]",
};

const statusStyles = {
  DETECTED: "text-[#F59E0B]",
  INVESTIGATING: "text-[#A78BFA]",
  MITIGATING: "text-[#3B82F6]",
  RESOLVED: "text-[#22C55E]",
};

export default function ActiveIncidentsTable({
  incidents,
}: ActiveIncidentsTableProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-[#F8FAFC]">
          Active Network Incidents
        </h2>

        <p className="mt-1 text-xs text-[#64748B]">
          Customer impact and correlated support activity
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[850px] text-left">
          <thead>
            <tr className="border-b border-[#202938] bg-[#121821]/50">
              <th className="px-5 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Incident
              </th>
              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Node
              </th>
              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Severity
              </th>
              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Status
              </th>
              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Impact
              </th>
              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Tickets
              </th>
              <th className="px-4 py-3" />
            </tr>
          </thead>

          <tbody>
            {incidents.map((incident) => (
              <tr
                key={incident.id}
                className="border-b border-[#202938] last:border-b-0 hover:bg-[#121821]/60"
              >
                <td className="px-5 py-4">
                  <p className="font-mono text-xs font-medium text-[#3B82F6]">
                    {incident.incidentCode}
                  </p>

                  <p className="mt-1 text-sm text-[#F8FAFC]">
                    {incident.title}
                  </p>

                  <p className="mt-1 text-[11px] text-[#64748B]">
                    Detected {incident.detectedAt}
                  </p>
                </td>

                <td className="px-4 py-4">
                  <p className="font-mono text-xs text-[#CBD5E1]">
                    {incident.affectedNode}
                  </p>

                  <p className="mt-1 text-[11px] text-[#64748B]">
                    {incident.area}
                  </p>
                </td>

                <td className="px-4 py-4">
                  <span
                    className={`border px-2 py-1 text-[10px] font-medium ${severityStyles[incident.severity]}`}
                  >
                    {incident.severity}
                  </span>
                </td>

                <td className="px-4 py-4">
                  <span
                    className={`text-xs font-medium ${statusStyles[incident.status]}`}
                  >
                    {incident.status}
                  </span>
                </td>

                <td className="px-4 py-4">
                  <p className="text-sm font-medium text-[#F8FAFC]">
                    {incident.affectedCustomers}
                  </p>

                  <p className="mt-1 text-[11px] text-[#64748B]">
                    customers
                  </p>
                </td>

                <td className="px-4 py-4">
                  <p className="text-sm font-medium text-[#F8FAFC]">
                    {incident.linkedTickets}
                  </p>

                  <p className="mt-1 text-[11px] text-[#64748B]">
                    linked
                  </p>
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