"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  ArrowRightLeft,
  Calendar,
  CheckCircle2,
  CircleAlert,
  Clock,
  Coins,
  CreditCard,
  Edit2,
  Eye,
  FileSpreadsheet,
  Filter,
  History,
  LoaderCircle,
  MapPin,
  Phone,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  UserCheck,
  UserCog,
  Users,
  X,
} from "lucide-react";

import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Skeleton from "@/components/ui/Skeleton";
import { ApiError } from "@/services/api-error";
import {
  AllocationPriority,
  AllocationStatus,
  ReassignAllocationPayload,
  RecoveryAllocationItem,
  recoveryService,
  StatusTransitionPayload,
} from "@/services/recovery.service";
import { OperatorListItem, staffService } from "@/services/staff-service";

export default function RecoveryAllocationsPage() {
  const [allocations, setAllocations] = useState<RecoveryAllocationItem[]>([]);
  const [operators, setOperators] = useState<OperatorListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [operatorFilter, setOperatorFilter] = useState("");

  // Detail Modal
  const [viewingAllocation, setViewingAllocation] = useState<RecoveryAllocationItem | null>(null);

  // Status Transition Modal
  const [statusModalAllocation, setStatusModalAllocation] = useState<RecoveryAllocationItem | null>(null);
  const [transitionForm, setTransitionForm] = useState<{
    new_status: AllocationStatus;
    notes: string;
  }>({
    new_status: "CONTACTED",
    notes: "",
  });
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [statusModalError, setStatusModalError] = useState("");

  // Reassign Modal
  const [reassignModalAllocation, setReassignModalAllocation] = useState<RecoveryAllocationItem | null>(null);
  const [reassignForm, setReassignForm] = useState<ReassignAllocationPayload>({
    new_assigned_staff_id: "",
    reassignment_reason: "",
    priority: "HIGH",
    notes: "",
  });
  const [isReassigning, setIsReassigning] = useState(false);
  const [reassignModalError, setReassignModalError] = useState("");

  const loadAllocations = async () => {
    try {
      setIsLoading(true);
      setError("");

      const response = await recoveryService.getAllocations({
        search: searchQuery || undefined,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        operator_id: operatorFilter || undefined,
      });

      setAllocations(response);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load recovery allocations.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    staffService
      .getOperators()
      .then(setOperators)
      .catch(() => setOperators([]));
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadAllocations();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, statusFilter, priorityFilter, operatorFilter]);

  const openStatusModal = (alloc: RecoveryAllocationItem) => {
    setStatusModalAllocation(alloc);
    setStatusModalError("");
    setTransitionForm({
      new_status:
        alloc.status === "ALLOCATED"
          ? "CONTACTED"
          : alloc.status === "CONTACTED"
          ? "PROMISE_RECEIVED"
          : alloc.status === "PROMISE_RECEIVED"
          ? "PAYMENT_COLLECTED"
          : "CONTACTED",
      notes: "",
    });
  };

  const handleStatusTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!statusModalAllocation) return;

    try {
      setIsTransitioning(true);
      setStatusModalError("");

      await recoveryService.transitionStatus(statusModalAllocation.id, {
        new_status: transitionForm.new_status,
        notes: transitionForm.notes || undefined,
      });

      setStatusModalAllocation(null);
      loadAllocations();
    } catch (err) {
      setStatusModalError(
        err instanceof ApiError
          ? err.message
          : "Failed to update recovery status.",
      );
    } finally {
      setIsTransitioning(false);
    }
  };

  const openReassignModal = (alloc: RecoveryAllocationItem) => {
    setReassignModalAllocation(alloc);
    setReassignModalError("");
    setReassignForm({
      new_assigned_staff_id: operators[0]?.user_id || "",
      reassignment_reason: "",
      priority: alloc.priority,
      notes: alloc.notes,
    });
  };

  const handleReassign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reassignModalAllocation || !reassignForm.new_assigned_staff_id) return;

    try {
      setIsReassigning(true);
      setReassignModalError("");

      await recoveryService.reassignAllocation(reassignModalAllocation.id, {
        new_assigned_staff_id: reassignForm.new_assigned_staff_id,
        reassignment_reason: reassignForm.reassignment_reason,
        priority: reassignForm.priority,
        notes: reassignForm.notes || undefined,
      });

      setReassignModalAllocation(null);
      loadAllocations();
    } catch (err) {
      setReassignModalError(
        err instanceof ApiError
          ? err.message
          : "Failed to reassign allocation.",
      );
    } finally {
      setIsReassigning(false);
    }
  };

  // KPIs
  const totalAllocations = allocations.length;
  const activeCases = allocations.filter(
    (a) =>
      a.status === "ALLOCATED" ||
      a.status === "IN_PROGRESS" ||
      a.status === "CONTACTED" ||
      a.status === "PROMISE_RECEIVED",
  ).length;
  const collectedCases = allocations.filter(
    (a) => a.status === "PAYMENT_COLLECTED" || a.status === "COMPLETED",
  ).length;
  const totalOutstanding = allocations
    .filter((a) => a.status !== "CANCELLED")
    .reduce((acc, a) => acc + parseFloat(a.outstanding_amount || "0"), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
            Recovery Operations
          </p>

          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
            Recovery Allocations Tracker
          </h1>

          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            Track active recovery workflows, follow up with defaulters, update collection states, and manage reassignments.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadAllocations}
            className="flex h-10 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/60 px-4 text-sm font-medium text-slate-300 transition hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>

          <Link
            href="/defaulters"
            className="flex h-10 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-500 shadow-lg shadow-blue-500/20"
          >
            <Plus className="h-4 w-4" />
            New Allocation
          </Link>
        </div>
      </section>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Allocations</span>
            <FileSpreadsheet className="h-4 w-4 text-blue-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-100">{totalAllocations}</p>
          <p className="mt-1 text-xs text-slate-500">Total cases in system</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Active Workflows</span>
            <Clock className="h-4 w-4 text-amber-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-400">{activeCases}</p>
          <p className="mt-1 text-xs text-slate-500">Currently in follow-up</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Collected / Resolved</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-400">{collectedCases}</p>
          <p className="mt-1 text-xs text-slate-500">Successfully completed</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Assigned Overdue</span>
            <Coins className="h-4 w-4 text-red-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-red-400">
            PKR {totalOutstanding.toLocaleString()}
          </p>
          <p className="mt-1 text-xs text-slate-500">Total recovery balance</p>
        </div>
      </div>

      {/* Filters Toolbar */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search by case number, subscriber name, phone, internet ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-10 w-full rounded-lg border border-slate-700 bg-slate-950/80 pl-9 pr-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="ALLOCATED">Allocated</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="CONTACTED">Contacted</option>
            <option value="PROMISE_RECEIVED">Promise Received</option>
            <option value="PAYMENT_COLLECTED">Payment Collected</option>
            <option value="NO_RESPONSE">No Response</option>
            <option value="FAILED">Failed</option>
            <option value="ESCALATED">Escalated</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Priorities</option>
            <option value="LOW">Low</option>
            <option value="NORMAL">Normal</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>

          <select
            value={operatorFilter}
            onChange={(e) => setOperatorFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Officers</option>
            {operators.map((op) => (
              <option key={op.user_id} value={op.user_id}>
                {op.full_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={loadAllocations} />}

      {/* Allocations Table */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-14 w-full rounded-xl" />
          <Skeleton className="h-14 w-full rounded-xl" />
          <Skeleton className="h-14 w-full rounded-xl" />
          <Skeleton className="h-14 w-full rounded-xl" />
        </div>
      ) : allocations.length === 0 ? (
        <EmptyState
          icon={FileSpreadsheet}
          title="No recovery allocations found"
          description="No recovery allocations match the active filters."
          actionLabel="Allocate Defaulter"
          actionHref="/defaulters"
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow-xl backdrop-blur-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-slate-800 bg-slate-950/60 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-5 py-3.5">Case #</th>
                  <th className="px-4 py-3.5">Subscriber</th>
                  <th className="px-4 py-3.5">Assigned Officer</th>
                  <th className="px-4 py-3.5">Outstanding</th>
                  <th className="px-4 py-3.5">Priority</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {allocations.map((item) => (
                  <tr
                    key={item.id}
                    className="transition hover:bg-slate-800/40"
                  >
                    <td className="px-5 py-4 font-mono text-xs text-blue-400">
                      <div>
                        <span>{item.allocation_number}</span>
                        {item.reassigned_from_number && (
                          <p className="text-[10px] text-slate-500 font-sans mt-0.5">
                            Reassigned from {item.reassigned_from_number}
                          </p>
                        )}
                      </div>
                    </td>

                    <td className="px-4 py-4">
                      <div>
                        <p className="font-semibold text-slate-100">
                          {item.customer_name}
                        </p>
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                          <span>{item.customer_phone}</span>
                          <span>•</span>
                          <span>{item.customer_area || item.customer_city || "Territory"}</span>
                        </div>
                        {item.linked_promise_number && (
                          <span className="mt-1 inline-flex items-center gap-1 rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-400 border border-emerald-500/20">
                            <Clock className="h-2.5 w-2.5" />
                            Promise {item.linked_promise_number}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="px-4 py-4 text-xs">
                      <p className="font-medium text-slate-200">
                        {item.assigned_staff_name}
                      </p>
                      <p className="text-slate-500">
                        Date: {item.assigned_date}
                      </p>
                    </td>

                    <td className="px-4 py-4">
                      <span className="font-bold text-red-400">
                        PKR {parseFloat(item.outstanding_amount).toLocaleString()}
                      </span>
                      {item.due_date && (
                        <p className="text-[11px] text-slate-500">
                          Due: {item.due_date}
                        </p>
                      )}
                    </td>

                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${
                          item.priority === "CRITICAL"
                            ? "bg-red-500/20 text-red-300 border border-red-500/30"
                            : item.priority === "HIGH"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                        }`}
                      >
                        {item.priority}
                      </span>
                    </td>

                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-semibold ${
                          item.status === "COMPLETED" || item.status === "PAYMENT_COLLECTED"
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                            : item.status === "PROMISE_RECEIVED"
                            ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                            : item.status === "CONTACTED"
                            ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                            : item.status === "CANCELLED"
                            ? "bg-slate-800 text-slate-400 border border-slate-700"
                            : item.status === "FAILED" || item.status === "ESCALATED"
                            ? "bg-red-500/20 text-red-300 border border-red-500/30"
                            : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        }`}
                      >
                        {item.status.replace("_", " ")}
                      </span>
                    </td>

                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setViewingAllocation(item)}
                          title="View Case Details"
                          className="rounded-lg border border-slate-700 bg-slate-800/80 p-1.5 text-slate-300 transition hover:bg-slate-700 hover:text-white"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </button>

                        {item.status !== "COMPLETED" && item.status !== "CANCELLED" && (
                          <>
                            <button
                              onClick={() => openStatusModal(item)}
                              title="Update Status"
                              className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-300 transition hover:bg-blue-500 hover:text-white"
                            >
                              Update Status
                            </button>

                            <button
                              onClick={() => openReassignModal(item)}
                              title="Reassign Officer"
                              className="rounded-lg border border-slate-700 bg-slate-800/80 p-1.5 text-slate-300 transition hover:bg-slate-700 hover:text-white"
                            >
                              <ArrowRightLeft className="h-3.5 w-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Case Details Drawer / Modal */}
      {viewingAllocation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-slate-950/60">
              <div>
                <h3 className="text-base font-semibold text-slate-100">
                  Recovery Case Details
                </h3>
                <p className="text-xs font-mono text-blue-400">
                  {viewingAllocation.allocation_number}
                </p>
              </div>
              <button
                onClick={() => setViewingAllocation(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <div>
                  <span className="text-slate-500">Subscriber Name:</span>
                  <p className="font-semibold text-slate-100 text-sm mt-0.5">
                    {viewingAllocation.customer_name}
                  </p>
                  <p className="text-slate-400 mt-0.5 font-mono">
                    {viewingAllocation.customer_number} • {viewingAllocation.customer_phone}
                  </p>
                </div>

                <div>
                  <span className="text-slate-500">Outstanding Overdue:</span>
                  <p className="font-bold text-red-400 text-base mt-0.5">
                    PKR {parseFloat(viewingAllocation.outstanding_amount).toLocaleString()}
                  </p>
                  <p className="text-slate-400 mt-0.5">
                    Assigned: {viewingAllocation.assigned_date}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-slate-500">Assigned Recovery Officer:</span>
                  <p className="font-medium text-slate-200 mt-0.5">
                    {viewingAllocation.assigned_staff_name}
                  </p>
                  <p className="text-slate-500 text-[11px]">
                    {viewingAllocation.assigned_staff_email}
                  </p>
                </div>

                <div>
                  <span className="text-slate-500">Current Lifecycle Status:</span>
                  <p className="font-semibold text-blue-400 mt-0.5">
                    {viewingAllocation.status}
                  </p>
                  <p className="text-slate-500 text-[11px]">
                    Priority: {viewingAllocation.priority}
                  </p>
                </div>

                {viewingAllocation.reassigned_from_number && (
                  <div className="col-span-2 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3">
                    <span className="font-semibold text-amber-300">Reassignment Delegation History:</span>
                    <p className="text-slate-300 mt-1">
                      Origin Case: <span className="font-mono text-amber-200">{viewingAllocation.reassigned_from_number}</span>
                    </p>
                    <p className="text-slate-400 mt-0.5">
                      Reason: {viewingAllocation.reassignment_reason}
                    </p>
                  </div>
                )}

                {viewingAllocation.notes && (
                  <div className="col-span-2">
                    <span className="text-slate-500">Operational Notes:</span>
                    <p className="text-slate-300 mt-1 bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                      {viewingAllocation.notes}
                    </p>
                  </div>
                )}
              </div>

              <div className="flex justify-end pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setViewingAllocation(null)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Status Transition Modal */}
      {statusModalAllocation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-slate-950/60">
              <div>
                <h3 className="text-base font-semibold text-slate-100">
                  Update Recovery Workflow
                </h3>
                <p className="text-xs text-slate-400">
                  Case {statusModalAllocation.allocation_number} • Current: {statusModalAllocation.status}
                </p>
              </div>
              <button
                onClick={() => setStatusModalAllocation(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {statusModalError && (
              <div className="m-5 mb-0 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{statusModalError}</span>
              </div>
            )}

            <form onSubmit={handleStatusTransition} className="p-6 space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-300">
                  New Status Transition <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={transitionForm.new_status}
                  onChange={(e) =>
                    setTransitionForm({
                      ...transitionForm,
                      new_status: e.target.value as AllocationStatus,
                    })
                  }
                  className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                >
                  <option value="IN_PROGRESS">In Progress (Reviewing)</option>
                  <option value="CONTACTED">Contacted (Called / Visited)</option>
                  <option value="PROMISE_RECEIVED">Promise Received (PTP Committed)</option>
                  <option value="PAYMENT_COLLECTED">Payment Collected (Paid by Customer)</option>
                  <option value="NO_RESPONSE">No Response / Unreachable</option>
                  <option value="FAILED">Failed / Refused Payment</option>
                  <option value="ESCALATED">Escalated to Management</option>
                  <option value="COMPLETED">Completed & Closed</option>
                  <option value="CANCELLED">Cancelled</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">
                  Follow-up Notes & Recovery Feedback
                </label>
                <textarea
                  rows={3}
                  value={transitionForm.notes}
                  onChange={(e) =>
                    setTransitionForm({
                      ...transitionForm,
                      notes: e.target.value,
                    })
                  }
                  placeholder="Record customer response, visit remarks, or promise agreement..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2.5 text-xs text-slate-200 outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setStatusModalAllocation(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isTransitioning}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {isTransitioning && <LoaderCircle className="h-3.5 w-3.5 animate-spin" />}
                  Save Transition
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reassign Modal */}
      {reassignModalAllocation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-slate-950/60">
              <div>
                <h3 className="text-base font-semibold text-slate-100">
                  Reassign Recovery Case
                </h3>
                <p className="text-xs text-slate-400">
                  From: {reassignModalAllocation.assigned_staff_name} ({reassignModalAllocation.allocation_number})
                </p>
              </div>
              <button
                onClick={() => setReassignModalAllocation(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {reassignModalError && (
              <div className="m-5 mb-0 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{reassignModalError}</span>
              </div>
            )}

            <form onSubmit={handleReassign} className="p-6 space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-300">
                  Transfer to Officer / Operator <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={reassignForm.new_assigned_staff_id}
                  onChange={(e) =>
                    setReassignForm({
                      ...reassignForm,
                      new_assigned_staff_id: e.target.value,
                    })
                  }
                  className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                >
                  <option value="">-- Select Officer --</option>
                  {operators
                    .filter((op) => op.user_id !== reassignModalAllocation.assigned_staff)
                    .map((op) => (
                      <option key={op.user_id} value={op.user_id}>
                        {op.full_name} ({op.staff_code}) • {op.assigned_area_name || "All Areas"}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">
                  Mandatory Reassignment Reason <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={reassignForm.reassignment_reason}
                  onChange={(e) =>
                    setReassignForm({
                      ...reassignForm,
                      reassignment_reason: e.target.value,
                    })
                  }
                  placeholder="e.g. Operator on medical leave, territory realignment"
                  className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-300">
                    Priority Level
                  </label>
                  <select
                    value={reassignForm.priority || "HIGH"}
                    onChange={(e) =>
                      setReassignForm({
                        ...reassignForm,
                        priority: e.target.value as AllocationPriority,
                      })
                    }
                    className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  >
                    <option value="LOW">Low</option>
                    <option value="NORMAL">Normal</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300">
                    Follow-up Deadline
                  </label>
                  <input
                    type="date"
                    value={reassignForm.due_date || ""}
                    onChange={(e) =>
                      setReassignForm({
                        ...reassignForm,
                        due_date: e.target.value,
                      })
                    }
                    className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">
                  Transfer Notes
                </label>
                <textarea
                  rows={2}
                  value={reassignForm.notes || ""}
                  onChange={(e) =>
                    setReassignForm({
                      ...reassignForm,
                      notes: e.target.value,
                    })
                  }
                  placeholder="Handover remarks or specific collector instructions..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2.5 text-xs text-slate-200 outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setReassignModalAllocation(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isReassigning || !reassignForm.new_assigned_staff_id || !reassignForm.reassignment_reason}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {isReassigning && <LoaderCircle className="h-3.5 w-3.5 animate-spin" />}
                  Confirm Reassignment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
