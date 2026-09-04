"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Calendar,
  Clock,
  Eye,
  FileCode,
  Filter,
  RefreshCw,
  Search,
  Shield,
  ShieldCheck,
  User,
  Users,
  X,
} from "lucide-react";

import { auditService, type AuditLog } from "@/services/audit.service";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [resourceFilter, setResourceFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  // Inspector Modal
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const loadAuditLogs = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      const data = await auditService.getAuditLogs({
        action: actionFilter,
        resource_type: resourceFilter,
        start_date: startDate,
        end_date: endDate,
        search: search,
      });

      setLogs(data);
    } catch (err: any) {
      console.error("Failed to fetch audit logs:", err);
      setError(err?.message || "Failed to load tenant audit trail.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [actionFilter, resourceFilter, startDate, endDate, search]);

  useEffect(() => {
    const timer = setTimeout(() => {
      void loadAuditLogs();
    }, 250);
    return () => clearTimeout(timer);
  }, [loadAuditLogs]);

  // Distinct metrics
  const metrics = useMemo(() => {
    const actorsSet = new Set(logs.map((l) => l.actor_email).filter(Boolean));
    const securityEvents = logs.filter(
      (l) => l.action.includes("LOGIN") || l.action.includes("SECURITY") || l.action.includes("PROFILE")
    ).length;
    const popEvents = logs.filter((l) => l.action.includes("POP_SITE")).length;

    return [
      {
        id: "total-events",
        label: "Total Event Logs",
        value: logs.length.toLocaleString(),
        desc: "Tenant activity records",
        icon: ShieldCheck,
        color: "text-[#38BDF8]",
      },
      {
        id: "active-actors",
        label: "Distinct Actors",
        value: actorsSet.size.toLocaleString(),
        desc: "Staff & operator sessions",
        icon: Users,
        color: "text-[#22C55E]",
      },
      {
        id: "security-events",
        label: "Security & Auth",
        value: securityEvents.toLocaleString(),
        desc: "Logins & profile modifications",
        icon: Shield,
        color: "text-[#F59E0B]",
      },
      {
        id: "pop-events",
        label: "POP & Network",
        value: popEvents.toLocaleString(),
        desc: "Facility & node state changes",
        icon: FileCode,
        color: "text-[#A855F7]",
      },
    ];
  }, [logs]);

  const getActionBadgeClass = (action: string) => {
    if (action.includes("LOGIN") || action.includes("AUTH")) {
      return "border-[#38BDF8]/30 bg-[#38BDF8]/10 text-[#38BDF8]";
    }
    if (action.includes("POP_SITE") || action.includes("NETWORK")) {
      return "border-[#06B6D4]/30 bg-[#06B6D4]/10 text-[#06B6D4]";
    }
    if (action.includes("PAYMENT") || action.includes("INVOICE") || action.includes("BILLING")) {
      return "border-[#22C55E]/30 bg-[#22C55E]/10 text-[#22C55E]";
    }
    if (action.includes("POS") || action.includes("INVENTORY")) {
      return "border-[#F59E0B]/30 bg-[#F59E0B]/10 text-[#F59E0B]";
    }
    if (action.includes("PROFILE") || action.includes("STAFF")) {
      return "border-[#A855F7]/30 bg-[#A855F7]/10 text-[#A855F7]";
    }
    return "border-[#64748B]/30 bg-[#64748B]/10 text-[#94A3B8]";
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[#F8FAFC]">
            System Audit Trail & Investigation
          </h1>
          <p className="mt-1 text-sm text-[#64748B]">
            Immutable chronological record of administrative actions, authentication events, and facility changes.
          </p>
        </div>

        <button
          type="button"
          disabled={refreshing}
          onClick={() => void loadAuditLogs(true)}
          className="flex h-10 items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 text-xs font-medium text-[#94A3B8] transition-colors hover:bg-[#121821] hover:text-[#F8FAFC] disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin text-[#38BDF8]" : ""}`} />
          {refreshing ? "Refreshing..." : "Refresh Trail"}
        </button>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((m) => {
          const Icon = m.icon;
          return (
            <div key={m.id} className="border border-[#202938] bg-[#0D1117] p-4">
              <div className="flex items-center justify-between">
                <span className="text-[11px] uppercase tracking-wider text-[#64748B]">{m.label}</span>
                <Icon className={`h-4 w-4 ${m.color}`} />
              </div>
              <div className="mt-2 text-2xl font-bold tracking-tight text-[#F8FAFC]">{m.value}</div>
              <div className="mt-1 text-[11px] text-[#64748B]">{m.desc}</div>
            </div>
          );
        })}
      </div>

      {/* Search & Filters */}
      <div className="border border-[#202938] bg-[#0D1117] p-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-5">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#64748B]" />
            <input
              type="text"
              placeholder="Search action or resource..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full border border-[#202938] bg-[#161B22] py-2 pl-9 pr-3 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:border-[#38BDF8] focus:outline-none"
            />
          </div>

          <div>
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
            >
              <option value="">All Action Types</option>
              <option value="USER_LOGIN">User Login</option>
              <option value="POP_SITE">POP Infrastructure</option>
              <option value="COMPANY_PROFILE">Company Profile</option>
              <option value="PAYMENT">Payments & Billing</option>
              <option value="INVOICE">Invoices</option>
              <option value="STOCK">Inventory & POS</option>
              <option value="JOURNAL">Journal Entries</option>
            </select>
          </div>

          <div>
            <select
              value={resourceFilter}
              onChange={(e) => setResourceFilter(e.target.value)}
              className="w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
            >
              <option value="">All Resource Models</option>
              <option value="PointOfPresence">PointOfPresence</option>
              <option value="Organization">Organization</option>
              <option value="User">User</option>
              <option value="Invoice">Invoice</option>
              <option value="Payment">Payment</option>
              <option value="InventoryItem">InventoryItem</option>
              <option value="PosSale">PosSale</option>
              <option value="JournalEntry">JournalEntry</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-[#64748B]" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full border border-[#202938] bg-[#161B22] px-2 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-[#64748B]" />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full border border-[#202938] bg-[#161B22] px-2 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="border border-[#EF4444]/20 bg-[#EF4444]/5 p-3 text-xs text-[#EF4444]">
          {error}
        </div>
      )}

      {/* Audit Log Table */}
      <div className="overflow-x-auto border border-[#202938] bg-[#0D1117]">
        <table className="w-full text-left text-xs text-[#F8FAFC]">
          <thead className="border-b border-[#202938] bg-[#161B22] text-[11px] uppercase tracking-wider text-[#64748B]">
            <tr>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Actor / User</th>
              <th className="px-4 py-3">Action Event</th>
              <th className="px-4 py-3">Resource Target</th>
              <th className="px-4 py-3">Resource ID</th>
              <th className="px-4 py-3 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#202938]">
            {loading ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-xs text-[#64748B]">
                  Loading audit event records...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-xs text-[#64748B]">
                  No audit log records match the selected parameters.
                </td>
              </tr>
            ) : (
              logs.map((log) => {
                const badgeClass = getActionBadgeClass(log.action);
                const formattedDate = new Date(log.created_at).toLocaleString();

                return (
                  <tr key={log.id} className="transition-colors hover:bg-[#161B22]/50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 font-mono text-[11px] text-[#94A3B8]">
                        <Clock className="h-3 w-3 text-[#64748B]" />
                        {formattedDate}
                      </div>
                    </td>

                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <User className="h-3 w-3 text-[#38BDF8]" />
                        <span className="font-medium text-[#F8FAFC]">
                          {log.actor_name || "System Automated"}
                        </span>
                      </div>
                      {log.actor_email && (
                        <div className="text-[10px] text-[#64748B] pl-4.5">{log.actor_email}</div>
                      )}
                    </td>

                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center border px-2 py-0.5 font-mono text-[10px] font-medium tracking-wide ${badgeClass}`}>
                        {log.action}
                      </span>
                    </td>

                    <td className="px-4 py-3">
                      <span className="font-medium text-[#E2E8F0]">{log.resource_type}</span>
                    </td>

                    <td className="px-4 py-3">
                      <span className="font-mono text-[11px] text-[#64748B]">
                        {log.resource_id ? `${log.resource_id.substring(0, 18)}...` : "—"}
                      </span>
                    </td>

                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedLog(log)}
                        className="inline-flex items-center gap-1 border border-[#202938] bg-[#161B22] px-2.5 py-1 text-[11px] text-[#94A3B8] transition-colors hover:border-[#38BDF8] hover:text-[#38BDF8]"
                      >
                        <Eye className="h-3 w-3" />
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Metadata Inspector Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-2xl border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-3">
              <div>
                <h3 className="text-sm font-semibold text-[#F8FAFC]">
                  Audit Event Payload Inspector
                </h3>
                <p className="mt-0.5 font-mono text-[11px] text-[#38BDF8]">
                  ID: {selectedLog.id}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="text-[#64748B] hover:text-[#F8FAFC]"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3 border border-[#202938] bg-[#161B22] p-3">
                <div>
                  <span className="text-[#64748B]">Action:</span>
                  <span className="ml-2 font-mono font-semibold text-[#38BDF8]">{selectedLog.action}</span>
                </div>
                <div>
                  <span className="text-[#64748B]">Target Resource:</span>
                  <span className="ml-2 text-[#F8FAFC]">{selectedLog.resource_type} ({selectedLog.resource_id || "N/A"})</span>
                </div>
                <div>
                  <span className="text-[#64748B]">Actor:</span>
                  <span className="ml-2 text-[#F8FAFC]">{selectedLog.actor_name || selectedLog.actor_email || "System"}</span>
                </div>
                <div>
                  <span className="text-[#64748B]">Timestamp:</span>
                  <span className="ml-2 font-mono text-[#94A3B8]">{new Date(selectedLog.created_at).toISOString()}</span>
                </div>
              </div>

              <div>
                <label className="block text-[11px] uppercase tracking-wider text-[#64748B] mb-1">
                  Recorded Payload Metadata (JSON)
                </label>
                <pre className="max-h-[300px] overflow-auto border border-[#202938] bg-[#000000] p-3 font-mono text-[11px] leading-relaxed text-[#22C55E]">
                  {JSON.stringify(selectedLog.metadata, null, 2)}
                </pre>
              </div>
            </div>

            <div className="mt-4 flex justify-end border-t border-[#202938] pt-3">
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="border border-[#202938] bg-[#161B22] px-4 py-1.5 text-xs text-[#F8FAFC] hover:bg-[#202938]"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
