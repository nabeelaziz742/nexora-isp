"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  BadgeAlert,
  Calendar,
  CheckCircle2,
  CircleAlert,
  Clock,
  Coins,
  CreditCard,
  FileSpreadsheet,
  Filter,
  LoaderCircle,
  MapPin,
  Phone,
  RefreshCw,
  Search,
  ShieldAlert,
  UserCheck,
  UserPlus,
  Users,
  X,
} from "lucide-react";

import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Skeleton from "@/components/ui/Skeleton";
import { ApiError } from "@/services/api-error";
import { Area, geoService } from "@/services/geo.service";
import {
  CreateAllocationPayload,
  DefaulterItem,
  recoveryService,
} from "@/services/recovery.service";
import { OperatorListItem, staffService } from "@/services/staff-service";

export default function DefaultersManagementPage() {
  const [defaulters, setDefaulters] = useState<DefaulterItem[]>([]);
  const [operators, setOperators] = useState<OperatorListItem[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [agingFilter, setAgingFilter] = useState("");
  const [allocationFilter, setAllocationFilter] = useState("");
  const [areaFilter, setAreaFilter] = useState("");

  // Allocate Modal
  const [selectedDefaulter, setSelectedDefaulter] = useState<DefaulterItem | null>(null);
  const [allocateForm, setAllocateForm] = useState<Partial<CreateAllocationPayload>>({
    priority: "HIGH",
  });
  const [isAllocating, setIsAllocating] = useState(false);
  const [modalError, setModalError] = useState("");

  const loadDefaulters = async () => {
    try {
      setIsLoading(true);
      setError("");

      const response = await recoveryService.getDefaulters({
        search: searchQuery || undefined,
        aging_bucket: agingFilter || undefined,
        has_active_allocation: allocationFilter || undefined,
        area: areaFilter || undefined,
      });

      setDefaulters(response);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load defaulter accounts.",
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

    geoService
      .getAreas({ status: "active" })
      .then(setAreas)
      .catch(() => setAreas([]));
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadDefaulters();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, agingFilter, allocationFilter, areaFilter]);

  const openAllocateModal = (defaulter: DefaulterItem) => {
    setSelectedDefaulter(defaulter);
    setAllocateForm({
      customer_id: defaulter.customer_id,
      service_account_id: defaulter.service_account_id,
      assigned_staff_id: operators[0]?.user_id || "",
      priority: "HIGH",
      outstanding_amount: defaulter.total_overdue,
      notes: `Defaulter allocation for ${defaulter.full_name} (${defaulter.overdue_invoices_count} overdue invoices).`,
    });
    setModalError("");
  };

  const handleAllocate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDefaulter || !allocateForm.assigned_staff_id) return;

    try {
      setIsAllocating(true);
      setModalError("");

      await recoveryService.createAllocation({
        customer_id: selectedDefaulter.customer_id,
        service_account_id: selectedDefaulter.service_account_id,
        assigned_staff_id: allocateForm.assigned_staff_id,
        priority: allocateForm.priority || "HIGH",
        due_date: allocateForm.due_date || null,
        notes: allocateForm.notes || undefined,
      });

      setSelectedDefaulter(null);
      loadDefaulters();
    } catch (err) {
      setModalError(
        err instanceof ApiError
          ? err.message
          : "Failed to allocate defaulter.",
      );
    } finally {
      setIsAllocating(false);
    }
  };

  // KPIs
  const totalDefaulters = defaulters.length;
  const unallocatedCount = defaulters.filter((d) => !d.active_allocation).length;
  const totalOverdueSum = defaulters.reduce(
    (acc, d) => acc + parseFloat(String(d.total_overdue || "0")),
    0,
  );
  const critical90PlusCount = defaulters.filter(
    (d) => d.aging_bucket === "90+",
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-red-400">
            Collections & Aging Engine
          </p>

          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
            Defaulter Accounts Workspace
          </h1>

          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            Track overdue subscribers, aging buckets (0–30, 31–60, 61–90, 90+ days), and allocate cases to recovery officers.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadDefaulters}
            className="flex h-10 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/60 px-4 text-sm font-medium text-slate-300 transition hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>

          <Link
            href="/allocations"
            className="flex h-10 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-500 shadow-lg shadow-blue-500/20"
          >
            <FileSpreadsheet className="h-4 w-4" />
            Active Allocations
          </Link>
        </div>
      </section>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Defaulters</span>
            <Users className="h-4 w-4 text-slate-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-100">{totalDefaulters}</p>
          <p className="mt-1 text-xs text-slate-500">Subscribers with overdue invoices</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Unallocated</span>
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-400">{unallocatedCount}</p>
          <p className="mt-1 text-xs text-slate-500">Need recovery officer assignment</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">90+ Days Critical</span>
            <ShieldAlert className="h-4 w-4 text-red-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-red-400">{critical90PlusCount}</p>
          <p className="mt-1 text-xs text-slate-500">High priority collection cases</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Overdue Amount</span>
            <Coins className="h-4 w-4 text-red-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-red-400">
            PKR {totalOverdueSum.toLocaleString()}
          </p>
          <p className="mt-1 text-xs text-slate-500">Real unpaid invoice balance</p>
        </div>
      </div>

      {/* Filters Toolbar */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search defaulters by name, customer ID, phone, internet ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-10 w-full rounded-lg border border-slate-700 bg-slate-950/80 pl-9 pr-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={agingFilter}
            onChange={(e) => setAgingFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Aging Buckets</option>
            <option value="0-30">0–30 Days Overdue</option>
            <option value="31-60">31–60 Days Overdue</option>
            <option value="61-90">61–90 Days Overdue</option>
            <option value="90+">90+ Days Critical</option>
          </select>

          <select
            value={allocationFilter}
            onChange={(e) => setAllocationFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Allocations</option>
            <option value="false">Unallocated Only</option>
            <option value="true">Allocated Only</option>
          </select>

          <select
            value={areaFilter}
            onChange={(e) => setAreaFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Areas</option>
            {areas.map((a) => (
              <option key={a.id} value={a.name}>
                {a.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={loadDefaulters} />}

      {/* Defaulters Table */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-14 w-full rounded-xl" />
          <Skeleton className="h-14 w-full rounded-xl" />
          <Skeleton className="h-14 w-full rounded-xl" />
          <Skeleton className="h-14 w-full rounded-xl" />
        </div>
      ) : defaulters.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="No defaulter accounts found"
          description="There are no overdue accounts matching the active filters. Great collection health!"
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow-xl backdrop-blur-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-slate-800 bg-slate-950/60 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-5 py-3.5">Subscriber</th>
                  <th className="px-4 py-3.5">Location</th>
                  <th className="px-4 py-3.5">Overdue Balance</th>
                  <th className="px-4 py-3.5">Aging Bucket</th>
                  <th className="px-4 py-3.5">Overdue Invoices</th>
                  <th className="px-4 py-3.5">Recovery Status</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {defaulters.map((item) => (
                  <tr
                    key={item.customer_id}
                    className="transition hover:bg-slate-800/40"
                  >
                    <td className="px-5 py-4">
                      <div>
                        <p className="font-semibold text-slate-100">
                          {item.full_name}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="font-mono text-xs text-blue-400">
                            {item.customer_number}
                          </span>
                          <span className="text-xs text-slate-500">
                            {item.phone}
                          </span>
                        </div>
                        {item.internet_id && (
                          <span className="mt-1 inline-block font-mono text-[11px] text-slate-400">
                            ID: {item.internet_id}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="px-4 py-4 text-xs">
                      <p className="text-slate-200">{item.area || "--"}</p>
                      <p className="text-slate-500">{item.city || "--"}</p>
                    </td>

                    <td className="px-4 py-4">
                      <span className="font-bold text-red-400">
                        PKR {parseFloat(String(item.total_overdue)).toLocaleString()}
                      </span>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Oldest: {item.oldest_due_date}
                      </p>
                    </td>

                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-semibold ${
                          item.aging_bucket === "90+"
                            ? "bg-red-500/20 text-red-300 border border-red-500/30"
                            : item.aging_bucket === "61-90"
                            ? "bg-orange-500/20 text-orange-300 border border-orange-500/30"
                            : item.aging_bucket === "31-60"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                        }`}
                      >
                        {item.aging_bucket} Days ({item.max_days_overdue}d)
                      </span>
                    </td>

                    <td className="px-4 py-4 text-xs">
                      <span className="font-semibold text-slate-200">
                        {item.overdue_invoices_count}
                      </span>{" "}
                      invoice{item.overdue_invoices_count > 1 ? "s" : ""}
                    </td>

                    <td className="px-4 py-4 text-xs">
                      {item.active_allocation ? (
                        <div className="space-y-1">
                          <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 font-medium text-amber-300">
                            Assigned: {item.active_allocation.assigned_staff_name}
                          </span>
                          <p className="text-[11px] text-slate-500">
                            Status: {item.active_allocation.status}
                          </p>
                        </div>
                      ) : item.active_promise ? (
                        <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-medium text-emerald-400">
                          <Clock className="h-3 w-3" />
                          Promise (PKR {parseFloat(item.active_promise.promised_amount).toLocaleString()})
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-md border border-slate-700 bg-slate-800 px-2 py-0.5 text-slate-400">
                          Unallocated
                        </span>
                      )}
                    </td>

                    <td className="px-5 py-4 text-right">
                      {item.active_allocation ? (
                        <Link
                          href="/allocations"
                          className="inline-flex items-center gap-1 text-xs font-medium text-blue-400 hover:text-blue-300"
                        >
                          View Case
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      ) : (
                        <button
                          onClick={() => openAllocateModal(item)}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-blue-500 shadow-md shadow-blue-500/20"
                        >
                          <UserPlus className="h-3.5 w-3.5" />
                          Allocate Officer
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Allocate Officer Modal */}
      {selectedDefaulter && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-slate-950/60">
              <div>
                <h3 className="text-base font-semibold text-slate-100">
                  Allocate Defaulter Case
                </h3>
                <p className="text-xs text-slate-400">
                  {selectedDefaulter.full_name} ({selectedDefaulter.customer_number})
                </p>
              </div>
              <button
                onClick={() => setSelectedDefaulter(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {modalError && (
              <div className="m-5 mb-0 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleAllocate} className="p-6 space-y-4">
              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 flex items-center justify-between text-xs">
                <div>
                  <span className="text-slate-500">Overdue Balance:</span>
                  <p className="font-bold text-red-400 text-sm">
                    PKR {parseFloat(String(selectedDefaulter.total_overdue)).toLocaleString()}
                  </p>
                </div>
                <div>
                  <span className="text-slate-500">Aging:</span>
                  <p className="font-semibold text-slate-200">
                    {selectedDefaulter.aging_bucket} Days ({selectedDefaulter.overdue_invoices_count} invoices)
                  </p>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">
                  Assign to Recovery Officer / Operator <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={allocateForm.assigned_staff_id || ""}
                  onChange={(e) =>
                    setAllocateForm({
                      ...allocateForm,
                      assigned_staff_id: e.target.value,
                    })
                  }
                  className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                >
                  <option value="">-- Select Officer --</option>
                  {operators.map((op) => (
                    <option key={op.user_id} value={op.user_id}>
                      {op.full_name} ({op.staff_code}) • {op.assigned_area_name || "All Areas"}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-300">
                    Priority Level
                  </label>
                  <select
                    value={allocateForm.priority || "HIGH"}
                    onChange={(e) =>
                      setAllocateForm({
                        ...allocateForm,
                        priority: e.target.value as any,
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
                    value={allocateForm.due_date || ""}
                    onChange={(e) =>
                      setAllocateForm({
                        ...allocateForm,
                        due_date: e.target.value,
                      })
                    }
                    className="mt-1 h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">
                  Operational Notes & Instructions
                </label>
                <textarea
                  rows={2}
                  value={allocateForm.notes || ""}
                  onChange={(e) =>
                    setAllocateForm({
                      ...allocateForm,
                      notes: e.target.value,
                    })
                  }
                  placeholder="Specific follow up instructions or contact preference..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2.5 text-xs text-slate-200 outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setSelectedDefaulter(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isAllocating || !allocateForm.assigned_staff_id}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {isAllocating && <LoaderCircle className="h-3.5 w-3.5 animate-spin" />}
                  Assign Case
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
