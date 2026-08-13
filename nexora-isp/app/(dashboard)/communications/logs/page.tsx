"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  CheckCircle2,
  Clock3,
  RotateCcw,
  Search,
  TriangleAlert,
  XCircle,
  RefreshCw,
  Eye,
  Download,
} from "lucide-react";

import { communicationsService } from "@/services/communications.service";

type CommunicationStatus =
  | "PENDING"
  | "QUEUED"
  | "SENT"
  | "DELIVERED"
  | "FAILED"
  | "RETRY";

interface CommunicationLog {
  id: string;
  customer_name: string | null;
  communication_provider_name: string | null;
  template_name: string | null;
  status: CommunicationStatus;
  provider_response: string | null;
  recipient: string | null;
  subject: string | null;
  message: string | null;
  created_at: string;
  updated_at?: string;
  is_connected?: boolean;
}

const PAGE_SIZE = 10;

export default function CommunicationLogsPage() {
  const [logs, setLogs] = useState<CommunicationLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [search, setSearch] = useState("");

  const [providerFilter, setProviderFilter] =
    useState("ALL");

  const [statusFilter, setStatusFilter] =
    useState("ALL");

  const [page, setPage] = useState(1);

  const [selectedLog, setSelectedLog] =
    useState<CommunicationLog | null>(null);

  const [detailsOpen, setDetailsOpen] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [retryingId, setRetryingId] = useState<string | null>(null);

  const loadLogs = useCallback(
    async (showRefresh = false) => {
      try {
        if (showRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        setError(null);

        const response =
          await communicationsService.getLogs();

        const items = Array.isArray(response)
          ? response
          : (response as any)?.results ?? [];

        setLogs(items);
      } catch (err) {
        console.error(err);

        setError(
          "Unable to load communication logs."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    loadLogs();

    const timer = setInterval(() => {
      loadLogs(true);
    }, 30000);

    return () => clearInterval(timer);
  }, [loadLogs]);

  function openDetails(log: CommunicationLog) {
    setSelectedLog(log);
    setDetailsOpen(true);
  }

  function closeDetails() {
    setSelectedLog(null);
    setDetailsOpen(false);
  }

  async function retryLog(log: CommunicationLog) {
    try {
      setRetryingId(log.id);

      const response =
        await communicationsService.retryLog(
          log.id,
        );

      if ((response as any)?.success) {
        await loadLogs(true);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setRetryingId(null);
    }
  }

  function exportCSV() {
    if (!filteredLogs.length) return;

    const headers = [
      "Customer",
      "Recipient",
      "Provider",
      "Template",
      "Status",
      "Response",
      "Created At",
    ];

    const rows = filteredLogs.map((log) => [
      log.customer_name ?? "",
      log.recipient ?? "",
      log.communication_provider_name ?? "",
      log.template_name ?? "",
      log.status,
      log.provider_response ?? "",
      new Date(log.created_at).toLocaleString(),
    ]);

    const csv = [
      headers.join(","),
      ...rows.map((r) =>
        r
          .map((v) => `"${String(v).replace(/"/g, '""')}"`)
          .join(","),
      ),
    ].join("\n");

    const blob = new Blob([csv], {
      type: "text/csv;charset=utf-8;",
    });

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;
    link.download = `communication_logs.csv`;

    link.click();

    URL.revokeObjectURL(url);
  }

  const stats = useMemo(() => {
    return {
      delivered: logs.filter(
        (x) => x.status === "DELIVERED"
      ).length,

      pending: logs.filter(
        (x) =>
          x.status === "PENDING" ||
          x.status === "QUEUED"
      ).length,

      failed: logs.filter(
        (x) => x.status === "FAILED"
      ).length,

      retry: logs.filter(
        (x) => x.status === "RETRY"
      ).length,
    };
  }, [logs]);

  const providers = useMemo(() => {
    const unique = new Set<string>();

    logs.forEach((log) => {
      if (log.communication_provider_name) {
        unique.add(log.communication_provider_name);
      }
    });

    return Array.from(unique);
  }, [logs]);

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchesSearch =
        [
          log.customer_name,
          log.communication_provider_name,
          log.template_name,
          log.status,
          log.provider_response,
          log.recipient,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(search.toLowerCase());

      const matchesProvider =
        providerFilter === "ALL"
          ? true
          : log.communication_provider_name ===
            providerFilter;

      const matchesStatus =
        statusFilter === "ALL"
          ? true
          : log.status === statusFilter;

      return (
        matchesSearch &&
        matchesProvider &&
        matchesStatus
      );
    });
  }, [
    logs,
    search,
    providerFilter,
    statusFilter,
  ]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredLogs.length / PAGE_SIZE)
  );

  const paginatedLogs = useMemo(() => {
    const start =
      (page - 1) * PAGE_SIZE;

    return filteredLogs.slice(
      start,
      start + PAGE_SIZE
    );
  }, [filteredLogs, page]);

  useEffect(() => {
    setPage(1);
  }, [
    search,
    providerFilter,
    statusFilter,
  ]);

  function badgeClasses(status: string) {
    switch (status) {
      case "DELIVERED":
        return "bg-green-500/10 text-green-400";

      case "FAILED":
        return "bg-red-500/10 text-red-400";

      case "PENDING":
      case "QUEUED":
        return "bg-amber-500/10 text-amber-400";

      default:
        return "bg-cyan-500/10 text-cyan-400";
    }
  }

  function StatusIcon(status: string) {
    switch (status) {
      case "DELIVERED":
        return CheckCircle2;

      case "FAILED":
        return XCircle;

      case "PENDING":
      case "QUEUED":
        return Clock3;

      default:
        return TriangleAlert;
    }
  }
    return (
    <div className="space-y-6 p-6">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.20em] text-green-400">
            Communication
          </p>

          <h1 className="mt-2 text-2xl font-semibold text-white">
            Communication Logs
          </h1>

          <p className="mt-2 text-sm text-[#64748B]">
            Delivery history, provider responses and retry management.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadLogs(true)}
            disabled={refreshing}
            className="flex items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 py-2 text-sm text-white transition hover:border-cyan-500"
          >
            <RefreshCw
              className={`h-4 w-4 ${
                refreshing ? "animate-spin" : ""
              }`}
            />
            Refresh
          </button>

          <button
            onClick={exportCSV}
            className="flex items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 py-2 text-sm text-white hover:border-green-500"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        </div>
      </div>

      {error && (
        <div className="border border-red-900 bg-red-950 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          {
            title: "Delivered",
            value: stats.delivered,
            color: "text-green-400",
          },
          {
            title: "Pending",
            value: stats.pending,
            color: "text-amber-400",
          },
          {
            title: "Failed",
            value: stats.failed,
            color: "text-red-400",
          },
          {
            title: "Retry Queue",
            value: stats.retry,
            color: "text-cyan-400",
          },
        ].map((card) => (
          <div
            key={card.title}
            className="border border-[#202938] bg-[#0D1117] p-5"
          >
            <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
              {card.title}
            </p>

            <h2
              className={`mt-4 text-3xl font-semibold ${card.color}`}
            >
              {card.value}
            </h2>
          </div>
        ))}
      </div>

      <div className="border border-[#202938] bg-[#0D1117]">
        <div className="flex flex-col gap-4 border-b border-[#202938] p-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative w-full max-w-md">
            <Search className="absolute left-3 top-3 h-4 w-4 text-[#64748B]" />

            <input
              value={search}
              onChange={(e) =>
                setSearch(e.target.value)
              }
              placeholder="Search logs..."
              className="w-full border border-[#202938] bg-[#080B10] py-2 pl-10 pr-4 text-sm text-white outline-none"
            />
          </div>

          <div className="flex gap-3">
            <select
              value={providerFilter}
              onChange={(e) =>
                setProviderFilter(e.target.value)
              }
              className="border border-[#202938] bg-[#080B10] px-3 py-2 text-sm text-white"
            >
              <option value="ALL">
                All Providers
              </option>

              {providers.map((provider) => (
                <option
                  key={provider}
                  value={provider}
                >
                  {provider}
                </option>
              ))}
            </select>

            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value)
              }
              className="border border-[#202938] bg-[#080B10] px-3 py-2 text-sm text-white"
            >
              <option value="ALL">
                All Status
              </option>

              <option value="DELIVERED">
                Delivered
              </option>

              <option value="PENDING">
                Pending
              </option>

              <option value="QUEUED">
                Queued
              </option>

              <option value="FAILED">
                Failed
              </option>

              <option value="RETRY">
                Retry
              </option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#202938] bg-[#080B10] text-left text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                <th className="px-5 py-4">
                  Customer
                </th>

                <th className="px-5 py-4">
                  Provider
                </th>

                <th className="px-5 py-4">
                  Template
                </th>

                <th className="px-5 py-4">
                  Status
                </th>

                <th className="px-5 py-4">
                  Response
                </th>

                <th className="px-5 py-4">
                  Created
                </th>

                <th className="px-5 py-4 text-right">
                  Action
                </th>
              </tr>
            </thead>

            <tbody>
              {loading && (
                <tr>
                  <td
                    colSpan={7}
                    className="px-5 py-10 text-center text-[#64748B]"
                  >
                    Loading communication logs...
                  </td>
                </tr>
              )}

              {!loading &&
                paginatedLogs.map((log) => {
                  const Icon =
                    StatusIcon(log.status);

                  return (
                    <tr
                      key={log.id}
                      className="border-b border-[#202938] hover:bg-[#080B10]"
                    >
                      <td className="px-5 py-4">
                        <div>
                          <h3 className="font-medium text-white">
                            {log.customer_name ??
                              "-"}
                          </h3>

                          <p className="mt-1 text-xs text-[#64748B]">
                            {log.recipient ??
                              "-"}
                          </p>
                        </div>
                      </td>

                      <td className="px-5 py-4 text-[#CBD5E1]">
                        {log.communication_provider_name ??
                          "-"}
                      </td>

                      <td className="px-5 py-4 text-[#CBD5E1]">
                        {log.template_name ??
                          "-"}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${badgeClasses(
                            log.status
                          )}`}
                        >
                          <Icon className="h-3.5 w-3.5" />

                          {log.status.replaceAll(
                            "_",
                            " "
                          )}
                        </span>
                      </td>

                                            <td className="px-5 py-4 text-[#CBD5E1]">
                        {log.provider_response ?? "-"}
                      </td>

                      <td className="px-5 py-4 text-[#94A3B8]">
                        {log.created_at
                          ? new Date(
                              log.created_at
                            ).toLocaleString()
                          : "-"}
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() =>
                              openDetails(log)
                            }
                            className="rounded-md border border-[#202938] bg-[#111827] p-2 transition hover:border-cyan-500"
                          >
                            <Eye className="h-4 w-4 text-cyan-400" />
                          </button>

                          <button
                            disabled={retryingId === log.id}
                            onClick={() => retryLog(log)}
                            className="rounded-md border border-[#202938] bg-[#111827] p-2 transition hover:border-amber-500 disabled:opacity-50"
                          >
                            <RotateCcw
                              className={`h-4 w-4 text-amber-400 ${
                                retryingId === log.id ? "animate-spin" : ""
                              }`}
                            />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}

              {!loading &&
                paginatedLogs.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-5 py-10 text-center text-[#64748B]"
                    >
                      No communication logs found.
                    </td>
                  </tr>
                )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-[#202938] px-5 py-4">
          <p className="text-sm text-[#64748B]">
            Showing{" "}
            <span className="text-white">
              {paginatedLogs.length}
            </span>{" "}
            of{" "}
            <span className="text-white">
              {filteredLogs.length}
            </span>{" "}
            logs
          </p>

          <div className="flex items-center gap-2">
            <button
              disabled={page === 1}
              onClick={() =>
                setPage((p) => p - 1)
              }
              className="rounded-md border border-[#202938] bg-[#080B10] px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              Previous
            </button>

            <span className="px-2 text-sm text-[#CBD5E1]">
              {page} / {totalPages}
            </span>

            <button
              disabled={page >= totalPages}
              onClick={() =>
                setPage((p) => p + 1)
              }
              className="rounded-md border border-[#202938] bg-[#080B10] px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {detailsOpen && selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6">
          <div className="w-full max-w-3xl border border-[#202938] bg-[#0D1117]">
            <div className="flex items-center justify-between border-b border-[#202938] px-6 py-4">
              <h2 className="text-lg font-semibold text-white">
                Communication Details
              </h2>

              <button
                onClick={closeDetails}
                className="text-sm text-[#94A3B8] hover:text-white"
              >
                Close
              </button>
            </div>

            <div className="space-y-6 p-6">
              <div className="grid gap-5 md:grid-cols-2">
                <div>
                  <p className="text-xs uppercase tracking-wide text-[#64748B]">
                    Customer
                  </p>

                  <p className="mt-2 text-white">
                    {selectedLog.customer_name ??
                      "-"}
                  </p>
                </div>

                <div>
                  <p className="text-xs uppercase tracking-wide text-[#64748B]">
                    Recipient
                  </p>

                  <p className="mt-2 text-white">
                    {selectedLog.recipient ??
                      "-"}
                  </p>
                </div>

                <div>
                  <p className="text-xs uppercase tracking-wide text-[#64748B]">
                    Provider
                  </p>

                  <p className="mt-2 text-white">
                    {selectedLog.communication_provider_name ??
                      "-"}
                  </p>
                </div>

                <div>
                  <p className="text-xs uppercase tracking-wide text-[#64748B]">
                    Template
                  </p>

                  <p className="mt-2 text-white">
                    {selectedLog.template_name ??
                      "-"}
                  </p>
                </div>

                <div>
                  <p className="text-xs uppercase tracking-wide text-[#64748B]">
                    Status
                  </p>

                  <p className="mt-2 text-white">
                    {selectedLog.status}
                  </p>
                </div>

                <div>
                  <p className="text-xs uppercase tracking-wide text-[#64748B]">
                    Created
                  </p>

                  <p className="mt-2 text-white">
                    {new Date(
                      selectedLog.created_at
                    ).toLocaleString()}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-wide text-[#64748B]">
                  Provider Response
                </p>

                <div className="mt-2 rounded-md border border-[#202938] bg-[#080B10] p-4 text-[#CBD5E1]">
                  {selectedLog.provider_response ??
                    "No provider response available."}
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-wide text-[#64748B]">
                  Message
                </p>

                <div className="mt-2 whitespace-pre-wrap rounded-md border border-[#202938] bg-[#080B10] p-4 text-[#CBD5E1]">
                  {selectedLog.message ??
                    "No message available."}
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-wide text-[#64748B]">
                  Subject
                </p>

                <div className="mt-2 rounded-md border border-[#202938] bg-[#080B10] p-4 text-[#CBD5E1]">
                  {selectedLog.subject ?? "-"}
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-wide text-[#64748B]">
                  Queue Status
                </p>

                <div className="mt-2 rounded-md border border-[#202938] bg-[#080B10] p-4 text-[#CBD5E1]">
                  {selectedLog.status}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
