import { MoreHorizontal } from "lucide-react";

import type { NetworkNode } from "@/types/network";

interface NetworkNodesTableProps {
  nodes: NetworkNode[];
}

export default function NetworkNodesTable({
  nodes,
}: NetworkNodesTableProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-[#F8FAFC]">
          Network Nodes
        </h2>

        <p className="mt-1 text-xs text-[#64748B]">
          Registered infrastructure and active service assignments
        </p>
      </div>

      {nodes.length === 0 ? (
        <div className="flex min-h-56 items-center justify-center p-6">
          <p className="text-xs text-[#64748B]">
            No network nodes are registered.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left">
            <thead>
              <tr className="border-b border-[#202938] bg-[#121821]/50">
                <th className="px-5 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Node
                </th>

                <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Type
                </th>

                <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Status
                </th>

                <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Management IP
                </th>

                <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Location
                </th>

                <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Assignments
                </th>

                <th className="px-4 py-3" />
              </tr>
            </thead>

            <tbody>
              {nodes.map((node) => (
                <tr
                  key={node.id}
                  className="border-b border-[#202938] transition-colors last:border-b-0 hover:bg-[#121821]/70"
                >
                  <td className="px-5 py-4">
                    <p className="text-sm font-medium text-[#F8FAFC]">
                      {node.name}
                    </p>

                    <p className="mt-1 font-mono text-[10px] text-[#64748B]">
                      {node.code}
                    </p>
                  </td>

                  <td className="px-4 py-4">
                    <span className="border border-[#3B82F6]/20 bg-[#3B82F6]/10 px-2 py-1 text-[10px] font-medium text-[#60A5FA]">
                      {node.node_type.replaceAll("_", " ")}
                    </span>
                  </td>

                  <td className="px-4 py-4">
                    <span
                      className={`inline-flex items-center gap-2 border px-2 py-1 text-[11px] font-medium ${
                        node.is_active
                          ? "border-[#22C55E]/20 bg-[#22C55E]/10 text-[#22C55E]"
                          : "border-[#EF4444]/20 bg-[#EF4444]/10 text-[#EF4444]"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          node.is_active
                            ? "bg-[#22C55E]"
                            : "bg-[#EF4444]"
                        }`}
                      />

                      {node.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>

                  <td className="px-4 py-4 font-mono text-xs text-[#94A3B8]">
                    {node.management_ip ?? "Not configured"}
                  </td>

                  <td className="px-4 py-4 text-xs text-[#94A3B8]">
                    {node.location || "Not specified"}
                  </td>

                  <td className="px-4 py-4 text-sm font-medium text-[#CBD5E1]">
                    {node.assignment_count}
                  </td>

                  <td className="px-4 py-4">
                    <button
                      type="button"
                      className="flex h-8 w-8 items-center justify-center text-[#64748B] transition-colors hover:bg-[#202938] hover:text-[#F8FAFC]"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}