"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Loader2,
  Search,
  ServerCog,
  XCircle,
} from "lucide-react";

import { networkService } from "@/services/network.service";

import type {
  ProvisioningAction,
  ProvisioningRequest,
  ProvisioningStatus,
} from "@/types/network";

interface ProvisioningRequestsTableProps {
  requests: ProvisioningRequest[];
}

type StatusFilter = ProvisioningStatus | "ALL";
type ActionFilter = ProvisioningAction | "ALL";

function formatDateTime(value: string | null) {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString();
}

function formatAction(action: ProvisioningAction) {
  switch (action) {
    case "ACTIVATE":
      return "Activate";

    case "SUSPEND":
      return "Suspend";

    case "RESTORE":
      return "Restore";

    case "CHANGE_PACKAGE":
      return "Change Package";

    default:
      return action;
  }
}

function getStatusStyles(status: ProvisioningStatus) {
  switch (status) {
    case "PENDING":
      return "border-[#F59E0B]/20 bg-[#F59E0B]/10 text-[#F59E0B]";

    case "PROCESSING":
      return "border-[#3B82F6]/20 bg-[#3B82F6]/10 text-[#3B82F6]";

    case "SUCCEEDED":
      return "border-[#22C55E]/20 bg-[#22C55E]/10 text-[#22C55E]";

    case "FAILED":
      return "border-[#EF4444]/20 bg-[#EF4444]/10 text-[#EF4444]";

    case "CANCELLED":
      return "border-[#64748B]/20 bg-[#64748B]/10 text-[#94A3B8]";

    default:
      return "border-[#64748B]/20 bg-[#64748B]/10 text-[#94A3B8]";
  }
}

function StatusIcon({
  status,
}: {
  status: ProvisioningStatus;
}) {
  switch (status) {
    case "PENDING":
      return <Clock3 className="h-3.5 w-3.5" />;

    case "PROCESSING":
      return <Loader2 className="h-3.5 w-3.5 animate-spin" />;

    case "SUCCEEDED":
      return <CheckCircle2 className="h-3.5 w-3.5" />;

    case "FAILED":
      return <AlertTriangle className="h-3.5 w-3.5" />;

    case "CANCELLED":
      return <XCircle className="h-3.5 w-3.5" />;

    default:
      return null;
  }
}

export default function ProvisioningRequestsTable({
  requests: initialRequests,
}: ProvisioningRequestsTableProps) {
  const [requests, setRequests] = useState<
    ProvisioningRequest[]
  >(initialRequests);

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] =
    useState("");

  const [statusFilter, setStatusFilter] =
    useState<StatusFilter>("ALL");

  const [actionFilter, setActionFilter] =
    useState<ActionFilter>("ALL");

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

  const loadRequests = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const data =
        await networkService.getProvisioningRequests({
          search: debouncedSearch || undefined,
          status:
            statusFilter === "ALL"
              ? undefined
              : statusFilter,
          action:
            actionFilter === "ALL"
              ? undefined
              : actionFilter,
        });

      setRequests(data);
    } catch (requestError) {
      console.error(
        "Failed to load provisioning requests:",
        requestError,
      );

      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load provisioning requests.",
      );
    } finally {
      setLoading(false);
    }
  }, [
    actionFilter,
    debouncedSearch,
    statusFilter,
  ]);

  useEffect(() => {
    void loadRequests();
  }, [loadRequests]);

  useEffect(() => {
    if (
      !debouncedSearch &&
      statusFilter === "ALL" &&
      actionFilter === "ALL"
    ) {
      setRequests(initialRequests);
    }
  }, [
    actionFilter,
    debouncedSearch,
    initialRequests,
    statusFilter,
  ]);

  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-4 py-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <ServerCog className="h-4 w-4 text-[#3B82F6]" />

              <h2 className="text-sm font-semibold text-[#F8FAFC]">
                Provisioning Operations
              </h2>

              {loading && (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[#3B82F6]" />
              )}
            </div>

            <p className="mt-1 text-[11px] text-[#64748B]">
              Service lifecycle provisioning requests
              recorded by the network backend.
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
                placeholder="Search provisioning..."
                className="h-9 w-full border border-[#202938] bg-[#090D12] pl-9 pr-3 text-xs text-[#F8FAFC] outline-none placeholder:text-[#475569] focus:border-[#3B82F6]/60"
              />
            </div>

            <select
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(
                  event.target.value as StatusFilter,
                )
              }
              className="h-9 min-w-40 border border-[#202938] bg-[#090D12] px-3 text-xs text-[#94A3B8] outline-none focus:border-[#3B82F6]/60"
            >
              <option value="ALL">
                All Statuses
              </option>

              <option value="PENDING">
                Pending
              </option>

              <option value="PROCESSING">
                Processing
              </option>

              <option value="SUCCEEDED">
                Succeeded
              </option>

              <option value="FAILED">
                Failed
              </option>

              <option value="CANCELLED">
                Cancelled
              </option>
            </select>

            <select
              value={actionFilter}
              onChange={(event) =>
                setActionFilter(
                  event.target.value as ActionFilter,
                )
              }
              className="h-9 min-w-44 border border-[#202938] bg-[#090D12] px-3 text-xs text-[#94A3B8] outline-none focus:border-[#3B82F6]/60"
            >
              <option value="ALL">
                All Actions
              </option>

              <option value="ACTIVATE">
                Activate
              </option>

              <option value="SUSPEND">
                Suspend
              </option>

              <option value="RESTORE">
                Restore
              </option>

              <option value="CHANGE_PACKAGE">
                Change Package
              </option>
            </select>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-wider text-[#64748B]">
          <span>
            {requests.length.toLocaleString()}
          </span>

          <span>
            requests returned
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
            Unable to load provisioning requests
          </p>

          <p className="mt-1 text-[11px] text-[#94A3B8]">
            {error}
          </p>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1540px]">
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
                Action
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Status
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Provider Reference
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Error
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Requested
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Started
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Completed
              </th>
            </tr>
          </thead>

          <tbody>
            {requests.map((request) => (
              <tr
                key={request.id}
                className="border-b border-[#202938] last:border-b-0 hover:bg-[#121821]"
              >
                <td className="px-4 py-3">
                  <p className="text-xs font-medium text-[#E2E8F0]">
                    {request.customer_name}
                  </p>

                  <p className="mt-1 font-mono text-[10px] text-[#64748B]">
                    {request.customer_number}
                  </p>
                </td>

                <td className="px-4 py-3">
                  <span className="font-mono text-[11px] text-[#CBD5E1]">
                    {request.service_number}
                  </span>
                </td>

                <td className="px-4 py-3">
                  <p className="text-xs text-[#CBD5E1]">
                    {request.network_node_name || "—"}
                  </p>

                  <p className="mt-1 font-mono text-[10px] text-[#3B82F6]">
                    {request.network_node_code || "—"}
                  </p>
                </td>

                <td className="px-4 py-3">
                  <span className="text-[11px] font-medium text-[#CBD5E1]">
                    {formatAction(request.action)}
                  </span>
                </td>

                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center gap-1.5 border px-2 py-1 text-[10px] font-medium uppercase tracking-wider ${getStatusStyles(
                      request.status,
                    )}`}
                  >
                    <StatusIcon
                      status={request.status}
                    />

                    {request.status}
                  </span>
                </td>

                <td className="px-4 py-3">
                  <span className="font-mono text-[11px] text-[#94A3B8]">
                    {request.provider_reference || "—"}
                  </span>
                </td>

                <td className="max-w-64 px-4 py-3">
                  <span
                    title={request.error_message || ""}
                    className={`block truncate text-[11px] ${
                      request.error_message
                        ? "text-[#EF4444]"
                        : "text-[#64748B]"
                    }`}
                  >
                    {request.error_message || "—"}
                  </span>
                </td>

                <td className="px-4 py-3">
                  <span className="whitespace-nowrap text-[11px] text-[#94A3B8]">
                    {formatDateTime(
                      request.requested_at,
                    )}
                  </span>
                </td>

                <td className="px-4 py-3">
                  <span className="whitespace-nowrap text-[11px] text-[#94A3B8]">
                    {formatDateTime(
                      request.started_at,
                    )}
                  </span>
                </td>

                <td className="px-4 py-3">
                  <span className="whitespace-nowrap text-[11px] text-[#94A3B8]">
                    {formatDateTime(
                      request.completed_at,
                    )}
                  </span>
                </td>
              </tr>
            ))}

            {!loading && requests.length === 0 && (
              <tr>
                <td
                  colSpan={10}
                  className="px-4 py-12 text-center"
                >
                  <p className="text-xs font-medium text-[#94A3B8]">
                    No provisioning requests found
                  </p>

                  <p className="mt-1 text-[11px] text-[#64748B]">
                    The backend returned no provisioning
                    requests for the current search or
                    filters.
                  </p>
                </td>
              </tr>
            )}

            {loading && requests.length === 0 && (
              <tr>
                <td
                  colSpan={10}
                  className="px-4 py-12 text-center"
                >
                  <Loader2 className="mx-auto h-4 w-4 animate-spin text-[#3B82F6]" />

                  <p className="mt-3 text-[11px] text-[#64748B]">
                    Loading provisioning requests...
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