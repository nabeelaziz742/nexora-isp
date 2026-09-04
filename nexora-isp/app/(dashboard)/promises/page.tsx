"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  Clock,
  DollarSign,
  Filter,
  Plus,
  Receipt,
  RefreshCw,
  Search,
  User,
  Users,
  X,
  XCircle,
} from "lucide-react";

import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Skeleton from "@/components/ui/Skeleton";
import {
  promisesService,
  type PromiseCreatePayload,
  type PromiseStatus,
  type PromiseToPayItem,
} from "@/services/promises.service";
import { customersService, type CustomerListItem } from "@/services/customers.service";

const STATUS_CONFIG: Record<
  PromiseStatus,
  { label: string; badgeClass: string }
> = {
  PENDING: {
    label: "Pending",
    badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  },
  ACTIVE: {
    label: "Active (In Grace)",
    badgeClass: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  },
  FULFILLED: {
    label: "Fulfilled (Paid)",
    badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  },
  BROKEN: {
    label: "Broken",
    badgeClass: "bg-rose-500/10 text-rose-400 border-rose-500/30",
  },
  EXPIRED: {
    label: "Expired",
    badgeClass: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  },
  CANCELLED: {
    label: "Cancelled",
    badgeClass: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
  },
};

export default function PromisesPage() {
  const [promises, setPromises] = useState<PromiseToPayItem[]>([]);
  const [customers, setCustomers] = useState<CustomerListItem[]>([]);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<PromiseStatus | "">("");
  const [showFilters, setShowFilters] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals & Action States
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showTransitionModal, setShowTransitionModal] = useState(false);
  const [selectedPromise, setSelectedPromise] = useState<PromiseToPayItem | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Create Form State
  const [newPromise, setNewPromise] = useState<{
    customer_id: string;
    service_account_id: string;
    invoice_id: string;
    promised_amount: string | number;
    promise_date: string;
    deadline: string;
    notes: string;
    status: PromiseStatus;
  }>({
    customer_id: "",
    service_account_id: "",
    invoice_id: "",
    promised_amount: "",
    promise_date: new Date().toISOString().split("T")[0],
    deadline: new Date(Date.now() + 5 * 86400000).toISOString().split("T")[0],
    notes: "",
    status: "ACTIVE",
  });

  // Transition Form State
  const [transitionForm, setTransitionForm] = useState<{
    status: PromiseStatus;
    failure_reason: string;
    notes: string;
  }>({
    status: "FULFILLED",
    failure_reason: "",
    notes: "",
  });

  // Load customer list for dropdown
  useEffect(() => {
    async function loadCustomers() {
      try {
        const custList = await customersService.getCustomers();
        setCustomers(custList);
      } catch {
        // Silently handle
      }
    }
    loadCustomers();
  }, []);

  // Fetch Promises
  const fetchPromises = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await promisesService.getPromises({
        status: statusFilter || undefined,
        search: search.trim() || undefined,
      });
      setPromises(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load promises.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPromises();
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPromises();
  };

  // Stats
  const stats = useMemo(() => {
    const total = promises.length;
    const active = promises.filter((p) => p.status === "ACTIVE" || p.status === "PENDING").length;
    const fulfilled = promises.filter((p) => p.status === "FULFILLED").length;
    const brokenOrExpired = promises.filter((p) => p.status === "BROKEN" || p.status === "EXPIRED").length;
    return { total, active, fulfilled, brokenOrExpired };
  }, [promises]);

  // Create Promise Submit
  const handleCreatePromise = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);
    try {
      await promisesService.createPromise({
        customer_id: newPromise.customer_id,
        service_account_id: newPromise.service_account_id || undefined as unknown as string,
        invoice_id: newPromise.invoice_id || undefined,
        promised_amount: Number(newPromise.promised_amount) || 0,
        promise_date: newPromise.promise_date,
        deadline: newPromise.deadline,
        notes: newPromise.notes,
        status: newPromise.status,
      });
      setShowCreateModal(false);
      fetchPromises();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to create promise to pay.");
    } finally {
      setFormSubmitting(false);
    }
  };

  // Status Transition Submit
  const handleTransitionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPromise) return;
    setFormSubmitting(true);
    setFormError(null);
    try {
      await promisesService.transitionStatus(selectedPromise.id, {
        status: transitionForm.status,
        failure_reason: transitionForm.failure_reason,
        notes: transitionForm.notes,
      });
      setShowTransitionModal(false);
      fetchPromises();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to transition status.");
    } finally {
      setFormSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Promise-to-Pay (PTP) Management
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Track subscriber payment commitments, manage extended grace periods, prevent duplicate promises, and verify real payment receipts.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchPromises()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => {
              setFormError(null);
              setShowCreateModal(true);
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 transition shadow-emerald-950/20"
          >
            <Plus className="h-4 w-4" />
            Record Promise
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <Clock className="h-4 w-4 text-blue-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Total Commitments</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-white">{stats.total}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <Calendar className="h-4 w-4 text-amber-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Active In Grace</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-400">{stats.active}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Fulfilled (Paid)</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-400">{stats.fulfilled}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <XCircle className="h-4 w-4 text-rose-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Broken / Expired</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-rose-400">{stats.brokenOrExpired}</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-sm space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <form onSubmit={handleSearchSubmit} className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by promise #, customer name, customer #, or service #..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950/80 pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </form>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition ${
                showFilters || statusFilter
                  ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400"
                  : "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              <Filter className="h-4 w-4" />
              Status Filter
              {statusFilter && <span className="h-2 w-2 rounded-full bg-emerald-400" />}
            </button>
            {(search || statusFilter) && (
              <button
                onClick={() => {
                  setSearch("");
                  setStatusFilter("");
                }}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-2 text-xs font-medium text-slate-400 hover:text-white transition"
              >
                <X className="h-3.5 w-3.5" />
                Clear
              </button>
            )}
          </div>
        </div>

        {showFilters && (
          <div className="pt-3 border-t border-slate-800">
            <label className="block text-xs font-medium text-slate-400 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as PromiseStatus | "")}
              className="w-full max-w-xs rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
            >
              <option value="">All Statuses</option>
              {Object.entries(STATUS_CONFIG).map(([key, { label }]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={fetchPromises} />
      ) : promises.length === 0 ? (
        <EmptyState
          icon={Clock}
          title="No promises recorded"
          description="No promise-to-pay commitments match your current search and filter criteria."
          actionLabel="Record First Promise"
          onActionClick={() => setShowCreateModal(true)}
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-slate-800 bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 pl-4 pr-3 font-semibold">Promise #</th>
                  <th className="px-3 py-3.5 font-semibold">Subscriber</th>
                  <th className="px-3 py-3.5 font-semibold">Service #</th>
                  <th className="px-3 py-3.5 font-semibold">Promised Amount</th>
                  <th className="px-3 py-3.5 font-semibold">Commitment Date</th>
                  <th className="px-3 py-3.5 font-semibold">Deadline</th>
                  <th className="px-3 py-3.5 font-semibold">Status</th>
                  <th className="py-3.5 pl-3 pr-4 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {promises.map((item) => {
                  const statusConf = STATUS_CONFIG[item.status] || {
                    label: item.status,
                    badgeClass: "bg-slate-500/10 text-slate-400 border-slate-500/30",
                  };
                  return (
                    <tr key={item.id} className="hover:bg-slate-800/30 transition">
                      <td className="whitespace-nowrap py-4 pl-4 pr-3 font-mono text-xs font-semibold text-emerald-400">
                        {item.promise_number}
                      </td>
                      <td className="px-3 py-4">
                        <div className="font-semibold text-white">{item.customer_name}</div>
                        <div className="text-xs font-mono text-slate-400">{item.customer_number}</div>
                      </td>
                      <td className="px-3 py-4 text-xs font-mono text-slate-300">
                        {item.service_number}
                      </td>
                      <td className="px-3 py-4 text-xs">
                        <div className="font-bold text-emerald-400">
                          PKR {Number(item.promised_amount).toLocaleString()}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          Due: PKR {Number(item.outstanding_amount).toLocaleString()}
                        </div>
                      </td>
                      <td className="px-3 py-4 text-xs text-slate-300">{item.promise_date}</td>
                      <td className="px-3 py-4 text-xs font-medium text-amber-400">{item.deadline}</td>
                      <td className="px-3 py-4">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusConf.badgeClass}`}
                        >
                          {statusConf.label}
                        </span>
                      </td>
                      <td className="py-4 pl-3 pr-4 text-right">
                        {item.status === "ACTIVE" || item.status === "PENDING" ? (
                          <button
                            onClick={() => {
                              setSelectedPromise(item);
                              setTransitionForm({
                                status: "FULFILLED",
                                failure_reason: "",
                                notes: "",
                              });
                              setFormError(null);
                              setShowTransitionModal(true);
                            }}
                            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                          >
                            Update Status
                          </button>
                        ) : (
                          <span className="text-xs text-slate-500">Completed</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CREATE PROMISE MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-white">Record Promise-to-Pay</h3>
                <p className="text-xs text-slate-400">Establish formal payment commitment & temporary grace period</p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreatePromise} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Select Subscriber <span className="text-rose-400">*</span>
                </label>
                <select
                  required
                  value={newPromise.customer_id}
                  onChange={(e) => {
                    const cust = customers.find((c) => c.id === e.target.value);
                    setNewPromise({
                      ...newPromise,
                      customer_id: e.target.value,
                    });
                  }}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  <option value="">Select customer account</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.customer_number} — {c.full_name} ({c.phone})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Promised Amount (PKR) <span className="text-rose-400">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="1"
                  required
                  value={newPromise.promised_amount}
                  onChange={(e) => setNewPromise({ ...newPromise, promised_amount: e.target.value })}
                  placeholder="e.g. 3500.00"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Promise Inception Date <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={newPromise.promise_date}
                    onChange={(e) => setNewPromise({ ...newPromise, promise_date: e.target.value })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Payment Deadline <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={newPromise.deadline}
                    onChange={(e) => setNewPromise({ ...newPromise, deadline: e.target.value })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Reason / Notes</label>
                <textarea
                  rows={2}
                  value={newPromise.notes}
                  onChange={(e) => setNewPromise({ ...newPromise, notes: e.target.value })}
                  placeholder="e.g. Subscriber requested extension until salary disbursement on 15th..."
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition"
                >
                  {formSubmitting ? "Recording..." : "Save Commitment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* STATUS TRANSITION MODAL */}
      {showTransitionModal && selectedPromise && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-white">Transition Promise Status</h3>
                <p className="text-xs text-slate-400 font-mono">{selectedPromise.promise_number}</p>
              </div>
              <button
                onClick={() => setShowTransitionModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleTransitionSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">New Status</label>
                <select
                  value={transitionForm.status}
                  onChange={(e) =>
                    setTransitionForm({ ...transitionForm, status: e.target.value as PromiseStatus })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  <option value="FULFILLED">FULFILLED (Paid in full/part via recorded payment)</option>
                  <option value="BROKEN">BROKEN (Deadline passed without payment)</option>
                  <option value="EXPIRED">EXPIRED (Terms expired)</option>
                  <option value="CANCELLED">CANCELLED (Revoked)</option>
                </select>
              </div>

              {transitionForm.status === "BROKEN" && (
                <div>
                  <label className="block text-xs font-medium text-rose-300 mb-1">Failure Reason</label>
                  <input
                    type="text"
                    required
                    value={transitionForm.failure_reason}
                    onChange={(e) => setTransitionForm({ ...transitionForm, failure_reason: e.target.value })}
                    placeholder="e.g. Subscriber failed to pay by grace deadline"
                    className="w-full rounded-lg border border-rose-700/50 bg-slate-950 px-3 py-2 text-sm text-white focus:border-rose-500 focus:outline-none"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Transition Remarks</label>
                <textarea
                  rows={2}
                  value={transitionForm.notes}
                  onChange={(e) => setTransitionForm({ ...transitionForm, notes: e.target.value })}
                  placeholder="Additional context or collection notes..."
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowTransitionModal(false)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition"
                >
                  {formSubmitting ? "Updating..." : "Confirm Status"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
