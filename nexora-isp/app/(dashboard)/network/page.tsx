"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  Activity,
  RefreshCw,
} from "lucide-react";

import NetworkAssignmentsTable from "@/components/network/NetworkAssignmentsTable";
import NetworkEvents from "@/components/network/NetworkEvents";
import NetworkMetricCard from "@/components/network/NetworkMetricCard";
import NetworkNodesTable from "@/components/network/NetworkNodesTable";
import NetworkTopology from "@/components/network/NetworkTopology";
import ProvisioningRequestsTable from "@/components/network/ProvisioningRequestsTable";

import { networkService } from "@/services/network.service";

import type {
  NetworkAssignment,
  NetworkMetric,
  NetworkNode,
  ProvisioningRequest,
} from "@/types/network";

export default function NetworkPage() {
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [assignments, setAssignments] = useState<
    NetworkAssignment[]
  >([]);
  const [
    provisioningRequests,
    setProvisioningRequests,
  ] = useState<ProvisioningRequest[]>([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] =
    useState(false);
  const [error, setError] = useState<
    string | null
  >(null);

  const loadNetworkData = useCallback(
    async (isRefresh = false) => {
      try {
        if (isRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        setError(null);

        const [
          nodesData,
          assignmentsData,
          provisioningData,
        ] = await Promise.all([
          networkService.getNodes(),
          networkService.getAssignments(),
          networkService.getProvisioningRequests(),
        ]);

        setNodes(nodesData);
        setAssignments(assignmentsData);
        setProvisioningRequests(provisioningData);
      } catch (requestError) {
        console.error(
          "Failed to load network dashboard:",
          requestError,
        );

        setError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to load network operations data.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadNetworkData();
  }, [loadNetworkData]);

  const metrics = useMemo<NetworkMetric[]>(() => {
    const activeNodes = nodes.filter(
      (node) => node.is_active,
    ).length;

    const activeAssignments = assignments.filter(
      (assignment) => assignment.is_active,
    ).length;

    const pendingRequests =
      provisioningRequests.filter(
        (request) =>
          request.status === "PENDING" ||
          request.status === "PROCESSING",
      ).length;

    const failedRequests =
      provisioningRequests.filter(
        (request) => request.status === "FAILED",
      ).length;

    return [
      {
        id: "total-nodes",
        label: "Total Nodes",
        value: nodes.length.toLocaleString(),
        description: "Registered infrastructure nodes",
        status: "neutral",
      },
      {
        id: "active-nodes",
        label: "Active Nodes",
        value: activeNodes.toLocaleString(),
        description: "Nodes enabled for operations",
        status:
          nodes.length > 0 &&
          activeNodes === nodes.length
            ? "healthy"
            : "warning",
      },
      {
        id: "active-assignments",
        label: "Active Assignments",
        value: activeAssignments.toLocaleString(),
        description: "Live service network assignments",
        status: "healthy",
      },
      {
        id: "provisioning-pending",
        label: "Pending Requests",
        value: pendingRequests.toLocaleString(),
        description:
          "Pending or processing provisioning",
        status:
          pendingRequests > 0
            ? "warning"
            : "healthy",
      },
      {
        id: "provisioning-failed",
        label: "Failed Requests",
        value: failedRequests.toLocaleString(),
        description:
          "Provisioning requests requiring review",
        status:
          failedRequests > 0
            ? "critical"
            : "healthy",
      },
      {
        id: "total-provisioning",
        label: "Provisioning Requests",
        value:
          provisioningRequests.length.toLocaleString(),
        description:
          "Recorded service lifecycle requests",
        status: "neutral",
      },
    ];
  }, [
    assignments,
    nodes,
    provisioningRequests,
  ]);

  const recentProvisioningRequests = useMemo(
    () => provisioningRequests.slice(0, 6),
    [provisioningRequests],
  );

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex min-h-[420px] items-center justify-center border border-[#202938] bg-[#0D1117]">
          <p className="text-xs text-[#64748B]">
            Loading network operations...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[#F8FAFC]">
            Network Operations Center
          </h1>

          <p className="mt-1 text-sm text-[#64748B]">
            Manage infrastructure nodes, service
            assignments and provisioning operations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 border border-[#202938] bg-[#0D1117] px-3 py-2">
            <Activity
              className={`h-3.5 w-3.5 ${
                error
                  ? "text-[#EF4444]"
                  : "text-[#22C55E]"
              }`}
            />

            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#64748B]">
                API Status
              </p>

              <p
                className={`text-xs font-medium ${
                  error
                    ? "text-[#EF4444]"
                    : "text-[#22C55E]"
                }`}
              >
                {error
                  ? "Unavailable"
                  : "Connected"}
              </p>
            </div>
          </div>

          <button
            type="button"
            disabled={refreshing}
            onClick={() => {
              void loadNetworkData(true);
            }}
            className="flex h-10 items-center gap-2 border border-[#202938] bg-[#0D1117] px-3 text-xs font-medium text-[#94A3B8] transition-colors hover:bg-[#121821] hover:text-[#F8FAFC] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${
                refreshing
                  ? "animate-spin"
                  : ""
              }`}
            />

            {refreshing
              ? "Refreshing"
              : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="border border-[#EF4444]/20 bg-[#EF4444]/5 px-4 py-3">
          <p className="text-xs font-medium text-[#EF4444]">
            Unable to load network data
          </p>

          <p className="mt-1 text-[11px] text-[#94A3B8]">
            {error}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {metrics.map((metric) => (
          <NetworkMetricCard
            key={metric.id}
            metric={metric}
          />
        ))}
      </div>

      <NetworkTopology nodes={nodes} />

      <div className="grid grid-cols-1 gap-6 2xl:grid-cols-[minmax(0,1fr)_420px]">
        <NetworkNodesTable nodes={nodes} />

        <NetworkEvents
          events={recentProvisioningRequests}
        />
      </div>

      <NetworkAssignmentsTable
        assignments={assignments}
        nodes={nodes}
      />

      <ProvisioningRequestsTable
        requests={provisioningRequests}
      />
    </div>
  );
}