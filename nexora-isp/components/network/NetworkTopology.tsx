import {
  Network,
  RadioTower,
  Router,
} from "lucide-react";

import type { NetworkNode } from "@/types/network";

interface NetworkTopologyProps {
  nodes: NetworkNode[];
}

function NodeIcon({
  nodeType,
}: {
  nodeType: string;
}) {
  if (nodeType === "ROUTER") {
    return <Router className="h-5 w-5" />;
  }

  return <RadioTower className="h-5 w-5" />;
}

export default function NetworkTopology({
  nodes,
}: NetworkTopologyProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="flex items-center justify-between border-b border-[#202938] px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <Network className="h-4 w-4 text-[#3B82F6]" />

            <h2 className="text-sm font-semibold text-[#F8FAFC]">
              Infrastructure Overview
            </h2>
          </div>

          <p className="mt-1 text-xs text-[#64748B]">
            Registered network nodes and service distribution
          </p>
        </div>

        <div className="flex items-center gap-4 text-[11px] text-[#64748B]">
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[#22C55E]" />
            Active
          </div>

          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[#EF4444]" />
            Inactive
          </div>
        </div>
      </div>

      {nodes.length === 0 ? (
        <div className="flex min-h-56 items-center justify-center p-6">
          <p className="text-xs text-[#64748B]">
            No infrastructure nodes are available.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto p-5">
          <div className="grid min-w-[680px] grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {nodes.map((node) => (
              <div
                key={node.id}
                className={`border bg-[#121821] p-4 ${
                  node.is_active
                    ? "border-[#22C55E]/30"
                    : "border-[#EF4444]/30"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-[#202938] bg-[#0D1117] text-[#94A3B8]">
                      <NodeIcon nodeType={node.node_type} />
                    </div>

                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-[#F8FAFC]">
                        {node.name}
                      </p>

                      <p className="mt-0.5 truncate font-mono text-[10px] text-[#64748B]">
                        {node.code}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                      node.is_active
                        ? "bg-[#22C55E]"
                        : "bg-[#EF4444]"
                    }`}
                  />
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[#202938] pt-3">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-[#64748B]">
                      Type
                    </p>

                    <p className="mt-1 text-xs font-medium text-[#F8FAFC]">
                      {node.node_type.replaceAll("_", " ")}
                    </p>
                  </div>

                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-[#64748B]">
                      Assignments
                    </p>

                    <p className="mt-1 text-xs font-medium text-[#F8FAFC]">
                      {node.assignment_count}
                    </p>
                  </div>

                  <div className="col-span-2">
                    <p className="text-[10px] uppercase tracking-wider text-[#64748B]">
                      Location
                    </p>

                    <p className="mt-1 truncate text-xs font-medium text-[#F8FAFC]">
                      {node.location || "Not specified"}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}