"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  Loader2,
  Network,
  Search,
  SlidersHorizontal,
} from "lucide-react";

import { networkService } from "@/services/network.service";

import type {
  NetworkAssignment,
  NetworkNode,
} from "@/types/network";

interface NetworkAssignmentsTableProps {
  assignments: NetworkAssignment[];
  nodes: NetworkNode[];
}

type AssignmentStateFilter =
  | "ALL"
  | "ACTIVE"
  | "INACTIVE";

export default function NetworkAssignmentsTable({
  assignments: initialAssignments,
  nodes,
}: NetworkAssignmentsTableProps) {
  const [assignments, setAssignments] = useState<
    NetworkAssignment[]
  >(initialAssignments);

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] =
    useState("");

  const [stateFilter, setStateFilter] =
    useState<AssignmentStateFilter>("ALL");

  const [nodeFilter, setNodeFilter] =
    useState("ALL");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(
    null,
  );

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedSearch(search.trim());
    }, 400);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [search]);

  const loadAssignments = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const data =
        await networkService.getAssignments({
          search: debouncedSearch || undefined,
          active:
            stateFilter === "ALL"
              ? undefined
              : stateFilter === "ACTIVE",
          nodeId:
            nodeFilter === "ALL"
              ? undefined
              : nodeFilter,
        });

      setAssignments(data);
    } catch (requestError) {
      console.error(
        "Failed to load network assignments:",
        requestError,
      );

      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load network assignments.",
      );
    } finally {
      setLoading(false);
    }
  }, [
    debouncedSearch,
    nodeFilter,
    stateFilter,
  ]);

  useEffect(() => {
    void loadAssignments();
  }, [loadAssignments]);

  useEffect(() => {
    if (
      !debouncedSearch &&
      stateFilter === "ALL" &&
      nodeFilter === "ALL"
    ) {
      setAssignments(initialAssignments);
    }
  }, [
    debouncedSearch,
    initialAssignments,
    nodeFilter,
    stateFilter,
  ]);

  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-4 py-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Network className="h-4 w-4 text-[#3B82F6]" />

              <h2 className="text-sm font-semibold text-[#F8FAFC]">
                Network Assignments
              </h2>

              {loading && (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[#3B82F6]" />
              )}
            </div>

            <p className="mt-1 text-[11px] text-[#64748B]">
              Operational service-to-node assignments
              loaded from the network backend.
            </p>
          </div>

          <div className="flex flex-col gap-2 lg:flex-row">
            <div className="relative min-w-0 lg:w-64">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#64748B]" />

              <input
                type="search"
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
                placeholder="Search assignments..."
                className="h-9 w-full border border-[#202938] bg-[#090D12] pl-9 pr-3 text-xs text-[#F8FAFC] outline-none placeholder:text-[#475569] focus:border-[#3B82F6]/60"
              />
            </div>

            <div className="relative">
              <SlidersHorizontal className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#64748B]" />

              <select
                value={stateFilter}
                onChange={(event) =>
                  setStateFilter(
                    event.target
                      .value as AssignmentStateFilter,
                  )
                }
                className="h-9 min-w-36 appearance-none border border-[#202938] bg-[#090D12] pl-9 pr-8 text-xs text-[#94A3B8] outline-none focus:border-[#3B82F6]/60"
              >
                <option value="ALL">
                  All States
                </option>

                <option value="ACTIVE">
                  Active
                </option>

                <option value="INACTIVE">
                  Inactive
                </option>
              </select>
            </div>

            <select
              value={nodeFilter}
              onChange={(event) =>
                setNodeFilter(event.target.value)
              }
              className="h-9 min-w-44 border border-[#202938] bg-[#090D12] px-3 text-xs text-[#94A3B8] outline-none focus:border-[#3B82F6]/60"
            >
              <option value="ALL">
                All Network Nodes
              </option>

              {nodes.map((node) => (
                <option
                  key={node.id}
                  value={node.id}
                >
                  {node.code} — {node.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2 text-[10px] uppercase tracking-wider text-[#64748B]">
          <span>
            {assignments.length.toLocaleString()}
          </span>

          <span>
            assignments returned
          </span>

          {debouncedSearch && (
            <>
              <span>•</span>

              <span className="normal-case tracking-normal text-[#94A3B8]">
                Search: {debouncedSearch}
              </span>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="border-b border-[#EF4444]/20 bg-[#EF4444]/5 px-4 py-3">
          <p className="text-xs font-medium text-[#EF4444]">
            Unable to load network assignments
          </p>

          <p className="mt-1 text-[11px] text-[#94A3B8]">
            {error}
          </p>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1180px]">
          <thead>
            <tr className="border-b border-[#202938] bg-[#090D12]">
              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Customer
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Service
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Network Node
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Provisioning User
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                IP Address
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Assignment
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Assigned At
              </th>
            </tr>
          </thead>

          <tbody>
            {assignments.map((assignment) => (
              <tr
                key={assignment.id}
                className="border-b border-[#202938] last:border-b-0 hover:bg-[#121821]"
              >
                <td className="px-4 py-3">
                  <p className="text-xs font-medium text-[#E2E8F0]">
                    {assignment.customer_name}
                  </p>

                  <p className="mt-1 font-mono text-[10px] text-[#64748B]">
                    {assignment.customer_number}
                  </p>
                </td>

                <td className="px-4 py-3">
                  <p className="font-mono text-[11px] text-[#CBD5E1]">
                    {assignment.service_number}
                  </p>

                  <p className="mt-1 text-[10px] text-[#64748B]">
                    {assignment.service_status}
                  </p>
                </td>

                <td className="px-4 py-3">
                  <p className="text-xs text-[#CBD5E1]">
                    {assignment.network_node_name}
                  </p>

                  <p className="mt-1 font-mono text-[10px] text-[#3B82F6]">
                    {assignment.network_node_code}
                  </p>
                </td>

                <td className="px-4 py-3">
                  <span className="font-mono text-[11px] text-[#CBD5E1]">
                    {assignment.username || "—"}
                  </span>
                </td>

                <td className="px-4 py-3">
                  <span className="font-mono text-[11px] text-[#94A3B8]">
                    {assignment.ip_address || "—"}
                  </span>
                </td>

                <td className="px-4 py-3">
                  <span
                    className={`inline-flex border px-2 py-1 text-[10px] font-medium uppercase tracking-wider ${
                      assignment.is_active
                        ? "border-[#22C55E]/20 bg-[#22C55E]/10 text-[#22C55E]"
                        : "border-[#64748B]/20 bg-[#64748B]/10 text-[#94A3B8]"
                    }`}
                  >
                    {assignment.is_active
                      ? "Active"
                      : "Inactive"}
                  </span>
                </td>

                <td className="px-4 py-3">
                  <span className="text-[11px] text-[#94A3B8]">
                    {new Date(
                      assignment.assigned_at,
                    ).toLocaleString()}
                  </span>
                </td>
              </tr>
            ))}

            {!loading && assignments.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-12 text-center"
                >
                  <p className="text-xs font-medium text-[#94A3B8]">
                    No network assignments found
                  </p>

                  <p className="mt-1 text-[11px] text-[#64748B]">
                    The backend returned no assignments
                    for the current search or filters.
                  </p>
                </td>
              </tr>
            )}

            {loading && assignments.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-12 text-center"
                >
                  <Loader2 className="mx-auto h-4 w-4 animate-spin text-[#3B82F6]" />

                  <p className="mt-3 text-[11px] text-[#64748B]">
                    Loading network assignments...
                  </p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}