"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Award,
  Banknote,
  BookOpen,
  Box,
  Building2,
  Calendar,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  Clock,
  CreditCard,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  Filter,
  HardDrive,
  Headphones,
  Layers,
  MapPin,
  Package,
  Printer,
  Receipt,
  RefreshCw,
  Search,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  UserCheck,
  Users,
  Wifi,
  X,
} from "lucide-react";

import {
  reportingEngineService,
  type AreaRevenueDensityRow,
  type BalanceSheetResponse,
  type CashierShiftResponse,
  type CashPositionResponse,
  type ComplaintSlaResponse,
  type CustomerCollectionsResponse,
  type CustomerGrowthChurnResponse,
  type CustomerMasterResponse,
  type Dealer360Row,
  type DefaultersAgingResponse,
  type DeviceCustodyResponse,
  type InvoiceRegisterResponse,
  type LeadConversionResponse,
  type ProfitAndLossResponse,
  type PromiseToPayResponse,
  type RecoveryOfficerScorecardRow,
} from "@/services/reporting-engine.service";
import Skeleton from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";

type DomainTab =
  | "customers"
  | "collections"
  | "defaulters"
  | "billing"
  | "financials"
  | "dealers"
  | "recovery"
  | "support"
  | "sales_inventory";

export default function ReportingCenterPage() {
  const [activeTab, setActiveTab] = useState<DomainTab>("customers");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Global filters
  const [startDate, setStartDate] = useState<string>(() => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState<string>(() => new Date().toISOString().split("T")[0]);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  // Sub-tab toggles per domain
  const [customerSubTab, setCustomerSubTab] = useState<"master" | "growth" | "density">("master");
  const [collectionSubTab, setCollectionSubTab] = useState<"register" | "shift">("register");
  const [financialSubTab, setFinancialSubTab] = useState<"pnl" | "balance_sheet" | "cash">("pnl");
  const [recoverySubTab, setRecoverySubTab] = useState<"ptp" | "officers">("ptp");
  const [salesInvSubTab, setSalesInvSubTab] = useState<"inquiries" | "devices">("inquiries");

  // Specific filter dropdowns
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [agingBucketFilter, setAgingBucketFilter] = useState("ALL");
  const [paymentMethodFilter, setPaymentMethodFilter] = useState("ALL");

  // Domain Data States
  const [customerMasterData, setCustomerMasterData] = useState<CustomerMasterResponse | null>(null);
  const [growthData, setGrowthData] = useState<CustomerGrowthChurnResponse | null>(null);
  const [densityData, setDensityData] = useState<AreaRevenueDensityRow[]>([]);
  const [collectionsData, setCollectionsData] = useState<CustomerCollectionsResponse | null>(null);
  const [shiftData, setShiftData] = useState<CashierShiftResponse | null>(null);
  const [defaultersData, setDefaultersData] = useState<DefaultersAgingResponse | null>(null);
  const [invoiceData, setInvoiceData] = useState<InvoiceRegisterResponse | null>(null);
  const [pnlData, setPnlData] = useState<ProfitAndLossResponse | null>(null);
  const [balanceSheetData, setBalanceSheetData] = useState<BalanceSheetResponse | null>(null);
  const [cashPositionData, setCashPositionData] = useState<CashPositionResponse | null>(null);
  const [dealerData, setDealerData] = useState<Dealer360Row[]>([]);
  const [ptpData, setPtpData] = useState<PromiseToPayResponse | null>(null);
  const [officerData, setOfficerData] = useState<RecoveryOfficerScorecardRow[]>([]);
  const [supportSlaData, setSupportSlaData] = useState<ComplaintSlaResponse | null>(null);
  const [funnelData, setFunnelData] = useState<LeadConversionResponse | null>(null);
  const [deviceData, setDeviceData] = useState<DeviceCustodyResponse | null>(null);

  // Load report data based on active tab and sub-tab
  const fetchActiveReport = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === "customers") {
        if (customerSubTab === "master") {
          const res = await reportingEngineService.getCustomerMaster({
            status: statusFilter,
            search: searchQuery,
            page: currentPage,
          });
          setCustomerMasterData(res);
        } else if (customerSubTab === "growth") {
          const res = await reportingEngineService.getCustomerGrowthChurn({
            start_date: startDate,
            end_date: endDate,
          });
          setGrowthData(res);
        } else {
          const res = await reportingEngineService.getAreaRevenueDensity();
          setDensityData(res);
        }
      } else if (activeTab === "collections") {
        if (collectionSubTab === "register") {
          const res = await reportingEngineService.getCollectionsRegister({
            start_date: startDate,
            end_date: endDate,
            payment_method: paymentMethodFilter,
            search: searchQuery,
            page: currentPage,
          });
          setCollectionsData(res);
        } else {
          const res = await reportingEngineService.getCashierShiftClose({
            shift_date: endDate,
          });
          setShiftData(res);
        }
      } else if (activeTab === "defaulters") {
        const res = await reportingEngineService.getDefaultersAging({
          aging_bucket: agingBucketFilter,
          page: currentPage,
          as_of_date: endDate,
        });
        setDefaultersData(res);
      } else if (activeTab === "billing") {
        const res = await reportingEngineService.getInvoiceRegister({
          status: statusFilter,
          start_date: startDate,
          end_date: endDate,
          search: searchQuery,
          page: currentPage,
        });
        setInvoiceData(res);
      } else if (activeTab === "financials") {
        if (financialSubTab === "pnl") {
          const res = await reportingEngineService.getProfitAndLoss({
            start_date: startDate,
            end_date: endDate,
          });
          setPnlData(res);
        } else if (financialSubTab === "balance_sheet") {
          const res = await reportingEngineService.getBalanceSheet({
            as_of_date: endDate,
          });
          setBalanceSheetData(res);
        } else {
          const res = await reportingEngineService.getCashPosition({
            start_date: startDate,
            end_date: endDate,
          });
          setCashPositionData(res);
        }
      } else if (activeTab === "dealers") {
        const res = await reportingEngineService.getDealer360Performance({
          start_date: startDate,
          end_date: endDate,
        });
        setDealerData(res);
      } else if (activeTab === "recovery") {
        if (recoverySubTab === "ptp") {
          const res = await reportingEngineService.getPromiseToPayReport({
            start_date: startDate,
            end_date: endDate,
            status: statusFilter,
            page: currentPage,
          });
          setPtpData(res);
        } else {
          const res = await reportingEngineService.getFieldRecoveryScorecard({
            start_date: startDate,
            end_date: endDate,
          });
          setOfficerData(res);
        }
      } else if (activeTab === "support") {
        const res = await reportingEngineService.getComplaintSla({
          start_date: startDate,
          end_date: endDate,
        });
        setSupportSlaData(res);
      } else if (activeTab === "sales_inventory") {
        if (salesInvSubTab === "inquiries") {
          const res = await reportingEngineService.getLeadConversionFunnel({
            start_date: startDate,
            end_date: endDate,
          });
          setFunnelData(res);
        } else {
          const res = await reportingEngineService.getDeviceCustody({
            page: currentPage,
          });
          setDeviceData(res);
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load report data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActiveReport();
  }, [
    activeTab,
    customerSubTab,
    collectionSubTab,
    financialSubTab,
    recoverySubTab,
    salesInvSubTab,
    currentPage,
    statusFilter,
    agingBucketFilter,
    paymentMethodFilter,
    startDate,
    endDate,
  ]);

  // Quick Date Preset helper
  const handleApplyPreset = (preset: "today" | "this_month" | "last_30" | "ytd") => {
    const today = new Date();
    const todayStr = today.toISOString().split("T")[0];
    if (preset === "today") {
      setStartDate(todayStr);
      setEndDate(todayStr);
    } else if (preset === "this_month") {
      const first = new Date(today.getFullYear(), today.getMonth(), 1);
      setStartDate(first.toISOString().split("T")[0]);
      setEndDate(todayStr);
    } else if (preset === "last_30") {
      const past = new Date();
      past.setDate(today.getDate() - 30);
      setStartDate(past.toISOString().split("T")[0]);
      setEndDate(todayStr);
    } else if (preset === "ytd") {
      const ytd = new Date(today.getFullYear(), 0, 1);
      setStartDate(ytd.toISOString().split("T")[0]);
      setEndDate(todayStr);
    }
    setCurrentPage(1);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6 pb-20">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Reports & Analytics Center
            </h1>
            <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-0.5 text-xs font-semibold text-indigo-400">
              Enterprise Engine
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Authoritative operational metrics, collections registers, financial statements, and partner analytics.
          </p>
        </div>

        {/* Global Toolbar Actions */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center rounded-xl border border-slate-800 bg-slate-900/90 p-1 text-xs text-slate-400">
            <button
              onClick={() => handleApplyPreset("today")}
              className="rounded-lg px-2.5 py-1 hover:text-white transition"
            >
              Today
            </button>
            <button
              onClick={() => handleApplyPreset("this_month")}
              className="rounded-lg px-2.5 py-1 hover:text-white transition"
            >
              This Month
            </button>
            <button
              onClick={() => handleApplyPreset("last_30")}
              className="rounded-lg px-2.5 py-1 hover:text-white transition"
            >
              Last 30D
            </button>
            <button
              onClick={() => handleApplyPreset("ytd")}
              className="rounded-lg px-2.5 py-1 hover:text-white transition"
            >
              YTD
            </button>
          </div>

          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/90 px-3.5 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition"
          >
            <Printer className="h-4 w-4 text-slate-400" />
            Print Report
          </button>

          <button
            onClick={fetchActiveReport}
            className="rounded-xl border border-slate-800 bg-slate-900/90 p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title="Refresh Report"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-indigo-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* Domain Navigation Tabs */}
      <div className="flex overflow-x-auto border-b border-slate-800 no-scrollbar">
        <div className="flex gap-1">
          {[
            { key: "customers", label: "Subscribers & Directory", icon: Users },
            { key: "collections", label: "Collections & Cashier", icon: CircleDollarSign },
            { key: "defaulters", label: "Defaulters & Aging", icon: AlertTriangle },
            { key: "billing", label: "Billing & Invoices", icon: FileSpreadsheet },
            { key: "financials", label: "Financial Statements (GL)", icon: ShieldCheck },
            { key: "dealers", label: "Dealer 360", icon: Building2 },
            { key: "recovery", label: "Recovery & Promises", icon: UserCheck },
            { key: "support", label: "Support & SLA", icon: Headphones },
            { key: "sales_inventory", label: "Sales & Devices", icon: HardDrive },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => {
                  setActiveTab(tab.key as DomainTab);
                  setCurrentPage(1);
                  setSearchQuery("");
                }}
                className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-3 text-xs font-semibold transition ${
                  active
                    ? "border-indigo-500 text-indigo-400 bg-indigo-500/5"
                    : "border-transparent text-slate-400 hover:border-slate-700 hover:text-slate-200"
                }`}
              >
                <Icon className={`h-4 w-4 ${active ? "text-indigo-400" : "text-slate-400"}`} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Parameters Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur">
        {/* Left: Sub-tabs or Specific Filter Selector */}
        <div className="flex flex-wrap items-center gap-2">
          {activeTab === "customers" && (
            <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800">
              <button
                onClick={() => setCustomerSubTab("master")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  customerSubTab === "master" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Subscriber Master Directory
              </button>
              <button
                onClick={() => setCustomerSubTab("growth")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  customerSubTab === "growth" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Growth & Churn Analysis
              </button>
              <button
                onClick={() => setCustomerSubTab("density")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  customerSubTab === "density" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Area Density & Yield
              </button>
            </div>
          )}

          {activeTab === "collections" && (
            <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800">
              <button
                onClick={() => setCollectionSubTab("register")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  collectionSubTab === "register" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Collections Register
              </button>
              <button
                onClick={() => setCollectionSubTab("shift")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  collectionSubTab === "shift" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Cashier Daily Shift Close
              </button>
            </div>
          )}

          {activeTab === "financials" && (
            <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800">
              <button
                onClick={() => setFinancialSubTab("pnl")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  financialSubTab === "pnl" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Profit & Loss (P&L)
              </button>
              <button
                onClick={() => setFinancialSubTab("balance_sheet")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  financialSubTab === "balance_sheet" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Balance Sheet
              </button>
              <button
                onClick={() => setFinancialSubTab("cash")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  financialSubTab === "cash" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Cash & Bank Position
              </button>
            </div>
          )}

          {activeTab === "recovery" && (
            <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800">
              <button
                onClick={() => setRecoverySubTab("ptp")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  recoverySubTab === "ptp" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Promise to Pay Performance
              </button>
              <button
                onClick={() => setRecoverySubTab("officers")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  recoverySubTab === "officers" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Field Recovery Officer Scorecard
              </button>
            </div>
          )}

          {activeTab === "sales_inventory" && (
            <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800">
              <button
                onClick={() => setSalesInvSubTab("inquiries")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  salesInvSubTab === "inquiries" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Lead Conversion Funnel
              </button>
              <button
                onClick={() => setSalesInvSubTab("devices")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  salesInvSubTab === "devices" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                CPE Device Custody Register
              </button>
            </div>
          )}
        </div>

        {/* Right: Date range inputs and search filter */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 font-medium">From:</span>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-500 font-medium">To:</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          {activeTab === "defaulters" && (
            <select
              value={agingBucketFilter}
              onChange={(e) => setAgingBucketFilter(e.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-1.5 text-white focus:border-indigo-500 focus:outline-none"
            >
              <option value="ALL">All Aging Buckets</option>
              <option value="0-30">0–30 Days Overdue</option>
              <option value="31-60">31–60 Days Overdue</option>
              <option value="61-90">61–90 Days Overdue</option>
              <option value="90+">90+ Days Critical</option>
            </select>
          )}

          {activeTab === "collections" && collectionSubTab === "register" && (
            <select
              value={paymentMethodFilter}
              onChange={(e) => setPaymentMethodFilter(e.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-1.5 text-white focus:border-indigo-500 focus:outline-none"
            >
              <option value="ALL">All Methods</option>
              <option value="CASH">Cash</option>
              <option value="BANK_TRANSFER">Bank Transfer</option>
              <option value="CARD">Card</option>
              <option value="MOBILE_WALLET">Mobile Wallet</option>
            </select>
          )}

          <div className="relative">
            <Search className="absolute left-3 top-2 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Filter / search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && fetchActiveReport()}
              className="rounded-xl border border-slate-800 bg-slate-950 pl-8 pr-3 py-1.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none w-44"
            />
          </div>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={fetchActiveReport} />}

      {/* ========================================================================= */}
      {/* 1. SUBSCRIBERS & DIRECTORY TAB */}
      {/* ========================================================================= */}
      {activeTab === "customers" && (
        <div className="space-y-6">
          {customerSubTab === "master" && customerMasterData && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Total Subscribers</span>
                  <div className="text-2xl font-bold text-white mt-1">
                    {customerMasterData.summary.total_subscribers}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Active Subscribers</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">
                    {customerMasterData.summary.active_count}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Suspended / Overdue</span>
                  <div className="text-2xl font-bold text-rose-400 mt-1">
                    {customerMasterData.summary.suspended_count}
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                      <tr>
                        <th className="py-3 px-4 font-semibold">Customer #</th>
                        <th className="py-3 px-4 font-semibold">Subscriber Name</th>
                        <th className="py-3 px-4 font-semibold">Phone</th>
                        <th className="py-3 px-4 font-semibold">Area / City</th>
                        <th className="py-3 px-4 font-semibold">Package & Speed</th>
                        <th className="py-3 px-4 font-semibold text-right">Monthly Fee</th>
                        <th className="py-3 px-4 font-semibold text-center">Status</th>
                        <th className="py-3 px-4 font-semibold">Assigned Node</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {customerMasterData.records.map((r) => (
                        <tr key={r.service_id} className="hover:bg-slate-800/30 transition">
                          <td className="py-3 px-4 font-mono font-bold text-indigo-300">{r.customer_number}</td>
                          <td className="py-3 px-4 font-semibold text-white">{r.customer_name}</td>
                          <td className="py-3 px-4 text-slate-300">{r.phone}</td>
                          <td className="py-3 px-4 text-slate-300">{r.area} ({r.city})</td>
                          <td className="py-3 px-4 text-slate-200">{r.package_name} • {r.speed_mbps}</td>
                          <td className="py-3 px-4 text-right font-mono font-bold text-white">PKR {r.monthly_price}</td>
                          <td className="py-3 px-4 text-center">
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                                r.status === "ACTIVE"
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                  : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                              }`}
                            >
                              {r.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-mono text-[11px] text-slate-400">{r.node_name}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {customerSubTab === "growth" && growthData && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Total New Activations</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">+{growthData.total_new}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Total Churned / Suspended</span>
                  <div className="text-2xl font-bold text-rose-400 mt-1">-{growthData.total_churned}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Net Growth</span>
                  <div className="text-2xl font-bold text-indigo-400 mt-1">
                    {growthData.net_overall_growth >= 0 ? `+${growthData.net_overall_growth}` : growthData.net_overall_growth}
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Month Period</th>
                      <th className="py-3 px-4 font-semibold text-center">New Activations</th>
                      <th className="py-3 px-4 font-semibold text-center">Deactivations</th>
                      <th className="py-3 px-4 font-semibold text-center">Net Growth</th>
                      <th className="py-3 px-4 font-semibold text-center">Churn Rate %</th>
                      <th className="py-3 px-4 font-semibold text-right">Active Base</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {growthData.intervals.map((item) => (
                      <tr key={item.period} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-4 font-mono font-bold text-white">{item.period}</td>
                        <td className="py-3 px-4 text-center font-mono font-semibold text-emerald-400">+{item.new_activations}</td>
                        <td className="py-3 px-4 text-center font-mono font-semibold text-rose-400">-{item.deactivations}</td>
                        <td className="py-3 px-4 text-center font-mono font-bold text-indigo-300">{item.net_growth >= 0 ? `+${item.net_growth}` : item.net_growth}</td>
                        <td className="py-3 px-4 text-center font-mono text-slate-300">{item.churn_rate_percent}%</td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-white">{item.active_subscribers_end}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {customerSubTab === "density" && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                  <tr>
                    <th className="py-3 px-4 font-semibold">City & Area</th>
                    <th className="py-3 px-4 font-semibold text-center">Active Subscribers</th>
                    <th className="py-3 px-4 font-semibold text-right">Invoiced Amount</th>
                    <th className="py-3 px-4 font-semibold text-right">Collected Amount</th>
                    <th className="py-3 px-4 font-semibold text-right">Outstanding</th>
                    <th className="py-3 px-4 font-semibold text-center">Collection Efficiency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {densityData.map((d, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-semibold text-white">{d.area_name} ({d.city_name})</td>
                      <td className="py-3 px-4 text-center font-mono font-bold text-indigo-300">{d.active_subscribers}</td>
                      <td className="py-3 px-4 text-right font-mono text-slate-300">PKR {d.invoiced_amount}</td>
                      <td className="py-3 px-4 text-right font-mono font-semibold text-emerald-400">PKR {d.collected_amount}</td>
                      <td className="py-3 px-4 text-right font-mono font-semibold text-rose-400">PKR {d.outstanding_amount}</td>
                      <td className="py-3 px-4 text-center font-mono font-bold text-emerald-400">{d.collection_rate_percent}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. COLLECTIONS & CASHIER TAB */}
      {/* ========================================================================= */}
      {activeTab === "collections" && (
        <div className="space-y-6">
          {collectionSubTab === "register" && collectionsData && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Total Period Collections</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">
                    PKR {Number(collectionsData.summary.total_collected).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Total Payments Count</span>
                  <div className="text-2xl font-bold text-white mt-1">
                    {collectionsData.summary.payment_count}
                  </div>
                </div>
                <div className="col-span-2 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-medium text-slate-400">Method Breakdown</span>
                    <div className="flex flex-wrap gap-3 mt-1.5">
                      {collectionsData.summary.method_breakdown.map((m) => (
                        <span key={m.method} className="text-xs text-slate-300 font-mono">
                          {m.method}: <strong className="text-white">PKR {m.total}</strong> ({m.count})
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Payment #</th>
                      <th className="py-3 px-4 font-semibold">Paid Date</th>
                      <th className="py-3 px-4 font-semibold">Customer</th>
                      <th className="py-3 px-4 font-semibold">Service Account</th>
                      <th className="py-3 px-4 font-semibold">Method</th>
                      <th className="py-3 px-4 font-semibold text-right">Amount</th>
                      <th className="py-3 px-4 font-semibold">Collector</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {collectionsData.records.map((p) => (
                      <tr key={p.id} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-4 font-mono font-bold text-indigo-300">{p.payment_number}</td>
                        <td className="py-3 px-4 text-slate-300">{new Date(p.paid_at).toLocaleString()}</td>
                        <td className="py-3 px-4 font-semibold text-white">{p.customer_name}</td>
                        <td className="py-3 px-4 font-mono text-slate-300">{p.service_number}</td>
                        <td className="py-3 px-4">
                          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300 border border-slate-700">
                            {p.payment_method}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-emerald-400">PKR {p.amount}</td>
                        <td className="py-3 px-4 text-slate-400">{p.received_by_name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {collectionSubTab === "shift" && shiftData && (
            <div className="max-w-2xl mx-auto rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-base font-bold text-white">Cashier Shift Close Reconciliation</h3>
                  <p className="text-xs text-slate-400">Cashier: {shiftData.cashier_name} • Shift Date: {shiftData.shift_date}</p>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-emerald-400 font-mono">PKR {shiftData.total_intake}</div>
                  <p className="text-[11px] text-slate-400">{shiftData.transaction_count} transactions verified</p>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Method Summary</h4>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {Object.entries(shiftData.method_breakdown).map(([k, v]) => (
                    <div key={k} className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block uppercase">{k}</span>
                      <strong className="text-xs text-white font-mono mt-0.5 block">PKR {v}</strong>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Shift Collections Log</h4>
                <div className="rounded-xl border border-slate-800 overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400">
                      <tr>
                        <th className="py-2.5 px-3">Time</th>
                        <th className="py-2.5 px-3">Receipt #</th>
                        <th className="py-2.5 px-3">Customer</th>
                        <th className="py-2.5 px-3">Method</th>
                        <th className="py-2.5 px-3 text-right">Amount</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {shiftData.transactions.map((t, i) => (
                        <tr key={i} className="hover:bg-slate-800/30">
                          <td className="py-2.5 px-3 text-slate-400">{t.time}</td>
                          <td className="py-2.5 px-3 font-mono text-indigo-400 font-bold">{t.payment_number}</td>
                          <td className="py-2.5 px-3 text-white">{t.customer}</td>
                          <td className="py-2.5 px-3 text-slate-300">{t.method}</td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-emerald-400">PKR {t.amount}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. DEFAULTERS & AGING TAB */}
      {/* ========================================================================= */}
      {activeTab === "defaulters" && defaultersData && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">Total Unpaid Exposure</span>
              <div className="text-2xl font-bold text-rose-400 mt-1">
                PKR {Number(defaultersData.summary.total_exposure).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">0–30 Days Overdue</span>
              <div className="text-xl font-bold text-amber-400 mt-1">
                PKR {defaultersData.summary.aging_buckets["0-30"]}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">31–60 Days Overdue</span>
              <div className="text-xl font-bold text-amber-400 mt-1">
                PKR {defaultersData.summary.aging_buckets["31-60"]}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">61–90 Days Overdue</span>
              <div className="text-xl font-bold text-rose-400 mt-1">
                PKR {defaultersData.summary.aging_buckets["61-90"]}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">90+ Days Critical</span>
              <div className="text-xl font-bold text-rose-500 mt-1">
                PKR {defaultersData.summary.aging_buckets["90+"]}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                <tr>
                  <th className="py-3 px-4 font-semibold">Invoice #</th>
                  <th className="py-3 px-4 font-semibold">Due Date</th>
                  <th className="py-3 px-4 font-semibold text-center">Aging Bucket</th>
                  <th className="py-3 px-4 font-semibold">Customer Name</th>
                  <th className="py-3 px-4 font-semibold">Phone</th>
                  <th className="py-3 px-4 font-semibold">Area</th>
                  <th className="py-3 px-4 font-semibold text-right">Invoiced</th>
                  <th className="py-3 px-4 font-semibold text-right">Paid</th>
                  <th className="py-3 px-4 font-semibold text-right">Outstanding Overdue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {defaultersData.records.map((d) => (
                  <tr key={d.invoice_id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4 font-mono font-bold text-indigo-300">{d.invoice_number}</td>
                    <td className="py-3 px-4 text-slate-300">{d.due_date} ({d.days_overdue}d ago)</td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold border ${
                          d.aging_bucket === "0-30"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                        }`}
                      >
                        {d.aging_bucket} DAYS
                      </span>
                    </td>
                    <td className="py-3 px-4 font-semibold text-white">{d.customer_name}</td>
                    <td className="py-3 px-4 text-slate-300">{d.phone}</td>
                    <td className="py-3 px-4 text-slate-400">{d.area}</td>
                    <td className="py-3 px-4 text-right font-mono text-slate-300">PKR {d.total_invoiced}</td>
                    <td className="py-3 px-4 text-right font-mono text-emerald-400">PKR {d.paid_amount}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-rose-400">PKR {d.outstanding_amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 4. BILLING & INVOICES TAB */}
      {/* ========================================================================= */}
      {activeTab === "billing" && invoiceData && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">Total Billed in Selection</span>
              <div className="text-2xl font-bold text-white mt-1">
                PKR {Number(invoiceData.summary.total_billed).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">Total Issued Invoices</span>
              <div className="text-2xl font-bold text-indigo-400 mt-1">
                {invoiceData.summary.total_invoices_count}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                <tr>
                  <th className="py-3 px-4 font-semibold">Invoice #</th>
                  <th className="py-3 px-4 font-semibold">Issue Date</th>
                  <th className="py-3 px-4 font-semibold">Due Date</th>
                  <th className="py-3 px-4 font-semibold">Subscriber</th>
                  <th className="py-3 px-4 font-semibold">Package</th>
                  <th className="py-3 px-4 font-semibold text-right">Invoiced</th>
                  <th className="py-3 px-4 font-semibold text-right">Paid</th>
                  <th className="py-3 px-4 font-semibold text-right">Outstanding</th>
                  <th className="py-3 px-4 font-semibold text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {invoiceData.records.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4 font-mono font-bold text-indigo-300">{inv.invoice_number}</td>
                    <td className="py-3 px-4 text-slate-300">{inv.issue_date}</td>
                    <td className="py-3 px-4 text-slate-300">{inv.due_date}</td>
                    <td className="py-3 px-4 font-semibold text-white">{inv.customer_name}</td>
                    <td className="py-3 px-4 text-slate-300">{inv.package_name}</td>
                    <td className="py-3 px-4 text-right font-mono font-semibold text-white">PKR {inv.total_amount}</td>
                    <td className="py-3 px-4 text-right font-mono text-emerald-400">PKR {inv.paid_amount}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-rose-400">PKR {inv.outstanding_amount}</td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                          inv.status === "PAID"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : inv.status === "PARTIALLY_PAID"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                        }`}
                      >
                        {inv.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 5. FINANCIAL STATEMENTS TAB (BATCH 10 GL) */}
      {/* ========================================================================= */}
      {activeTab === "financials" && (
        <div className="space-y-6">
          {financialSubTab === "pnl" && pnlData && (
            <div className="max-w-3xl mx-auto rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-6">
              <div className="border-b border-slate-800 pb-4 text-center">
                <h3 className="text-lg font-bold text-white">Statement of Profit & Loss</h3>
                <p className="text-xs text-slate-400 mt-1">Period: {pnlData.period.start_date} to {pnlData.period.end_date}</p>
              </div>

              <div className="space-y-3">
                <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider">1. Operating Revenue</h4>
                <div className="divide-y divide-slate-800/80 rounded-xl border border-slate-800 bg-slate-950/60">
                  {pnlData.revenue_statement.accounts.map((acc) => (
                    <div key={acc.code} className="p-3 flex justify-between text-xs">
                      <span className="text-slate-200">{acc.code} — {acc.name}</span>
                      <strong className="text-emerald-400 font-mono">PKR {acc.amount}</strong>
                    </div>
                  ))}
                  <div className="p-3 flex justify-between text-xs font-bold bg-slate-900 text-white">
                    <span>Total Revenue</span>
                    <span className="text-emerald-400 font-mono">PKR {pnlData.revenue_statement.total_revenue}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-xs font-bold text-rose-400 uppercase tracking-wider">2. Operating Expenses</h4>
                <div className="divide-y divide-slate-800/80 rounded-xl border border-slate-800 bg-slate-950/60">
                  {pnlData.expense_statement.accounts.map((acc) => (
                    <div key={acc.code} className="p-3 flex justify-between text-xs">
                      <span className="text-slate-200">{acc.code} — {acc.name}</span>
                      <strong className="text-rose-400 font-mono">PKR {acc.amount}</strong>
                    </div>
                  ))}
                  <div className="p-3 flex justify-between text-xs font-bold bg-slate-900 text-white">
                    <span>Total Operating Expenses</span>
                    <span className="text-rose-400 font-mono">PKR {pnlData.expense_statement.total_expenses}</span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-between text-sm font-bold">
                <span className="text-white">Net Operating Profit:</span>
                <span className="text-xl font-mono text-emerald-400">PKR {pnlData.net_income.net_profit_amount}</span>
              </div>
            </div>
          )}

          {financialSubTab === "balance_sheet" && balanceSheetData && (
            <div className="max-w-3xl mx-auto rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-6">
              <div className="border-b border-slate-800 pb-4 text-center">
                <h3 className="text-lg font-bold text-white">Statement of Financial Position (Balance Sheet)</h3>
                <p className="text-xs text-slate-400 mt-1">As of: {balanceSheetData.as_of_date}</p>
                <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-3 py-0.5 text-xs text-emerald-400 font-semibold">
                  <CheckCircle2 className="h-3.5 w-3.5" /> ASSETS == LIABILITIES + EQUITY (BALANCED)
                </div>
              </div>

              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                {/* Assets */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-wider">Assets</h4>
                  <div className="divide-y divide-slate-800/80 rounded-xl border border-slate-800 bg-slate-950/60">
                    {balanceSheetData.assets.accounts.map((acc) => (
                      <div key={acc.code} className="p-2.5 flex justify-between text-xs">
                        <span className="text-slate-300">{acc.code} {acc.name}</span>
                        <strong className="text-emerald-400 font-mono">PKR {acc.amount}</strong>
                      </div>
                    ))}
                    <div className="p-2.5 flex justify-between text-xs font-bold bg-slate-900 text-white">
                      <span>Total Assets</span>
                      <span className="text-emerald-400 font-mono">PKR {balanceSheetData.assets.total_assets}</span>
                    </div>
                  </div>
                </div>

                {/* Liabilities & Equity */}
                <div className="space-y-4">
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider">Liabilities</h4>
                    <div className="divide-y divide-slate-800/80 rounded-xl border border-slate-800 bg-slate-950/60">
                      {balanceSheetData.liabilities.accounts.map((acc) => (
                        <div key={acc.code} className="p-2 flex justify-between text-xs">
                          <span className="text-slate-300">{acc.code} {acc.name}</span>
                          <strong className="text-amber-400 font-mono">PKR {acc.amount}</strong>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider">Equity & Earnings</h4>
                    <div className="divide-y divide-slate-800/80 rounded-xl border border-slate-800 bg-slate-950/60">
                      {balanceSheetData.equity.accounts.map((acc) => (
                        <div key={acc.code} className="p-2 flex justify-between text-xs">
                          <span className="text-slate-300">{acc.code} {acc.name}</span>
                          <strong className="text-purple-400 font-mono">PKR {acc.amount}</strong>
                        </div>
                      ))}
                      <div className="p-2 flex justify-between text-xs">
                        <span className="text-slate-300 font-semibold">Retained Earnings</span>
                        <strong className="text-emerald-400 font-mono">PKR {balanceSheetData.equity.retained_earnings}</strong>
                      </div>
                    </div>
                  </div>

                  <div className="p-2.5 flex justify-between text-xs font-bold bg-slate-900 rounded-xl border border-slate-800 text-white">
                    <span>Total Liabilities + Equity</span>
                    <span className="text-indigo-400 font-mono">PKR {balanceSheetData.total_liabilities_and_equity}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {financialSubTab === "cash" && cashPositionData && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
              <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/80">
                <h3 className="text-sm font-bold text-white">Liquid Cash & Bank Position</h3>
                <span className="text-xs text-slate-400">
                  Total Liquid Funds: <strong className="text-emerald-400 font-mono text-sm">PKR {cashPositionData.total_liquid_funds}</strong>
                </span>
              </div>
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Account</th>
                    <th className="py-3 px-4 font-semibold text-right">Opening Balance</th>
                    <th className="py-3 px-4 font-semibold text-right">Period Inflow (+)</th>
                    <th className="py-3 px-4 font-semibold text-right">Period Outflow (-)</th>
                    <th className="py-3 px-4 font-semibold text-right">Closing Liquid Balance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {cashPositionData.accounts.map((acc) => (
                    <tr key={acc.code} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-semibold text-white">{acc.code} — {acc.name}</td>
                      <td className="py-3 px-4 text-right font-mono text-slate-300">PKR {acc.opening_balance}</td>
                      <td className="py-3 px-4 text-right font-mono text-emerald-400">+PKR {acc.inflows}</td>
                      <td className="py-3 px-4 text-right font-mono text-rose-400">-PKR {acc.outflows}</td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-white">PKR {acc.closing_balance}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 6. DEALER 360 PERFORMANCE TAB */}
      {/* ========================================================================= */}
      {activeTab === "dealers" && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
              <tr>
                <th className="py-3 px-4 font-semibold">Dealer / Partner</th>
                <th className="py-3 px-4 font-semibold">Area</th>
                <th className="py-3 px-4 font-semibold text-center">Active Subs</th>
                <th className="py-3 px-4 font-semibold text-right">Billed</th>
                <th className="py-3 px-4 font-semibold text-right">Collected</th>
                <th className="py-3 px-4 font-semibold text-right">Accrued Commission</th>
                <th className="py-3 px-4 font-semibold text-right">Settled / Paid</th>
                <th className="py-3 px-4 font-semibold text-right">Net ISP Margin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {dealerData.map((d) => (
                <tr key={d.dealer_id} className="hover:bg-slate-800/30 transition">
                  <td className="py-3 px-4 font-semibold text-white">
                    {d.dealer_name} <span className="font-mono text-slate-500 text-[10px]">({d.dealer_code})</span>
                  </td>
                  <td className="py-3 px-4 text-slate-300">{d.area_name}</td>
                  <td className="py-3 px-4 text-center font-mono font-bold text-indigo-300">{d.active_subscribers}</td>
                  <td className="py-3 px-4 text-right font-mono text-slate-300">PKR {d.invoiced_amount}</td>
                  <td className="py-3 px-4 text-right font-mono font-semibold text-emerald-400">PKR {d.collected_amount}</td>
                  <td className="py-3 px-4 text-right font-mono text-amber-400">PKR {d.commission_accrued}</td>
                  <td className="py-3 px-4 text-right font-mono text-purple-400">PKR {d.commission_settled}</td>
                  <td className="py-3 px-4 text-right font-mono font-bold text-white">PKR {d.net_isp_margin}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 7. RECOVERY & PROMISES TAB */}
      {/* ========================================================================= */}
      {activeTab === "recovery" && (
        <div className="space-y-6">
          {recoverySubTab === "ptp" && ptpData && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Total Promises</span>
                  <div className="text-2xl font-bold text-white mt-1">{ptpData.summary.total_promises}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Fulfilled Rate</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">{ptpData.summary.fulfillment_rate_percent}%</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Fulfilled Count</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">{ptpData.summary.fulfilled_count}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Broken Count</span>
                  <div className="text-2xl font-bold text-rose-400 mt-1">{ptpData.summary.broken_count}</div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Promise #</th>
                      <th className="py-3 px-4 font-semibold">Subscriber</th>
                      <th className="py-3 px-4 font-semibold text-right">Promised</th>
                      <th className="py-3 px-4 font-semibold">Deadline</th>
                      <th className="py-3 px-4 font-semibold text-center">Status</th>
                      <th className="py-3 px-4 font-semibold">Staff Officer</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {ptpData.records.map((p) => (
                      <tr key={p.id} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-4 font-mono font-bold text-indigo-300">{p.promise_number}</td>
                        <td className="py-3 px-4 font-semibold text-white">{p.customer_name}</td>
                        <td className="py-3 px-4 text-right font-mono font-semibold text-white">PKR {p.promised_amount}</td>
                        <td className="py-3 px-4 text-slate-300">{p.deadline}</td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                              p.status === "FULFILLED"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : p.status === "BROKEN"
                                ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                                : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            }`}
                          >
                            {p.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-400">{p.created_by}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {recoverySubTab === "officers" && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Recovery Officer</th>
                    <th className="py-3 px-4 font-semibold text-center">Total Allocated</th>
                    <th className="py-3 px-4 font-semibold text-center">Completed</th>
                    <th className="py-3 px-4 font-semibold text-right">Allocated Amount</th>
                    <th className="py-3 px-4 font-semibold text-right">Recovered Amount</th>
                    <th className="py-3 px-4 font-semibold text-center">Recovery Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {officerData.map((o) => (
                    <tr key={o.officer_id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-semibold text-white">{o.officer_name}</td>
                      <td className="py-3 px-4 text-center font-mono text-slate-300">{o.total_allocations}</td>
                      <td className="py-3 px-4 text-center font-mono font-semibold text-emerald-400">{o.completed_allocations}</td>
                      <td className="py-3 px-4 text-right font-mono text-slate-300">PKR {o.allocated_amount}</td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-emerald-400">PKR {o.recovered_amount}</td>
                      <td className="py-3 px-4 text-center font-mono font-bold text-emerald-400">{o.recovery_rate_percent}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 8. SUPPORT & SLA TAB */}
      {/* ========================================================================= */}
      {activeTab === "support" && supportSlaData && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">Total Registered Tickets</span>
              <div className="text-2xl font-bold text-white mt-1">{supportSlaData.summary.total_complaints}</div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">Resolved Complaints</span>
              <div className="text-2xl font-bold text-emerald-400 mt-1">{supportSlaData.summary.resolved_count}</div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">SLA Compliance Rate</span>
              <div className="text-2xl font-bold text-emerald-400 mt-1">{supportSlaData.summary.sla_compliance_rate_percent}%</div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-xs font-medium text-slate-400">SLA Breaches</span>
              <div className="text-2xl font-bold text-rose-400 mt-1">{supportSlaData.summary.breached_count}</div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-900/80">
              <h3 className="text-sm font-bold text-white">SLA Breaches by Complaint Category</h3>
            </div>
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                <tr>
                  <th className="py-3 px-4 font-semibold">Category</th>
                  <th className="py-3 px-4 font-semibold text-center">Total Volume</th>
                  <th className="py-3 px-4 font-semibold text-center">Breached Tickets</th>
                  <th className="py-3 px-4 font-semibold text-center">Breach Rate %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {supportSlaData.category_breakdown.map((cat) => (
                  <tr key={cat.category} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4 font-semibold text-white">{cat.category}</td>
                    <td className="py-3 px-4 text-center font-mono text-slate-300">{cat.total_count}</td>
                    <td className="py-3 px-4 text-center font-mono font-semibold text-rose-400">{cat.breached_count}</td>
                    <td className="py-3 px-4 text-center font-mono font-bold text-slate-200">{cat.breach_rate_percent}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 9. SALES & INVENTORY TAB */}
      {/* ========================================================================= */}
      {activeTab === "sales_inventory" && (
        <div className="space-y-6">
          {salesInvSubTab === "inquiries" && funnelData && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Total Leads</span>
                  <div className="text-2xl font-bold text-white mt-1">{funnelData.summary.total_inquiries}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Conversion Rate</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">{funnelData.summary.conversion_rate_percent}%</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Activated Subscribers</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">{funnelData.summary.converted_count}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Lost Inquiries</span>
                  <div className="text-2xl font-bold text-rose-400 mt-1">{funnelData.summary.lost_count}</div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
                <h3 className="text-sm font-bold text-white">Conversion Funnel Drop-off Progression</h3>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
                  {funnelData.funnel_stages.map((stage) => (
                    <div key={stage.stage} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                      <span className="text-xs font-semibold text-slate-300 block">{stage.stage}</span>
                      <div className="text-xl font-bold text-white font-mono mt-1">{stage.count}</div>
                      {stage.dropoff_percent > 0 && (
                        <span className="text-[10px] text-rose-400 font-mono mt-0.5 block">
                          -{stage.dropoff_percent}% dropoff
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {salesInvSubTab === "devices" && deviceData && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Total Tracked CPE Devices</span>
                  <div className="text-2xl font-bold text-white mt-1">{deviceData.summary.total_devices}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Deployed at Customers</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">{deviceData.summary.assigned_count}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">In Warehouse Stock</span>
                  <div className="text-2xl font-bold text-indigo-400 mt-1">{deviceData.summary.available_count}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <span className="text-xs font-medium text-slate-400">Faulty / In Repair</span>
                  <div className="text-2xl font-bold text-rose-400 mt-1">{deviceData.summary.faulty_count}</div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Asset Tag</th>
                      <th className="py-3 px-4 font-semibold">Type</th>
                      <th className="py-3 px-4 font-semibold">Manufacturer / Model</th>
                      <th className="py-3 px-4 font-semibold">Serial / MAC</th>
                      <th className="py-3 px-4 font-semibold text-center">Status</th>
                      <th className="py-3 px-4 font-semibold">Current Custody / Customer</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {deviceData.records.map((dev) => (
                      <tr key={dev.id} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-4 font-mono font-bold text-indigo-300">{dev.asset_tag}</td>
                        <td className="py-3 px-4 text-slate-300">{dev.device_type}</td>
                        <td className="py-3 px-4 text-white font-medium">{dev.manufacturer} {dev.model_name}</td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-400">{dev.serial_number} • {dev.mac_address}</td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                              dev.status === "ASSIGNED"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : dev.status === "AVAILABLE"
                                ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/20"
                                : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                            }`}
                          >
                            {dev.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300">{dev.assigned_customer}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}