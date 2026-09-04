"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  BadgeAlert,
  BellRing,
  Calendar,
  CheckCircle2,
  Clock,
  Coins,
  CreditCard,
  FileSpreadsheet,
  Filter,
  History,
  LoaderCircle,
  Play,
  Power,
  RefreshCw,
  Search,
  Settings,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  Users,
  X,
  Zap,
} from "lucide-react";

import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Skeleton from "@/components/ui/Skeleton";
import { ApiError } from "@/services/api-error";
import { suspensionService } from "@/services/suspension.service";
import type {
  AutomatedRunResult,
  OverdueEligibilityItem,
  ServiceSuspensionLog,
  SuspensionDashboardMetrics,
  SuspensionPolicy,
} from "@/types/suspension";

export default function SuspensionsManagementPage() {
  const [activeTab, setActiveTab] = useState<"eligibility" | "suspended" | "history" | "policy">("eligibility");
  const [metrics, setMetrics] = useState<SuspensionDashboardMetrics | null>(null);
  const [eligibilityList, setEligibilityList] = useState<OverdueEligibilityItem[]>([]);
  const [historyList, setHistoryList] = useState<ServiceSuspensionLog[]>([]);
  const [policy, setPolicy] = useState<SuspensionPolicy | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [ptpFilter, setPtpFilter] = useState<string>("ALL");

  // Manual Suspend Modal State
  const [selectedForSuspend, setSelectedForSuspend] = useState<OverdueEligibilityItem | null>(null);
  const [suspendReason, setSuspendReason] = useState("");
  const [isSubmittingSuspend, setIsSubmittingSuspend] = useState(false);
  const [suspendModalError, setSuspendModalError] = useState("");

  // Manual Restore Modal State
  const [selectedForRestore, setSelectedForRestore] = useState<OverdueEligibilityItem | ServiceSuspensionLog | null>(null);
  const [restoreReason, setRestoreReason] = useState("");
  const [isSubmittingRestore, setIsSubmittingRestore] = useState(false);
  const [restoreModalError, setRestoreModalError] = useState("");

  // Automated Batch Run Modal State
  const [showRunConfirmModal, setShowRunConfirmModal] = useState(false);
  const [isRunningEngine, setIsRunningEngine] = useState(false);
  const [batchRunResult, setBatchRunResult] = useState<AutomatedRunResult | null>(null);

  // Policy form state
  const [policyForm, setPolicyForm] = useState<Partial<SuspensionPolicy>>({});
  const [isSavingPolicy, setIsSavingPolicy] = useState(false);
  const [policySaveSuccess, setPolicySaveSuccess] = useState(false);
  const [policySaveError, setPolicySaveError] = useState("");

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError("");
      const [metricsData, eligibilityData, historyData, policyData] = await Promise.all([
        suspensionService.getDashboardMetrics(),
        suspensionService.getOverdueEligibility(),
        suspensionService.getSuspensionHistory(),
        suspensionService.getPolicy(),
      ]);

      setMetrics(metricsData);
      setEligibilityList(eligibilityData);
      setHistoryList(historyData);
      setPolicy(policyData);
      setPolicyForm(policyData);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to load suspension workspace data.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleManualSuspend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedForSuspend) return;
    if (!suspendReason.trim()) {
      setSuspendModalError("A mandatory suspension reason is required.");
      return;
    }

    try {
      setIsSubmittingSuspend(true);
      setSuspendModalError("");
      await suspensionService.suspendService(selectedForSuspend.service_id, {
        reason: suspendReason.trim(),
        trigger_type: "MANUAL_STAFF",
      });
      setSelectedForSuspend(null);
      setSuspendReason("");
      await loadData();
    } catch (err) {
      if (err instanceof ApiError) {
        setSuspendModalError(err.message);
      } else {
        setSuspendModalError("Failed to suspend service account.");
      }
    } finally {
      setIsSubmittingSuspend(false);
    }
  };

  const handleManualRestore = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedForRestore) return;
    if (!restoreReason.trim()) {
      setRestoreModalError("A mandatory restoration reason is required.");
      return;
    }

    const serviceId = "service_id" in selectedForRestore 
      ? selectedForRestore.service_id 
      : selectedForRestore.service_account;

    try {
      setIsSubmittingRestore(true);
      setRestoreModalError("");
      await suspensionService.restoreService(serviceId, {
        reason: restoreReason.trim(),
        trigger_type: "MANUAL_STAFF",
      });
      setSelectedForRestore(null);
      setRestoreReason("");
      await loadData();
    } catch (err) {
      if (err instanceof ApiError) {
        setRestoreModalError(err.message);
      } else {
        setRestoreModalError("Failed to restore service account.");
      }
    } finally {
      setIsSubmittingRestore(false);
    }
  };

  const handleRunAutomatedEngine = async () => {
    try {
      setIsRunningEngine(true);
      const result = await suspensionService.runAutomatedEngine();
      setBatchRunResult(result);
      await loadData();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Error running automated suspension engine.");
      }
    } finally {
      setIsRunningEngine(false);
    }
  };

  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSavingPolicy(true);
      setPolicySaveError("");
      setPolicySaveSuccess(false);
      const updated = await suspensionService.updatePolicy(policyForm);
      setPolicy(updated);
      setPolicyForm(updated);
      setPolicySaveSuccess(true);
      setTimeout(() => setPolicySaveSuccess(false), 4000);
      await loadData();
    } catch (err) {
      if (err instanceof ApiError) {
        setPolicySaveError(err.message);
      } else {
        setPolicySaveError("Failed to update suspension policy.");
      }
    } finally {
      setIsSavingPolicy(false);
    }
  };

  // Filtered lists
  const filteredEligibility = eligibilityList.filter((item) => {
    const matchesSearch =
      item.customer_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.service_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.phone.includes(searchQuery);

    if (!matchesSearch) return false;

    if (ptpFilter === "PTP_EXEMPT") return item.is_ptp_exempt;
    if (ptpFilter === "SUSPENDABLE") return item.is_eligible_for_suspension;
    if (ptpFilter === "GRACE") return item.in_grace_period;
    return true;
  });

  const suspendedList = eligibilityList.filter(
    (item) => item.status === "SUSPENDED_NON_PAYMENT" || item.status === "SUSPENDED"
  );

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Suspension & Policy Center
            </h1>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500/10 px-2.5 py-0.5 text-xs font-medium text-red-400 border border-red-500/20">
              <ShieldAlert className="h-3 w-3" />
              Automated Lifecycle
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Authoritative overdue enforcement, Promise-to-Pay protection, auto-suspension & instant payment restoration.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3.5 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>

          <button
            onClick={() => setShowRunConfirmModal(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-amber-600 to-red-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-red-900/20 hover:from-amber-500 hover:to-red-500 transition-all"
          >
            <Play className="h-4 w-4 fill-white" />
            Run Engine Now
          </button>
        </div>
      </div>

      {error && (
        <ErrorState
          title="Error loading suspension data"
          message={error}
          onRetry={loadData}
        />
      )}

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Metric 1 */}
        <div className="rounded-xl border border-red-900/30 bg-gradient-to-b from-red-950/20 to-slate-900/60 p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-red-400">
              Currently Suspended
            </span>
            <div className="rounded-lg bg-red-500/10 p-2 text-red-400">
              <Power className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">
              {isLoading ? <Skeleton className="h-8 w-16" /> : metrics?.currently_suspended ?? 0}
            </span>
            <span className="text-xs text-slate-400">Service Accounts</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Auto-restores instantly upon full payment
          </p>
        </div>

        {/* Metric 2 */}
        <div className="rounded-xl border border-amber-900/30 bg-gradient-to-b from-amber-950/20 to-slate-900/60 p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              Eligible for Suspension
            </span>
            <div className="rounded-lg bg-amber-500/10 p-2 text-amber-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">
              {isLoading ? <Skeleton className="h-8 w-16" /> : metrics?.eligible_for_suspension ?? 0}
            </span>
            <span className="text-xs text-amber-400/80">Action Required</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Past grace period + overdue threshold
          </p>
        </div>

        {/* Metric 3 */}
        <div className="rounded-xl border border-emerald-900/30 bg-gradient-to-b from-emerald-950/20 to-slate-900/60 p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              PTP Protected
            </span>
            <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">
              {isLoading ? <Skeleton className="h-8 w-16" /> : metrics?.ptp_exempt ?? 0}
            </span>
            <span className="text-xs text-slate-400">Exempt from Cutoff</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Active Promise-to-Pay agreements in effect
          </p>
        </div>

        {/* Metric 4 */}
        <div className="rounded-xl border border-blue-900/30 bg-gradient-to-b from-blue-950/20 to-slate-900/60 p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-400">
              Pre-Cutoff Warnings
            </span>
            <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
              <BellRing className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">
              {isLoading ? <Skeleton className="h-8 w-16" /> : metrics?.warning_eligible ?? 0}
            </span>
            <span className="text-xs text-slate-400">Warning Candidates</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            WhatsApp & SMS warning triggers active
          </p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-slate-800">
        <div className="flex space-x-8">
          <button
            onClick={() => setActiveTab("eligibility")}
            className={`flex items-center gap-2 border-b-2 py-4 text-sm font-medium transition-colors ${
              activeTab === "eligibility"
                ? "border-amber-500 text-amber-400"
                : "border-transparent text-slate-400 hover:border-slate-700 hover:text-slate-300"
            }`}
          >
            <AlertTriangle className="h-4 w-4" />
            Overdue Eligibility
            <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-400">
              {eligibilityList.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("suspended")}
            className={`flex items-center gap-2 border-b-2 py-4 text-sm font-medium transition-colors ${
              activeTab === "suspended"
                ? "border-red-500 text-red-400"
                : "border-transparent text-slate-400 hover:border-slate-700 hover:text-slate-300"
            }`}
          >
            <Power className="h-4 w-4" />
            Suspended Accounts
            <span className="rounded-full bg-red-500/10 px-2 py-0.5 text-xs text-red-400">
              {metrics?.currently_suspended ?? 0}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("history")}
            className={`flex items-center gap-2 border-b-2 py-4 text-sm font-medium transition-colors ${
              activeTab === "history"
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-slate-400 hover:border-slate-700 hover:text-slate-300"
            }`}
          >
            <History className="h-4 w-4" />
            Audit & History Log
            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
              {historyList.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("policy")}
            className={`flex items-center gap-2 border-b-2 py-4 text-sm font-medium transition-colors ${
              activeTab === "policy"
                ? "border-purple-500 text-purple-400"
                : "border-transparent text-slate-400 hover:border-slate-700 hover:text-slate-300"
            }`}
          >
            <Settings className="h-4 w-4" />
            Automation & Policy Settings
          </button>
        </div>
      </div>

      {/* TAB 1: OVERDUE ELIGIBILITY */}
      {activeTab === "eligibility" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search by customer name, service number, or phone..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-slate-800 bg-slate-950/60 pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-amber-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-500" />
              <select
                value={ptpFilter}
                onChange={(e) => setPtpFilter(e.target.value)}
                className="rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 focus:border-amber-500 focus:outline-none"
              >
                <option value="ALL">All Accounts</option>
                <option value="SUSPENDABLE">Eligible for Suspension Only</option>
                <option value="PTP_EXEMPT">PTP Protected Only</option>
                <option value="GRACE">In Grace Period Only</option>
              </select>
            </div>
          </div>

          {/* Table */}
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded-lg" />
              ))}
            </div>
          ) : filteredEligibility.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="No Overdue Accounts"
              description="All customers are within grace period or have cleared balances."
            />
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-800 bg-slate-950/60 text-xs font-semibold uppercase text-slate-400">
                    <tr>
                      <th className="px-4 py-3.5">Customer & Service</th>
                      <th className="px-4 py-3.5">Package</th>
                      <th className="px-4 py-3.5">Outstanding Debt</th>
                      <th className="px-4 py-3.5">Oldest Due Date</th>
                      <th className="px-4 py-3.5">Overdue Days</th>
                      <th className="px-4 py-3.5">Policy Status</th>
                      <th className="px-4 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filteredEligibility.map((item) => (
                      <tr key={item.service_id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3.5">
                          <div className="font-medium text-white">{item.customer_name}</div>
                          <div className="text-xs text-slate-400">
                            {item.service_number} • {item.phone}
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-slate-300">{item.package_name}</td>
                        <td className="px-4 py-3.5 font-semibold text-amber-400">
                          PKR {parseFloat(item.total_outstanding).toLocaleString()}
                        </td>
                        <td className="px-4 py-3.5 text-slate-400">
                          {item.oldest_due_date || "—"}
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${
                            item.days_overdue > 10
                              ? "bg-red-500/10 text-red-400 border border-red-500/20"
                              : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          }`}>
                            {item.days_overdue} days
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          {item.is_ptp_exempt ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/20">
                              <ShieldCheck className="h-3 w-3" />
                              PTP Active
                            </span>
                          ) : item.in_grace_period ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-medium text-blue-400 border border-blue-500/20">
                              <Clock className="h-3 w-3" />
                              Grace Period
                            </span>
                          ) : item.is_eligible_for_suspension ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2.5 py-0.5 text-xs font-medium text-red-400 border border-red-500/20">
                              <AlertTriangle className="h-3 w-3" />
                              Eligible for Cutoff
                            </span>
                          ) : (
                            <span className="text-xs text-slate-400">Compliant</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {item.status === "SUSPENDED_NON_PAYMENT" ? (
                              <button
                                onClick={() => setSelectedForRestore(item)}
                                className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                              >
                                Restore
                              </button>
                            ) : (
                              <button
                                onClick={() => setSelectedForSuspend(item)}
                                className="rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-400 hover:bg-red-500/20 transition-colors"
                              >
                                Suspend Now
                              </button>
                            )}
                            <Link
                              href={`/customers/${item.customer_id}`}
                              className="rounded-lg border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
                            >
                              Profile
                            </Link>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: CURRENTLY SUSPENDED */}
      {activeTab === "suspended" && (
        <div className="space-y-4">
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded-lg" />
              ))}
            </div>
          ) : suspendedList.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="No Suspended Accounts"
              description="There are currently no customer service accounts under suspension."
            />
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-800 bg-slate-950/60 text-xs font-semibold uppercase text-slate-400">
                    <tr>
                      <th className="px-4 py-3.5">Customer / Service</th>
                      <th className="px-4 py-3.5">Package</th>
                      <th className="px-4 py-3.5">Current Balance</th>
                      <th className="px-4 py-3.5">Status</th>
                      <th className="px-4 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {suspendedList.map((item) => (
                      <tr key={item.service_id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3.5">
                          <div className="font-medium text-white">{item.customer_name}</div>
                          <div className="text-xs text-slate-400">
                            {item.service_number} • {item.phone}
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-slate-300">{item.package_name}</td>
                        <td className="px-4 py-3.5 font-semibold text-red-400">
                          PKR {parseFloat(item.total_outstanding).toLocaleString()}
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2.5 py-0.5 text-xs font-medium text-red-400 border border-red-500/20">
                            <Power className="h-3 w-3" />
                            SUSPENDED (Non-Payment)
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => setSelectedForRestore(item)}
                              className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                            >
                              Restore Service
                            </button>
                            <Link
                              href={`/collections?customer_id=${item.customer_id}`}
                              className="rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-400 hover:bg-blue-500/20 transition-colors"
                            >
                              Record Payment
                            </Link>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: AUDIT & HISTORY LOG */}
      {activeTab === "history" && (
        <div className="space-y-4">
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded-lg" />
              ))}
            </div>
          ) : historyList.length === 0 ? (
            <EmptyState
              icon={History}
              title="No Suspension Logs"
              description="No suspension or restoration events have been recorded yet."
            />
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-800 bg-slate-950/60 text-xs font-semibold uppercase text-slate-400">
                    <tr>
                      <th className="px-4 py-3.5">Timestamp</th>
                      <th className="px-4 py-3.5">Event Type</th>
                      <th className="px-4 py-3.5">Customer & Service</th>
                      <th className="px-4 py-3.5">Trigger / Actor</th>
                      <th className="px-4 py-3.5">Reason & Details</th>
                      <th className="px-4 py-3.5">Outstanding Snapshot</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {historyList.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3.5 text-xs text-slate-400 whitespace-nowrap">
                          {new Date(log.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3.5">
                          {log.event_type === "SUSPENSION" ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2.5 py-0.5 text-xs font-medium text-red-400 border border-red-500/20">
                              <Power className="h-3 w-3" />
                              SUSPENSION
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/20">
                              <CheckCircle2 className="h-3 w-3" />
                              RESTORATION
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="font-medium text-white">{log.customer_name}</div>
                          <div className="text-xs text-slate-400">{log.service_number}</div>
                        </td>
                        <td className="px-4 py-3.5 text-xs text-slate-300">
                          <div>{log.trigger_type}</div>
                          {log.actor_name && (
                            <div className="text-slate-500">By {log.actor_name}</div>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-slate-300 max-w-xs truncate">
                          {log.reason}
                        </td>
                        <td className="px-4 py-3.5 font-medium text-amber-400">
                          PKR {parseFloat(log.outstanding_amount || "0").toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: AUTOMATION & POLICY SETTINGS */}
      {activeTab === "policy" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">Suspension & Restoration Policy</h2>
              <p className="text-sm text-slate-400">
                Configure automated overdue rules, grace periods, threshold days, and restoration triggers for your organization.
              </p>
            </div>
          </div>

          {policySaveSuccess && (
            <div className="mb-6 rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-400">
              Suspension policy updated successfully!
            </div>
          )}

          {policySaveError && (
            <div className="mb-6 rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
              {policySaveError}
            </div>
          )}

          <form onSubmit={handleSavePolicy} className="space-y-6">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Grace Period (Days)
                </label>
                <input
                  type="number"
                  min="0"
                  value={policyForm.grace_period_days ?? 3}
                  onChange={(e) => setPolicyForm({ ...policyForm, grace_period_days: parseInt(e.target.value) || 0 })}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-sm text-white focus:border-amber-500 focus:outline-none"
                />
                <p className="mt-1.5 text-xs text-slate-500">
                  Number of days after invoice due date before any overdue action is initiated.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Suspension Threshold (Days after Grace Period)
                </label>
                <input
                  type="number"
                  min="0"
                  value={policyForm.suspension_threshold_days ?? 5}
                  onChange={(e) => setPolicyForm({ ...policyForm, suspension_threshold_days: parseInt(e.target.value) || 0 })}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-sm text-white focus:border-amber-500 focus:outline-none"
                />
                <p className="mt-1.5 text-xs text-slate-500">
                  Additional days overdue past the grace period before the service is cut off.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Minimum Outstanding Debt (PKR)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={policyForm.minimum_outstanding_amount ?? "100.00"}
                  onChange={(e) => setPolicyForm({ ...policyForm, minimum_outstanding_amount: e.target.value })}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-sm text-white focus:border-amber-500 focus:outline-none"
                />
                <p className="mt-1.5 text-xs text-slate-500">
                  Accounts with debt lower than this amount are exempt from automatic suspension.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Warning Notice Days Before Cutoff
                </label>
                <input
                  type="number"
                  min="0"
                  value={policyForm.warning_days_before_suspension ?? 2}
                  onChange={(e) => setPolicyForm({ ...policyForm, warning_days_before_suspension: parseInt(e.target.value) || 0 })}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-sm text-white focus:border-amber-500 focus:outline-none"
                />
                <p className="mt-1.5 text-xs text-slate-500">
                  Days remaining before cutoff when pre-suspension WhatsApp/SMS alert is dispatched.
                </p>
              </div>
            </div>

            <div className="border-t border-slate-800 pt-6 space-y-4">
              <h3 className="text-sm font-semibold text-white">Automation Switches</h3>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-950/40 p-4 cursor-pointer hover:border-slate-700 transition-colors">
                  <input
                    type="checkbox"
                    checked={policyForm.auto_suspension_enabled ?? true}
                    onChange={(e) => setPolicyForm({ ...policyForm, auto_suspension_enabled: e.target.checked })}
                    className="mt-1 rounded border-slate-700 text-amber-500 focus:ring-amber-500/20"
                  />
                  <div>
                    <span className="text-sm font-medium text-white block">Auto-Suspension Engine</span>
                    <span className="text-xs text-slate-400">Allow nightly background engine to automatically disconnect eligible overdue accounts.</span>
                  </div>
                </label>

                <label className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-950/40 p-4 cursor-pointer hover:border-slate-700 transition-colors">
                  <input
                    type="checkbox"
                    checked={policyForm.auto_restoration_enabled ?? true}
                    onChange={(e) => setPolicyForm({ ...policyForm, auto_restoration_enabled: e.target.checked })}
                    className="mt-1 rounded border-slate-700 text-emerald-500 focus:ring-emerald-500/20"
                  />
                  <div>
                    <span className="text-sm font-medium text-white block">Instant Auto-Restoration</span>
                    <span className="text-xs text-slate-400">Immediately reconnect suspended services as soon as verified payment is recorded.</span>
                  </div>
                </label>

                <label className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-950/40 p-4 cursor-pointer hover:border-slate-700 transition-colors">
                  <input
                    type="checkbox"
                    checked={policyForm.ptp_exemption_enabled ?? true}
                    onChange={(e) => setPolicyForm({ ...policyForm, ptp_exemption_enabled: e.target.checked })}
                    className="mt-1 rounded border-slate-700 text-blue-500 focus:ring-blue-500/20"
                  />
                  <div>
                    <span className="text-sm font-medium text-white block">Promise-to-Pay Exemption</span>
                    <span className="text-xs text-slate-400">Exempt customers with active Promise-to-Pay agreements until deadline expires.</span>
                  </div>
                </label>

                <label className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-950/40 p-4 cursor-pointer hover:border-slate-700 transition-colors">
                  <input
                    type="checkbox"
                    checked={policyForm.restore_on_partial_payment ?? false}
                    onChange={(e) => setPolicyForm({ ...policyForm, restore_on_partial_payment: e.target.checked })}
                    className="mt-1 rounded border-slate-700 text-purple-500 focus:ring-purple-500/20"
                  />
                  <div>
                    <span className="text-sm font-medium text-white block">Restore on Partial Payment</span>
                    <span className="text-xs text-slate-400">Allow restoration even if only partial bill payment is received (Default: Require Full Payment).</span>
                  </div>
                </label>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <button
                type="submit"
                disabled={isSavingPolicy}
                className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-amber-900/20 hover:bg-amber-500 disabled:opacity-50 transition-all"
              >
                {isSavingPolicy ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                Save Policy Configuration
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL: MANUAL SUSPEND */}
      {selectedForSuspend && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-red-900/40 bg-slate-950 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2 text-red-400 font-semibold">
                <AlertTriangle className="h-5 w-5" />
                Suspend Service Account
              </div>
              <button
                onClick={() => setSelectedForSuspend(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleManualSuspend} className="mt-4 space-y-4">
              <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-300">
                Are you sure you want to suspend this service? Internet access will be disconnected and a notification will be dispatched.
              </div>

              <div className="space-y-1 text-sm">
                <div className="text-slate-400">Customer: <span className="text-white font-medium">{selectedForSuspend.customer_name}</span></div>
                <div className="text-slate-400">Service: <span className="text-white font-medium">{selectedForSuspend.service_number}</span></div>
                <div className="text-slate-400">Outstanding: <span className="text-amber-400 font-semibold">PKR {parseFloat(selectedForSuspend.total_outstanding).toLocaleString()}</span></div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  Mandatory Reason <span className="text-red-400">*</span>
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="e.g. Non-payment after repeated reminders, or customer request..."
                  value={suspendReason}
                  onChange={(e) => setSuspendReason(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white focus:border-red-500 focus:outline-none"
                />
              </div>

              {suspendModalError && (
                <div className="text-xs text-red-400">{suspendModalError}</div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedForSuspend(null)}
                  className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingSuspend}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-50"
                >
                  {isSubmittingSuspend ? <LoaderCircle className="h-3 w-3 animate-spin" /> : <Power className="h-3 w-3" />}
                  Confirm Suspension
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: MANUAL RESTORE */}
      {selectedForRestore && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-emerald-900/40 bg-slate-950 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <CheckCircle2 className="h-5 w-5" />
                Restore Service Account
              </div>
              <button
                onClick={() => setSelectedForRestore(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleManualRestore} className="mt-4 space-y-4">
              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-300">
                This will reactivate network connectivity and send a restoration notification to the customer.
              </div>

              <div className="space-y-1 text-sm">
                <div className="text-slate-400">Customer: <span className="text-white font-medium">{selectedForRestore.customer_name}</span></div>
                <div className="text-slate-400">Service: <span className="text-white font-medium">{selectedForRestore.service_number}</span></div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  Restoration Reason / Note <span className="text-emerald-400">*</span>
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="e.g. Payment verified via bank transfer, or management exception..."
                  value={restoreReason}
                  onChange={(e) => setRestoreReason(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              {restoreModalError && (
                <div className="text-xs text-red-400">{restoreModalError}</div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedForRestore(null)}
                  className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingRestore}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {isSubmittingRestore ? <LoaderCircle className="h-3 w-3 animate-spin" /> : <Power className="h-3 w-3" />}
                  Confirm Restoration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: RUN ENGINE CONFIRMATION */}
      {showRunConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl border border-amber-900/40 bg-slate-950 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2 text-amber-400 font-semibold">
                <Zap className="h-5 w-5" />
                Run Automated Suspension Engine
              </div>
              <button
                onClick={() => {
                  setShowRunConfirmModal(false);
                  setBatchRunResult(null);
                }}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 space-y-4 text-sm">
              {!batchRunResult ? (
                <>
                  <p className="text-slate-300">
                    This will evaluate all active service accounts against your organization's policy:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-xs text-slate-400">
                    <li>Grace Period: {policy?.grace_period_days ?? 3} days</li>
                    <li>Suspension Threshold: {policy?.suspension_threshold_days ?? 5} days</li>
                    <li>Exempts accounts with active Promise-to-Pay agreements</li>
                    <li>Dispatches WhatsApp / SMS warnings to warning-eligible customers</li>
                    <li>Suspends non-paying overdue accounts automatically</li>
                  </ul>

                  <div className="flex justify-end gap-2 pt-4">
                    <button
                      onClick={() => setShowRunConfirmModal(false)}
                      className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-900"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleRunAutomatedEngine}
                      disabled={isRunningEngine}
                      className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-amber-600 to-red-600 px-4 py-2 text-xs font-semibold text-white hover:from-amber-500 hover:to-red-500 disabled:opacity-50"
                    >
                      {isRunningEngine ? <LoaderCircle className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3 fill-white" />}
                      Execute Batch Engine
                    </button>
                  </div>
                </>
              ) : (
                <div className="space-y-4">
                  <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-400">
                    Automated engine run completed successfully!
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                      <div className="text-slate-400">Accounts Evaluated</div>
                      <div className="text-lg font-bold text-white mt-1">{batchRunResult.eligible_count}</div>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                      <div className="text-slate-400">Suspensions Executed</div>
                      <div className="text-lg font-bold text-red-400 mt-1">{batchRunResult.suspended_count}</div>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                      <div className="text-slate-400">Warnings Dispatched</div>
                      <div className="text-lg font-bold text-amber-400 mt-1">{batchRunResult.warnings_sent_count}</div>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                      <div className="text-slate-400">Errors Encountered</div>
                      <div className="text-lg font-bold text-slate-300 mt-1">{batchRunResult.errors_count}</div>
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      onClick={() => {
                        setShowRunConfirmModal(false);
                        setBatchRunResult(null);
                      }}
                      className="rounded-lg bg-slate-800 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-700"
                    >
                      Close
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
