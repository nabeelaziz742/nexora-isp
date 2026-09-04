"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  BadgeAlert,
  Calendar,
  CheckCircle2,
  Clock,
  Coins,
  CreditCard,
  Eye,
  MapPin,
  Phone,
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
import { Area, geoService } from "@/services/geo.service";
import {
  OperatorListItem,
  OperatorWorkloadDetail,
  staffService,
} from "@/services/staff-service";

export default function OperatorsManagementPage() {
  const [operators, setOperators] = useState<OperatorListItem[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [areaFilter, setAreaFilter] = useState("");

  // Workload Detail Modal
  const [selectedOperatorId, setSelectedOperatorId] = useState<string | null>(null);
  const [workloadDetail, setWorkloadDetail] = useState<OperatorWorkloadDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  const loadOperators = async () => {
    try {
      setIsLoading(true);
      setError("");

      const response = await staffService.getOperators({
        search: searchQuery || undefined,
        area_id: areaFilter || undefined,
      });

      setOperators(response);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load operators directory.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    geoService
      .getAreas({ status: "active" })
      .then(setAreas)
      .catch(() => setAreas([]));
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadOperators();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, areaFilter]);

  const viewWorkload = async (userId: string) => {
    try {
      setSelectedOperatorId(userId);
      setIsLoadingDetail(true);
      const detail = await staffService.getOperatorWorkload(userId);
      setWorkloadDetail(detail);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load operator workload.",
      );
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // Overall calculations from real data
  const totalOperators = operators.length;
  const totalAssigned = operators.reduce(
    (acc, op) => acc + (op.workload?.total_assigned || 0),
    0,
  );
  const totalPromises = operators.reduce(
    (acc, op) => acc + (op.workload?.promises_count || 0),
    0,
  );
  const totalOutstanding = operators.reduce(
    (acc, op) =>
      acc + parseFloat(op.workload?.outstanding_assigned_amount || "0"),
    0,
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
            Field & Recovery Operations
          </p>

          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
            Operators & Recovery Officers
          </h1>

          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            Monitor recovery officers, active defaulter allocations, promises received, and collection workloads.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadOperators}
            className="flex h-10 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/60 px-4 text-sm font-medium text-slate-300 transition hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>

          <Link
            href="/defaulters"
            className="flex h-10 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-500 shadow-lg shadow-blue-500/20"
          >
            <Coins className="h-4 w-4" />
            Allocate Defaulters
          </Link>
        </div>
      </section>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Officers</span>
            <UserCheck className="h-4 w-4 text-blue-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-100">{totalOperators}</p>
          <p className="mt-1 text-xs text-slate-500">Active recovery staff</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Assigned Defaulters</span>
            <Users className="h-4 w-4 text-amber-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-400">{totalAssigned}</p>
          <p className="mt-1 text-xs text-slate-500">Live active allocations</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Promises Received</span>
            <Clock className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-400">{totalPromises}</p>
          <p className="mt-1 text-xs text-slate-500">Active PTP commitments</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Under Recovery</span>
            <Coins className="h-4 w-4 text-red-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-red-400">
            PKR {totalOutstanding.toLocaleString()}
          </p>
          <p className="mt-1 text-xs text-slate-500">Assigned overdue balance</p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search operators by name, staff code, phone, department..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-10 w-full rounded-lg border border-slate-700 bg-slate-950/80 pl-9 pr-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-3">
          <select
            value={areaFilter}
            onChange={(e) => setAreaFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Territories</option>
            {areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.city_name || "City"})
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={loadOperators} />}

      {/* Operator List Cards */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
      ) : operators.length === 0 ? (
        <EmptyState
          icon={UserCheck}
          title="No operators found"
          description="No recovery officers or operators registered in the organization."
          actionLabel="Add Staff Member"
          actionHref="/staff/add"
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {operators.map((op) => (
            <div
              key={op.membership_id}
              className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-xl backdrop-blur-sm transition hover:border-slate-700"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 font-bold text-blue-400">
                      {op.full_name[0] || "O"}
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-100">
                        {op.full_name}
                      </h3>
                      <p className="font-mono text-xs text-blue-400">
                        {op.staff_code}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`rounded-md px-2 py-0.5 text-[11px] font-medium ${
                      op.status === "ACTIVE"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {op.status}
                  </span>
                </div>

                <div className="mt-4 space-y-1.5 text-xs text-slate-400">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-3.5 w-3.5 text-slate-500" />
                    <span>
                      {op.assigned_area_name
                        ? `Territory: ${op.assigned_area_name}`
                        : "All Organization Areas"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Phone className="h-3.5 w-3.5 text-slate-500" />
                    <span>{op.phone || op.email}</span>
                  </div>
                </div>

                {/* Workload Metric Pills */}
                <div className="mt-4 grid grid-cols-3 gap-2 rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-center">
                  <div>
                    <span className="text-[11px] text-slate-500">Assigned</span>
                    <p className="mt-0.5 text-sm font-bold text-slate-200">
                      {op.workload?.total_assigned || 0}
                    </p>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500">Promises</span>
                    <p className="mt-0.5 text-sm font-bold text-emerald-400">
                      {op.workload?.promises_count || 0}
                    </p>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500">Collected</span>
                    <p className="mt-0.5 text-sm font-bold text-blue-400">
                      {op.workload?.payments_collected_count || 0}
                    </p>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between text-xs">
                  <span className="text-slate-500">Under Recovery:</span>
                  <span className="font-semibold text-red-400">
                    PKR {parseFloat(op.workload?.outstanding_assigned_amount || "0").toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800/80">
                <button
                  onClick={() => viewWorkload(op.user_id)}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 py-2 text-xs font-medium text-slate-200 transition hover:bg-slate-700"
                >
                  <Eye className="h-3.5 w-3.5" />
                  View Live Workload & Allocations
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Workload Modal */}
      {selectedOperatorId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-3xl rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-slate-950/60">
              <div>
                <h3 className="text-base font-semibold text-slate-100">
                  {workloadDetail?.full_name || "Operator"} Workload
                </h3>
                <p className="text-xs text-blue-400">
                  {workloadDetail?.staff_code} • {workloadDetail?.assigned_area_name || "Global Territory"}
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedOperatorId(null);
                  setWorkloadDetail(null);
                }}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              {isLoadingDetail ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-32 w-full" />
                </div>
              ) : workloadDetail ? (
                <>
                  <div className="grid grid-cols-4 gap-3">
                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-center">
                      <span className="text-[11px] text-slate-500">Active Cases</span>
                      <p className="mt-1 text-lg font-bold text-slate-100">
                        {workloadDetail.workload?.total_assigned || 0}
                      </p>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-center">
                      <span className="text-[11px] text-slate-500">Contacted</span>
                      <p className="mt-1 text-lg font-bold text-blue-400">
                        {workloadDetail.workload?.contacted_count || 0}
                      </p>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-center">
                      <span className="text-[11px] text-slate-500">Promises</span>
                      <p className="mt-1 text-lg font-bold text-emerald-400">
                        {workloadDetail.workload?.promises_count || 0}
                      </p>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-center">
                      <span className="text-[11px] text-slate-500">Outstanding</span>
                      <p className="mt-1 text-sm font-bold text-red-400">
                        PKR {parseFloat(workloadDetail.workload?.outstanding_assigned_amount || "0").toLocaleString()}
                      </p>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                      Active Recovery Cases ({workloadDetail.active_allocations.length})
                    </h4>

                    {workloadDetail.active_allocations.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-slate-800 p-6 text-center text-xs text-slate-500">
                        No active cases assigned to this operator.
                      </div>
                    ) : (
                      <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                        {workloadDetail.active_allocations.map((alloc) => (
                          <div
                            key={alloc.id}
                            className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/80 p-3 text-xs"
                          >
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-slate-100">
                                  {alloc.customer_name}
                                </span>
                                <span className="font-mono text-[11px] text-slate-500">
                                  ({alloc.customer_number})
                                </span>
                              </div>
                              <p className="mt-0.5 text-slate-400">
                                Case: {alloc.allocation_number} • Phone: {alloc.phone}
                              </p>
                            </div>

                            <div className="text-right">
                              <span className="font-bold text-red-400">
                                PKR {parseFloat(alloc.outstanding_amount).toLocaleString()}
                              </span>
                              <div className="mt-1 flex items-center justify-end gap-1.5">
                                <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-300">
                                  {alloc.status}
                                </span>
                                <span
                                  className={`rounded px-1.5 py-0.5 text-[10px] ${
                                    alloc.priority === "CRITICAL"
                                      ? "bg-red-500/20 text-red-300"
                                      : alloc.priority === "HIGH"
                                      ? "bg-amber-500/20 text-amber-300"
                                      : "bg-blue-500/20 text-blue-300"
                                  }`}
                                >
                                  {alloc.priority}
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              ) : null}

              <div className="flex justify-end pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedOperatorId(null);
                    setWorkloadDetail(null);
                  }}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
