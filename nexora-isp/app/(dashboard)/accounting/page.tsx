"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowDownLeft,
  ArrowRightLeft,
  ArrowUpRight,
  BookOpen,
  Building2,
  Calendar,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  Download,
  Eye,
  FileCheck,
  FileSpreadsheet,
  Filter,
  Landmark,
  Layers,
  Lock,
  Plus,
  Receipt,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Unlock,
  Wallet,
  X,
} from "lucide-react";

import {
  accountingService,
  type Account,
  type AccountingOverview,
  type DealerSettlementRecord,
  type DirectIncomeRecord,
  type ExpenseRecord,
  type FinancialPeriodRecord,
  type FundTransferRecord,
  type GeneralLedgerStatement,
  type JournalEntry,
  type TrialBalanceStatement,
} from "@/services/accounting.service";
import { dealersService, type DealerItem } from "@/services/dealers.service";
import Skeleton from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";

type TabKey =
  | "overview"
  | "coa"
  | "journals"
  | "ledger"
  | "expenses"
  | "income"
  | "transfers"
  | "dealers"
  | "trial-balance"
  | "periods";

export default function AccountingWorkspacePage() {
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [overview, setOverview] = useState<AccountingOverview | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [journals, setJournals] = useState<JournalEntry[]>([]);
  const [expenses, setExpenses] = useState<ExpenseRecord[]>([]);
  const [incomes, setIncomes] = useState<DirectIncomeRecord[]>([]);
  const [transfers, setTransfers] = useState<FundTransferRecord[]>([]);
  const [settlements, setSettlements] = useState<DealerSettlementRecord[]>([]);
  const [periods, setPeriods] = useState<FinancialPeriodRecord[]>([]);
  const [dealers, setDealers] = useState<DealerItem[]>([]);

  // General Ledger state
  const [selectedLedgerAccount, setSelectedLedgerAccount] = useState<string>("");
  const [ledgerStatement, setLedgerStatement] = useState<GeneralLedgerStatement | null>(null);
  const [ledgerLoading, setLedgerLoading] = useState(false);

  // Trial Balance state
  const [trialBalance, setTrialBalance] = useState<TrialBalanceStatement | null>(null);
  const [tbLoading, setTbLoading] = useState(false);

  // Modals
  const [showAddAccountModal, setShowAddAccountModal] = useState(false);
  const [showNewJournalModal, setShowNewJournalModal] = useState(false);
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [showIncomeModal, setShowIncomeModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [showSettlementModal, setShowSettlementModal] = useState(false);
  const [showAccrualModal, setShowAccrualModal] = useState(false);
  const [selectedJournalDetail, setSelectedJournalDetail] = useState<JournalEntry | null>(null);

  // Filters & Search
  const [coaCategoryFilter, setCoaCategoryFilter] = useState<string>("ALL");
  const [coaSearch, setCoaSearch] = useState<string>("");
  const [journalSearch, setJournalSearch] = useState<string>("");
  const [journalRefFilter, setJournalRefFilter] = useState<string>("ALL");

  // Form states
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Initial Load
  const loadBaseData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ovData, accData, jData, expData, incData, trfData, setlData, perData, dlrData] =
        await Promise.all([
          accountingService.getOverview().catch(() => null),
          accountingService.getAccounts().catch(() => []),
          accountingService.getJournalEntries().catch(() => []),
          accountingService.getExpenses().catch(() => []),
          accountingService.getDirectIncome().catch(() => []),
          accountingService.getFundTransfers().catch(() => []),
          accountingService.getDealerSettlements().catch(() => []),
          accountingService.getFinancialPeriods().catch(() => []),
          dealersService.getDealers().catch(() => []),
        ]);

      setOverview(ovData);
      setAccounts(accData);
      setJournals(jData);
      setExpenses(expData);
      setIncomes(incData);
      setTransfers(trfData);
      setSettlements(setlData);
      setPeriods(perData);
      setDealers(dlrData);

      if (accData.length > 0 && !selectedLedgerAccount) {
        setSelectedLedgerAccount(accData[0].id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load accounting data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBaseData();
  }, []);

  // Load General Ledger when selected account changes
  useEffect(() => {
    if (activeTab === "ledger" && selectedLedgerAccount) {
      loadLedger(selectedLedgerAccount);
    }
  }, [activeTab, selectedLedgerAccount]);

  const loadLedger = async (accId: string) => {
    setLedgerLoading(true);
    try {
      const stmt = await accountingService.getGeneralLedger({ account_id: accId });
      setLedgerStatement(stmt);
    } catch (err) {
      console.error(err);
    } finally {
      setLedgerLoading(false);
    }
  };

  // Load Trial Balance when trial-balance tab is active
  useEffect(() => {
    if (activeTab === "trial-balance") {
      loadTrialBalance();
    }
  }, [activeTab]);

  const loadTrialBalance = async () => {
    setTbLoading(true);
    try {
      const tb = await accountingService.getTrialBalance();
      setTrialBalance(tb);
    } catch (err) {
      console.error(err);
    } finally {
      setTbLoading(false);
    }
  };

  const currency = overview?.currency || "PKR";

  // Form helpers
  const assetAccounts = useMemo(() => accounts.filter((a) => a.category === "ASSET" && a.is_active), [accounts]);
  const expenseAccounts = useMemo(() => accounts.filter((a) => a.category === "EXPENSE" && a.is_active), [accounts]);
  const revenueAccounts = useMemo(() => accounts.filter((a) => a.category === "REVENUE" && a.is_active), [accounts]);

  const filteredAccounts = useMemo(() => {
    return accounts.filter((a) => {
      const matchesCat = coaCategoryFilter === "ALL" || a.category === coaCategoryFilter;
      const matchesSearch =
        !coaSearch ||
        a.code.toLowerCase().includes(coaSearch.toLowerCase()) ||
        a.name.toLowerCase().includes(coaSearch.toLowerCase()) ||
        a.description?.toLowerCase().includes(coaSearch.toLowerCase());
      return matchesCat && matchesSearch;
    });
  }, [accounts, coaCategoryFilter, coaSearch]);

  const filteredJournals = useMemo(() => {
    return journals.filter((j) => {
      const matchesRef = journalRefFilter === "ALL" || j.reference_type === journalRefFilter;
      const matchesSearch =
        !journalSearch ||
        j.entry_number.toLowerCase().includes(journalSearch.toLowerCase()) ||
        j.narration.toLowerCase().includes(journalSearch.toLowerCase()) ||
        j.reference_id.toLowerCase().includes(journalSearch.toLowerCase());
      return matchesRef && matchesSearch;
    });
  }, [journals, journalRefFilter, journalSearch]);

  // Handle Reverse Journal
  const handleReverseJournal = async (entry: JournalEntry) => {
    const reason = prompt(`Enter reason for reversing journal ${entry.entry_number}:`);
    if (!reason) return;
    try {
      await accountingService.reverseJournalEntry(entry.id, reason);
      await loadBaseData();
      alert("Journal entry reversed successfully.");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to reverse journal entry.");
    }
  };

  // Handle Close / Reopen Period
  const handleTogglePeriod = async (period: FinancialPeriodRecord) => {
    if (period.is_closed) {
      const reason = prompt(`Enter authorization reason to reopen ${period.name}:`);
      if (!reason) return;
      try {
        await accountingService.reopenFinancialPeriod(period.id, reason);
        await loadBaseData();
      } catch (err: unknown) {
        alert(err instanceof Error ? err.message : "Failed to reopen period.");
      }
    } else {
      if (!confirm(`Are you sure you want to close financial period ${period.name}? No further entries can be posted into this period.`)) return;
      try {
        await accountingService.closeFinancialPeriod(period.id);
        await loadBaseData();
      } catch (err: unknown) {
        alert(err instanceof Error ? err.message : "Failed to close period.");
      }
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 pb-12">
        <Skeleton className="h-10 w-64 rounded-lg" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-2xl" />
          ))}
        </div>
        <Skeleton className="h-96 w-full rounded-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12">
        <ErrorState message={error} onRetry={loadBaseData} />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-16">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Accounting & Financial Ledger
            </h1>
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
              Double-Entry GL
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Enterprise Chart of Accounts, General Ledger, Cash/Bank management, and financial integrity controls.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowExpenseModal(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-2 text-xs font-semibold text-rose-400 hover:bg-rose-500/20 transition shadow-sm"
          >
            <TrendingDown className="h-4 w-4" />
            Record Expense
          </button>
          <button
            onClick={() => setShowIncomeModal(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-2 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20 transition shadow-sm"
          >
            <TrendingUp className="h-4 w-4" />
            Direct Income
          </button>
          <button
            onClick={() => setShowTransferModal(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-3.5 py-2 text-xs font-semibold text-indigo-400 hover:bg-indigo-500/20 transition shadow-sm"
          >
            <ArrowRightLeft className="h-4 w-4" />
            Transfer Funds
          </button>
          <button
            onClick={() => setShowNewJournalModal(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-500 transition"
          >
            <Plus className="h-4 w-4" />
            New Journal Entry
          </button>
          <button
            onClick={loadBaseData}
            title="Refresh"
            className="rounded-xl border border-slate-800 bg-slate-900/80 p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/90 to-slate-950/90 p-4 shadow-sm backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Cash & Bank Balance</span>
            <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-400 border border-emerald-500/20">
              <Landmark className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold tracking-tight text-white">
              {currency} {Number(overview?.metrics.cash_bank_balance || 0).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
            </div>
            <p className="text-[11px] text-emerald-400/90 mt-0.5">Liquid Available Capital</p>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/90 to-slate-950/90 p-4 shadow-sm backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Accounts Receivable</span>
            <div className="rounded-lg bg-amber-500/10 p-2 text-amber-400 border border-amber-500/20">
              <Receipt className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold tracking-tight text-white">
              {currency} {Number(overview?.metrics.receivables_balance || 0).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
            </div>
            <p className="text-[11px] text-amber-400/90 mt-0.5">Unsettled Invoices</p>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/90 to-slate-950/90 p-4 shadow-sm backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">MTD Revenue</span>
            <div className="rounded-lg bg-indigo-500/10 p-2 text-indigo-400 border border-indigo-500/20">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold tracking-tight text-white">
              {currency} {Number(overview?.metrics.mtd_revenue || 0).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
            </div>
            <p className="text-[11px] text-indigo-400/90 mt-0.5">Subscriptions & Fees</p>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/90 to-slate-950/90 p-4 shadow-sm backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">MTD Expenses</span>
            <div className="rounded-lg bg-rose-500/10 p-2 text-rose-400 border border-rose-500/20">
              <TrendingDown className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold tracking-tight text-white">
              {currency} {Number(overview?.metrics.mtd_expenses || 0).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
            </div>
            <p className="text-[11px] text-rose-400/90 mt-0.5">Transit, Power & Ops</p>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/90 to-slate-950/90 p-4 shadow-sm backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Net Operating Margin</span>
            <div className="rounded-lg bg-cyan-500/10 p-2 text-cyan-400 border border-cyan-500/20">
              <CircleDollarSign className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold tracking-tight text-white">
              {currency} {Number(overview?.metrics.net_margin || 0).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
            </div>
            <p className="text-[11px] text-cyan-400/90 mt-0.5">Net Operating Surplus</p>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex overflow-x-auto border-b border-slate-800/80 no-scrollbar">
        <div className="flex gap-1">
          {[
            { key: "overview", label: "Overview & Accounts", icon: Layers },
            { key: "coa", label: "Chart of Accounts", icon: BookOpen },
            { key: "journals", label: "Journal Entries", icon: FileCheck },
            { key: "ledger", label: "General Ledger", icon: FileSpreadsheet },
            { key: "expenses", label: "Expenses", icon: TrendingDown },
            { key: "income", label: "Direct Income", icon: TrendingUp },
            { key: "transfers", label: "Fund Transfers", icon: ArrowRightLeft },
            { key: "dealers", label: "Dealer Settlements", icon: Building2 },
            { key: "trial-balance", label: "Trial Balance", icon: ShieldCheck },
            { key: "periods", label: "Fiscal Periods", icon: Lock },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as TabKey)}
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

      {/* TAB CONTENT: 1. OVERVIEW & LIQUID ACCOUNTS */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Cash & Bank Drawers */}
            <div className="lg:col-span-1 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Wallet className="h-4 w-4 text-emerald-400" />
                  Liquid Cash & Bank Accounts
                </h2>
                <button
                  onClick={() => setShowTransferModal(true)}
                  className="text-xs font-medium text-indigo-400 hover:underline"
                >
                  Transfer
                </button>
              </div>

              <div className="space-y-3">
                {overview?.cash_bank_accounts.map((acc) => (
                  <div
                    key={acc.id}
                    className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 flex items-center justify-between hover:border-slate-700 transition"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-1.5 py-0.5 rounded">
                          {acc.code}
                        </span>
                        <p className="text-xs font-semibold text-white">{acc.name}</p>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">{acc.account_type.replace(/_/g, " ")}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm font-bold text-emerald-400">
                        {currency} {Number(acc.balance).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                      </p>
                      <button
                        onClick={() => {
                          setSelectedLedgerAccount(acc.id);
                          setActiveTab("ledger");
                        }}
                        className="text-[10px] text-slate-400 hover:text-white flex items-center gap-0.5 justify-end mt-0.5"
                      >
                        Ledger <ChevronRight className="h-2.5 w-2.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Double-Entry Journal Activity */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <FileCheck className="h-4 w-4 text-indigo-400" />
                  Recent Double-Entry Journal Activity
                </h2>
                <button
                  onClick={() => setActiveTab("journals")}
                  className="text-xs font-medium text-indigo-400 hover:underline"
                >
                  View All ({journals.length})
                </button>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                      <tr>
                        <th className="py-3 px-4 font-semibold">Entry Number</th>
                        <th className="py-3 px-4 font-semibold">Date</th>
                        <th className="py-3 px-4 font-semibold">Narration</th>
                        <th className="py-3 px-4 font-semibold">Type</th>
                        <th className="py-3 px-4 font-semibold text-right">Debit = Credit</th>
                        <th className="py-3 px-4 font-semibold text-center">Status</th>
                        <th className="py-3 px-4 font-semibold text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {overview?.recent_journals.map((entry) => (
                        <tr key={entry.id} className="hover:bg-slate-800/30 transition">
                          <td className="py-3 px-4 font-mono font-semibold text-indigo-300">
                            {entry.entry_number}
                          </td>
                          <td className="py-3 px-4 text-slate-300">{entry.date}</td>
                          <td className="py-3 px-4 text-slate-200 max-w-xs truncate" title={entry.narration}>
                            {entry.narration}
                          </td>
                          <td className="py-3 px-4">
                            <span className="rounded-full bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] font-medium text-slate-300">
                              {entry.reference_type}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right font-mono font-semibold text-white">
                            {currency} {Number(entry.total_debit).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                                entry.status === "POSTED"
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                  : entry.status === "REVERSED"
                                  ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                                  : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                              }`}
                            >
                              {entry.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-center">
                            <button
                              onClick={() => setSelectedJournalDetail(entry)}
                              className="rounded-lg p-1 text-slate-400 hover:text-white hover:bg-slate-800 transition"
                              title="View lines"
                            >
                              <Eye className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 2. CHART OF ACCOUNTS */}
      {activeTab === "coa" && (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-1.5">
              {["ALL", "ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCoaCategoryFilter(cat)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                    coaCategoryFilter === cat
                      ? "bg-indigo-600 text-white shadow"
                      : "bg-slate-900/80 text-slate-400 border border-slate-800 hover:text-white"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search code, name..."
                  value={coaSearch}
                  onChange={(e) => setCoaSearch(e.target.value)}
                  className="rounded-xl border border-slate-800 bg-slate-900/80 pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>
              <button
                onClick={() => setShowAddAccountModal(true)}
                className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 transition"
              >
                <Plus className="h-3.5 w-3.5" /> Add Account
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Account Code</th>
                    <th className="py-3 px-4 font-semibold">Account Name</th>
                    <th className="py-3 px-4 font-semibold">Category</th>
                    <th className="py-3 px-4 font-semibold">Subtype</th>
                    <th className="py-3 px-4 font-semibold">Description</th>
                    <th className="py-3 px-4 font-semibold text-center">System Protected</th>
                    <th className="py-3 px-4 font-semibold text-center">Status</th>
                    <th className="py-3 px-4 font-semibold text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredAccounts.map((acc) => (
                    <tr key={acc.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-mono font-bold text-indigo-300">{acc.code}</td>
                      <td className="py-3 px-4 font-semibold text-white">{acc.name}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                            acc.category === "ASSET"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : acc.category === "LIABILITY"
                              ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                              : acc.category === "EQUITY"
                              ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                              : acc.category === "REVENUE"
                              ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/20"
                              : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          }`}
                        >
                          {acc.category}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">{acc.account_type.replace(/_/g, " ")}</td>
                      <td className="py-3 px-4 text-slate-400 max-w-xs truncate">{acc.description || "-"}</td>
                      <td className="py-3 px-4 text-center">
                        {acc.is_system ? (
                          <span className="text-[10px] text-indigo-400 font-semibold bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                            CORE SYSTEM
                          </span>
                        ) : (
                          <span className="text-slate-500 text-[10px]">Custom</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                            acc.is_active
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : "bg-slate-500/10 text-slate-400 border-slate-500/20"
                          }`}
                        >
                          {acc.is_active ? "ACTIVE" : "INACTIVE"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={() => {
                            setSelectedLedgerAccount(acc.id);
                            setActiveTab("ledger");
                          }}
                          className="rounded-lg bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-300 hover:text-white hover:bg-slate-700 transition"
                        >
                          View Ledger
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 3. JOURNAL ENTRIES */}
      {activeTab === "journals" && (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={journalRefFilter}
                onChange={(e) => setJournalRefFilter(e.target.value)}
                className="rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-300 focus:border-indigo-500 focus:outline-none"
              >
                <option value="ALL">All Reference Types</option>
                <option value="MANUAL">Manual Journal</option>
                <option value="INVOICE">Invoice</option>
                <option value="PAYMENT">Payment</option>
                <option value="PAYMENT_REVERSAL">Payment Reversal</option>
                <option value="INVOICE_CANCEL">Invoice Cancellation</option>
                <option value="EXPENSE">Expense</option>
                <option value="INCOME">Direct Income</option>
                <option value="TRANSFER">Fund Transfer</option>
                <option value="DEALER_ACCRUAL">Dealer Accrual</option>
                <option value="DEALER_SETTLEMENT">Dealer Settlement</option>
              </select>

              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search journals..."
                  value={journalSearch}
                  onChange={(e) => setJournalSearch(e.target.value)}
                  className="rounded-xl border border-slate-800 bg-slate-900/80 pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            <button
              onClick={() => setShowNewJournalModal(true)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 transition"
            >
              <Plus className="h-3.5 w-3.5" /> Post Balanced Journal
            </button>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Entry #</th>
                    <th className="py-3 px-4 font-semibold">Date</th>
                    <th className="py-3 px-4 font-semibold">Narration</th>
                    <th className="py-3 px-4 font-semibold">Reference Type</th>
                    <th className="py-3 px-4 font-semibold">Reference ID</th>
                    <th className="py-3 px-4 font-semibold text-right">Debit = Credit</th>
                    <th className="py-3 px-4 font-semibold text-center">Status</th>
                    <th className="py-3 px-4 font-semibold text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredJournals.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-mono font-bold text-indigo-300">{entry.entry_number}</td>
                      <td className="py-3 px-4 text-slate-300">{entry.date}</td>
                      <td className="py-3 px-4 text-slate-200 max-w-sm truncate" title={entry.narration}>
                        {entry.narration}
                      </td>
                      <td className="py-3 px-4 text-slate-300">{entry.reference_type}</td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-400 max-w-[120px] truncate">
                        {entry.reference_id || "-"}
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-semibold text-white">
                        {currency} {Number(entry.total_debit).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                            entry.status === "POSTED"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : entry.status === "REVERSED"
                              ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                              : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                          }`}
                        >
                          {entry.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => setSelectedJournalDetail(entry)}
                            className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition"
                            title="View Lines"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </button>
                          {entry.status === "POSTED" && (
                            <button
                              onClick={() => handleReverseJournal(entry)}
                              className="rounded-lg p-1.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition"
                              title="Reverse Journal"
                            >
                              <RotateCcw className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 4. GENERAL LEDGER */}
      {activeTab === "ledger" && (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <label className="text-xs font-medium text-slate-400">Select Account:</label>
              <select
                value={selectedLedgerAccount}
                onChange={(e) => setSelectedLedgerAccount(e.target.value)}
                className="rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none min-w-[280px]"
              >
                {accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.code} — {acc.name} ({acc.category})
                  </option>
                ))}
              </select>
            </div>

            {ledgerStatement && (
              <div className="flex items-center gap-4 text-xs">
                <span className="text-slate-400">
                  Opening: <strong className="text-white font-mono">{currency} {ledgerStatement.opening_balance}</strong>
                </span>
                <span className="text-slate-400">
                  Closing: <strong className="text-emerald-400 font-mono">{currency} {ledgerStatement.closing_balance}</strong>
                </span>
              </div>
            )}
          </div>

          {ledgerLoading ? (
            <Skeleton className="h-64 w-full rounded-2xl" />
          ) : ledgerStatement ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
                <div>
                  <h3 className="text-sm font-bold text-white">
                    {ledgerStatement.account.code} — {ledgerStatement.account.name}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Category: {ledgerStatement.account.category} • Normal Side: {ledgerStatement.account.normal_side}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-400">Net Period Change: </span>
                  <span className="font-mono text-xs font-bold text-indigo-400">
                    {currency} {Number(ledgerStatement.net_change).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Date</th>
                      <th className="py-3 px-4 font-semibold">Entry #</th>
                      <th className="py-3 px-4 font-semibold">Narration</th>
                      <th className="py-3 px-4 font-semibold">Description</th>
                      <th className="py-3 px-4 font-semibold text-right">Debit</th>
                      <th className="py-3 px-4 font-semibold text-right">Credit</th>
                      <th className="py-3 px-4 font-semibold text-right">Running Balance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {ledgerStatement.entries.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-slate-500">
                          No transactions recorded for this account.
                        </td>
                      </tr>
                    ) : (
                      ledgerStatement.entries.map((item) => (
                        <tr key={item.id} className="hover:bg-slate-800/30 transition">
                          <td className="py-3 px-4 text-slate-300">{item.date}</td>
                          <td className="py-3 px-4 font-mono font-semibold text-indigo-300">{item.entry_number}</td>
                          <td className="py-3 px-4 text-slate-200 max-w-xs truncate">{item.narration}</td>
                          <td className="py-3 px-4 text-slate-400">{item.description || "-"}</td>
                          <td className="py-3 px-4 text-right font-mono font-semibold text-emerald-400">
                            {Number(item.debit) > 0 ? `${currency} ${Number(item.debit).toLocaleString("en-PK", { minimumFractionDigits: 2 })}` : "-"}
                          </td>
                          <td className="py-3 px-4 text-right font-mono font-semibold text-rose-400">
                            {Number(item.credit) > 0 ? `${currency} ${Number(item.credit).toLocaleString("en-PK", { minimumFractionDigits: 2 })}` : "-"}
                          </td>
                          <td className="py-3 px-4 text-right font-mono font-bold text-white">
                            {currency} {Number(item.running_balance).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* TAB CONTENT: 5. EXPENSES */}
      {activeTab === "expenses" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-rose-400" /> Operational Expense Ledger
            </h2>
            <button
              onClick={() => setShowExpenseModal(true)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-500 transition shadow"
            >
              <Plus className="h-3.5 w-3.5" /> Record Expense
            </button>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Expense #</th>
                    <th className="py-3 px-4 font-semibold">Date</th>
                    <th className="py-3 px-4 font-semibold">Payee</th>
                    <th className="py-3 px-4 font-semibold">Category</th>
                    <th className="py-3 px-4 font-semibold">Expense Account</th>
                    <th className="py-3 px-4 font-semibold">Paid From</th>
                    <th className="py-3 px-4 font-semibold text-right">Amount</th>
                    <th className="py-3 px-4 font-semibold">Journal #</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {expenses.map((exp) => (
                    <tr key={exp.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-mono font-bold text-rose-300">{exp.expense_number}</td>
                      <td className="py-3 px-4 text-slate-300">{exp.date}</td>
                      <td className="py-3 px-4 font-semibold text-white">{exp.payee || "-"}</td>
                      <td className="py-3 px-4">
                        <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300 border border-slate-700">
                          {exp.category || "General"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-300">{exp.expense_account_name}</td>
                      <td className="py-3 px-4 text-slate-300">{exp.payment_account_name}</td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-rose-400">
                        {currency} {Number(exp.amount).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-indigo-400">{exp.journal_entry_number || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 6. DIRECT INCOME */}
      {activeTab === "income" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-400" /> Direct Non-Subscriber Income
            </h2>
            <button
              onClick={() => setShowIncomeModal(true)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 transition shadow"
            >
              <Plus className="h-3.5 w-3.5" /> Record Income
            </button>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Income #</th>
                    <th className="py-3 px-4 font-semibold">Date</th>
                    <th className="py-3 px-4 font-semibold">Received From</th>
                    <th className="py-3 px-4 font-semibold">Revenue Head</th>
                    <th className="py-3 px-4 font-semibold">Deposited Into</th>
                    <th className="py-3 px-4 font-semibold text-right">Amount</th>
                    <th className="py-3 px-4 font-semibold">Journal #</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {incomes.map((inc) => (
                    <tr key={inc.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-mono font-bold text-emerald-300">{inc.income_number}</td>
                      <td className="py-3 px-4 text-slate-300">{inc.date}</td>
                      <td className="py-3 px-4 font-semibold text-white">{inc.received_from || "-"}</td>
                      <td className="py-3 px-4 text-slate-300">{inc.income_account_name}</td>
                      <td className="py-3 px-4 text-slate-300">{inc.deposit_account_name}</td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-emerald-400">
                        {currency} {Number(inc.amount).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-indigo-400">{inc.journal_entry_number || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 7. FUND TRANSFERS */}
      {activeTab === "transfers" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <ArrowRightLeft className="h-4 w-4 text-indigo-400" /> Cash & Bank Fund Transfers
            </h2>
            <button
              onClick={() => setShowTransferModal(true)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 transition shadow"
            >
              <Plus className="h-3.5 w-3.5" /> Transfer Funds
            </button>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Transfer #</th>
                    <th className="py-3 px-4 font-semibold">Date</th>
                    <th className="py-3 px-4 font-semibold">Source Account</th>
                    <th className="py-3 px-4 font-semibold">Destination Account</th>
                    <th className="py-3 px-4 font-semibold text-right">Amount</th>
                    <th className="py-3 px-4 font-semibold">Reference</th>
                    <th className="py-3 px-4 font-semibold">Journal #</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {transfers.map((trf) => (
                    <tr key={trf.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-mono font-bold text-indigo-300">{trf.transfer_number}</td>
                      <td className="py-3 px-4 text-slate-300">{trf.date}</td>
                      <td className="py-3 px-4 text-rose-300 font-medium">{trf.from_account_name}</td>
                      <td className="py-3 px-4 text-emerald-300 font-medium">{trf.to_account_name}</td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-white">
                        {currency} {Number(trf.amount).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 text-slate-400">{trf.reference || "-"}</td>
                      <td className="py-3 px-4 font-mono text-[11px] text-indigo-400">{trf.journal_entry_number || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 8. DEALER SETTLEMENTS */}
      {activeTab === "dealers" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Building2 className="h-4 w-4 text-indigo-400" /> Dealer Commission Accruals & Payout Settlements
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowAccrualModal(true)}
                className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs font-semibold text-indigo-400 hover:bg-indigo-500/20 transition"
              >
                <Plus className="h-3.5 w-3.5" /> Accrue Commission
              </button>
              <button
                onClick={() => setShowSettlementModal(true)}
                className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 transition shadow"
              >
                <Plus className="h-3.5 w-3.5" /> Record Payout Settlement
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Settlement #</th>
                    <th className="py-3 px-4 font-semibold">Date</th>
                    <th className="py-3 px-4 font-semibold">Dealer / Partner</th>
                    <th className="py-3 px-4 font-semibold">Period Covered</th>
                    <th className="py-3 px-4 font-semibold">Disbursed From</th>
                    <th className="py-3 px-4 font-semibold text-right">Amount</th>
                    <th className="py-3 px-4 font-semibold">Journal #</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {settlements.map((setl) => (
                    <tr key={setl.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-mono font-bold text-indigo-300">{setl.settlement_number}</td>
                      <td className="py-3 px-4 text-slate-300">{setl.settlement_date}</td>
                      <td className="py-3 px-4 font-semibold text-white">
                        {setl.dealer_name}{" "}
                        <span className="font-mono text-[10px] text-slate-400">({setl.dealer_code})</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {setl.period_start} to {setl.period_end}
                      </td>
                      <td className="py-3 px-4 text-slate-300">{setl.payment_account_name}</td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-emerald-400">
                        {currency} {Number(setl.amount).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-indigo-400">{setl.journal_entry_number || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 9. TRIAL BALANCE */}
      {activeTab === "trial-balance" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-indigo-400" /> Periodic Trial Balance Statement
              </h2>
              <p className="text-[11px] text-slate-400">Authoritative balance validation across all Chart of Accounts.</p>
            </div>
            {trialBalance && (
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold border flex items-center gap-1.5 ${
                  trialBalance.is_balanced
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                    : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                }`}
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                {trialBalance.is_balanced ? "DEBITS = CREDITS BALANCED" : "UNBALANCED WARNING"}
              </span>
            )}
          </div>

          {tbLoading ? (
            <Skeleton className="h-64 w-full rounded-2xl" />
          ) : trialBalance ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/90 text-slate-400">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Account Code</th>
                      <th className="py-3 px-4 font-semibold">Account Name</th>
                      <th className="py-3 px-4 font-semibold">Category</th>
                      <th className="py-3 px-4 font-semibold text-right">Debit Total</th>
                      <th className="py-3 px-4 font-semibold text-right">Credit Total</th>
                      <th className="py-3 px-4 font-semibold text-right">Net Balance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {trialBalance.accounts.map((row) => (
                      <tr key={row.account_id} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-4 font-mono font-bold text-indigo-300">{row.code}</td>
                        <td className="py-3 px-4 font-semibold text-white">{row.name}</td>
                        <td className="py-3 px-4 text-slate-400">{row.category}</td>
                        <td className="py-3 px-4 text-right font-mono font-semibold text-emerald-400">
                          {Number(row.debit_total) > 0 ? `${currency} ${Number(row.debit_total).toLocaleString("en-PK", { minimumFractionDigits: 2 })}` : "-"}
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-semibold text-rose-400">
                          {Number(row.credit_total) > 0 ? `${currency} ${Number(row.credit_total).toLocaleString("en-PK", { minimumFractionDigits: 2 })}` : "-"}
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-white">
                          {currency} {Number(row.net_balance).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="border-t-2 border-slate-700 bg-slate-900 text-white font-bold font-mono">
                    <tr>
                      <td colSpan={3} className="py-3 px-4 text-right uppercase tracking-wider">
                        Total Sum:
                      </td>
                      <td className="py-3 px-4 text-right text-emerald-400">
                        {currency} {Number(trialBalance.total_debits).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 text-right text-rose-400">
                        {currency} {Number(trialBalance.total_credits).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 text-right text-indigo-400">
                        {trialBalance.is_balanced ? "BALANCED" : "MISMATCH"}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* TAB CONTENT: 10. FISCAL PERIODS */}
      {activeTab === "periods" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Lock className="h-4 w-4 text-indigo-400" /> Fiscal Period Locking & Controls
              </h2>
              <p className="text-[11px] text-slate-400">Closing a period blocks accidental backdated transactions.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {periods.map((per) => (
              <div
                key={per.id}
                className={`rounded-2xl border p-4 transition ${
                  per.is_closed
                    ? "border-rose-500/30 bg-rose-500/5"
                    : "border-emerald-500/30 bg-emerald-500/5"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-base font-bold text-white">{per.name}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                        per.is_closed
                          ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      }`}
                    >
                      {per.is_closed ? "LOCKED" : "OPEN"}
                    </span>
                  </div>
                  <button
                    onClick={() => handleTogglePeriod(per)}
                    className={`rounded-xl px-3 py-1.5 text-xs font-semibold border transition ${
                      per.is_closed
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                        : "border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20"
                    }`}
                  >
                    {per.is_closed ? "Reopen Period" : "Lock / Close Period"}
                  </button>
                </div>

                <div className="mt-3 text-xs text-slate-400 space-y-1">
                  <p>Start Date: <span className="text-slate-200 font-mono">{per.start_date}</span></p>
                  <p>End Date: <span className="text-slate-200 font-mono">{per.end_date}</span></p>
                  {per.closed_at && (
                    <p className="text-[11px] text-rose-400">
                      Closed by {per.closed_by_name || "Admin"} on {new Date(per.closed_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: JOURNAL DETAIL DRAWER */}
      {/* ========================================================================= */}
      {selectedJournalDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">
                  Journal Entry: {selectedJournalDetail.entry_number}
                </h3>
                <p className="text-xs text-slate-400">
                  {selectedJournalDetail.date} • {selectedJournalDetail.reference_type}
                </p>
              </div>
              <button
                onClick={() => setSelectedJournalDetail(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300 bg-slate-800/40 p-3 rounded-xl border border-slate-800">
              {selectedJournalDetail.narration}
            </p>

            <div className="rounded-xl border border-slate-800 overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-800/80 text-slate-400">
                  <tr>
                    <th className="py-2.5 px-3">Account Code</th>
                    <th className="py-2.5 px-3">Account Name</th>
                    <th className="py-2.5 px-3 text-right">Debit</th>
                    <th className="py-2.5 px-3 text-right">Credit</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {selectedJournalDetail.lines?.map((line, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/20">
                      <td className="py-2.5 px-3 font-mono text-indigo-400 font-bold">{line.account_code}</td>
                      <td className="py-2.5 px-3 text-slate-200">{line.account_name}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-emerald-400">
                        {Number(line.debit) > 0 ? `${currency} ${Number(line.debit).toLocaleString("en-PK", { minimumFractionDigits: 2 })}` : "-"}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-rose-400">
                        {Number(line.credit) > 0 ? `${currency} ${Number(line.credit).toLocaleString("en-PK", { minimumFractionDigits: 2 })}` : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-slate-800 font-bold font-mono text-white">
                  <tr>
                    <td colSpan={2} className="py-2 px-3 text-right">Totals:</td>
                    <td className="py-2 px-3 text-right text-emerald-400">
                      {currency} {Number(selectedJournalDetail.total_debit).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-3 text-right text-rose-400">
                      {currency} {Number(selectedJournalDetail.total_credit).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedJournalDetail(null)}
                className="rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: RECORD EXPENSE */}
      {/* ========================================================================= */}
      {showExpenseModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <TrendingDown className="h-5 w-5 text-rose-400" /> Record Operational Expense
              </h3>
              <button onClick={() => setShowExpenseModal(false)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                {actionError}
              </div>
            )}

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setSubmitting(true);
                setActionError(null);
                const fd = new FormData(e.currentTarget);
                try {
                  await accountingService.createExpense({
                    expense_account_id: fd.get("expense_account_id") as string,
                    payment_account_id: fd.get("payment_account_id") as string,
                    amount: fd.get("amount") as string,
                    date: fd.get("date") as string,
                    payee: fd.get("payee") as string,
                    category: fd.get("category") as string,
                    reference: fd.get("reference") as string,
                    description: fd.get("description") as string,
                  });
                  setShowExpenseModal(false);
                  await loadBaseData();
                } catch (err: unknown) {
                  setActionError(err instanceof Error ? err.message : "Failed to record expense.");
                } finally {
                  setSubmitting(false);
                }
              }}
              className="space-y-3 text-xs"
            >
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Expense Account (Head)</label>
                  <select
                    name="expense_account_id"
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  >
                    {expenseAccounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.code} — {a.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Paid From Account (Asset)</label>
                  <select
                    name="payment_account_id"
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  >
                    {assetAccounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.code} — {a.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Amount ({currency})</label>
                  <input
                    type="number"
                    step="0.01"
                    name="amount"
                    required
                    placeholder="0.00"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Date</label>
                  <input
                    type="date"
                    name="date"
                    defaultValue={new Date().toISOString().split("T")[0]}
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Payee / Vendor</label>
                  <input
                    type="text"
                    name="payee"
                    placeholder="e.g. Bandwidth Provider"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Category</label>
                  <input
                    type="text"
                    name="category"
                    placeholder="e.g. Bandwidth, Utilities, Fuel"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">Description / Notes</label>
                <textarea
                  name="description"
                  rows={2}
                  placeholder="Additional context..."
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowExpenseModal(false)}
                  className="rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-500 shadow"
                >
                  {submitting ? "Posting..." : "Record & Post Expense"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: DIRECT INCOME */}
      {/* ========================================================================= */}
      {showIncomeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-emerald-400" /> Record Direct Income
              </h3>
              <button onClick={() => setShowIncomeModal(false)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                {actionError}
              </div>
            )}

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setSubmitting(true);
                setActionError(null);
                const fd = new FormData(e.currentTarget);
                try {
                  await accountingService.createDirectIncome({
                    income_account_id: fd.get("income_account_id") as string,
                    deposit_account_id: fd.get("deposit_account_id") as string,
                    amount: fd.get("amount") as string,
                    date: fd.get("date") as string,
                    received_from: fd.get("received_from") as string,
                    reference: fd.get("reference") as string,
                    description: fd.get("description") as string,
                  });
                  setShowIncomeModal(false);
                  await loadBaseData();
                } catch (err: unknown) {
                  setActionError(err instanceof Error ? err.message : "Failed to record income.");
                } finally {
                  setSubmitting(false);
                }
              }}
              className="space-y-3 text-xs"
            >
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Income Head (Revenue)</label>
                  <select
                    name="income_account_id"
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  >
                    {revenueAccounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.code} — {a.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Deposit Account (Asset)</label>
                  <select
                    name="deposit_account_id"
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  >
                    {assetAccounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.code} — {a.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Amount ({currency})</label>
                  <input
                    type="number"
                    step="0.01"
                    name="amount"
                    required
                    placeholder="0.00"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Date</label>
                  <input
                    type="date"
                    name="date"
                    defaultValue={new Date().toISOString().split("T")[0]}
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">Received From</label>
                <input
                  type="text"
                  name="received_from"
                  placeholder="e.g. Customer Name, Buyer"
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">Description</label>
                <textarea
                  name="description"
                  rows={2}
                  placeholder="Details of income..."
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowIncomeModal(false)}
                  className="rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 shadow"
                >
                  {submitting ? "Posting..." : "Record & Post Income"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: FUND TRANSFER */}
      {/* ========================================================================= */}
      {showTransferModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <ArrowRightLeft className="h-5 w-5 text-indigo-400" /> Cash / Bank Fund Transfer
              </h3>
              <button onClick={() => setShowTransferModal(false)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                {actionError}
              </div>
            )}

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setSubmitting(true);
                setActionError(null);
                const fd = new FormData(e.currentTarget);
                try {
                  await accountingService.createFundTransfer({
                    from_account_id: fd.get("from_account_id") as string,
                    to_account_id: fd.get("to_account_id") as string,
                    amount: fd.get("amount") as string,
                    date: fd.get("date") as string,
                    reference: fd.get("reference") as string,
                    description: fd.get("description") as string,
                  });
                  setShowTransferModal(false);
                  await loadBaseData();
                } catch (err: unknown) {
                  setActionError(err instanceof Error ? err.message : "Failed to transfer funds.");
                } finally {
                  setSubmitting(false);
                }
              }}
              className="space-y-3 text-xs"
            >
              <div>
                <label className="text-slate-400 block mb-1 font-medium">Source Account (Outflow)</label>
                <select
                  name="from_account_id"
                  required
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                >
                  {assetAccounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.code} — {a.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">Destination Account (Inflow)</label>
                <select
                  name="to_account_id"
                  required
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                >
                  {assetAccounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.code} — {a.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Amount ({currency})</label>
                  <input
                    type="number"
                    step="0.01"
                    name="amount"
                    required
                    placeholder="0.00"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1 font-medium">Date</label>
                  <input
                    type="date"
                    name="date"
                    defaultValue={new Date().toISOString().split("T")[0]}
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-medium">Reference / Cheque #</label>
                <input
                  type="text"
                  name="reference"
                  placeholder="e.g. CHQ-99001"
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowTransferModal(false)}
                  className="rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 shadow"
                >
                  {submitting ? "Transferring..." : "Execute Transfer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: POST BALANCED MANUAL JOURNAL */}
      {/* ========================================================================= */}
      {showNewJournalModal && (
        <NewJournalEntryModal
          accounts={accounts}
          currency={currency}
          onClose={() => setShowNewJournalModal(false)}
          onSuccess={async () => {
            setShowNewJournalModal(false);
            await loadBaseData();
          }}
        />
      )}
    </div>
  );
}

// Subcomponent: New Balanced Journal Entry Modal
function NewJournalEntryModal({
  accounts,
  currency,
  onClose,
  onSuccess,
}: {
  accounts: Account[];
  currency: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [txnDate, setTxnDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [narration, setNarration] = useState<string>("");
  const [lines, setLines] = useState<
    Array<{ account_id: string; debit: string; credit: string; description: string }>
  >([
    { account_id: accounts[0]?.id || "", debit: "0", credit: "0", description: "" },
    { account_id: accounts[1]?.id || "", debit: "0", credit: "0", description: "" },
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalDebit = useMemo(() => {
    return lines.reduce((acc, curr) => acc + (Number(curr.debit) || 0), 0);
  }, [lines]);

  const totalCredit = useMemo(() => {
    return lines.reduce((acc, curr) => acc + (Number(curr.credit) || 0), 0);
  }, [lines]);

  const isBalanced = useMemo(() => {
    return totalDebit > 0 && Math.abs(totalDebit - totalCredit) < 0.001;
  }, [totalDebit, totalCredit]);

  const handleLineChange = (index: number, field: string, val: string) => {
    const next = [...lines];
    next[index] = { ...next[index], [field]: val };
    setLines(next);
  };

  const handleAddLine = () => {
    setLines([...lines, { account_id: accounts[0]?.id || "", debit: "0", credit: "0", description: "" }]);
  };

  const handleRemoveLine = (idx: number) => {
    if (lines.length <= 2) return;
    setLines(lines.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isBalanced) {
      setError(`Journal entry is unbalanced. Total Debit (${totalDebit}) != Total Credit (${totalCredit}).`);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await accountingService.createJournalEntry({
        date: txnDate,
        narration,
        lines: lines.map((l) => ({
          account_id: l.account_id,
          debit: Number(l.debit) || 0,
          credit: Number(l.credit) || 0,
          description: l.description,
        })),
      });
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to post journal entry.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-3xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <FileCheck className="h-5 w-5 text-indigo-400" /> Post Balanced Double-Entry Journal
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-slate-400 block mb-1 font-medium">Transaction Date</label>
              <input
                type="date"
                value={txnDate}
                onChange={(e) => setTxnDate(e.target.value)}
                required
                className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div className="col-span-2">
              <label className="text-slate-400 block mb-1 font-medium">Narration</label>
              <input
                type="text"
                value={narration}
                onChange={(e) => setNarration(e.target.value)}
                required
                placeholder="Business justification and narration..."
                className="w-full rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-white">Journal Line Items</span>
              <button
                type="button"
                onClick={handleAddLine}
                className="text-indigo-400 text-xs hover:underline flex items-center gap-1"
              >
                <Plus className="h-3 w-3" /> Add Line
              </button>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {lines.map((line, idx) => (
                <div key={idx} className="flex items-center gap-2 p-2 rounded-xl bg-slate-950 border border-slate-800">
                  <select
                    value={line.account_id}
                    onChange={(e) => handleLineChange(idx, "account_id", e.target.value)}
                    className="flex-1 rounded-lg border border-slate-800 bg-slate-900 p-1.5 text-white text-xs"
                  >
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.code} — {a.name} ({a.category})
                      </option>
                    ))}
                  </select>

                  <input
                    type="text"
                    placeholder="Line memo..."
                    value={line.description}
                    onChange={(e) => handleLineChange(idx, "description", e.target.value)}
                    className="w-40 rounded-lg border border-slate-800 bg-slate-900 p-1.5 text-white text-xs"
                  />

                  <div className="w-28">
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Debit"
                      value={line.debit === "0" ? "" : line.debit}
                      onChange={(e) => {
                        handleLineChange(idx, "debit", e.target.value);
                        if (Number(e.target.value) > 0) handleLineChange(idx, "credit", "0");
                      }}
                      className="w-full rounded-lg border border-slate-800 bg-slate-900 p-1.5 text-right text-emerald-400 font-mono text-xs"
                    />
                  </div>

                  <div className="w-28">
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Credit"
                      value={line.credit === "0" ? "" : line.credit}
                      onChange={(e) => {
                        handleLineChange(idx, "credit", e.target.value);
                        if (Number(e.target.value) > 0) handleLineChange(idx, "debit", "0");
                      }}
                      className="w-full rounded-lg border border-slate-800 bg-slate-900 p-1.5 text-right text-rose-400 font-mono text-xs"
                    />
                  </div>

                  {lines.length > 2 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveLine(idx)}
                      className="p-1 text-slate-500 hover:text-rose-400"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Debit / Credit Totals & Live Variance Indicator */}
            {(() => {
              const variance = Math.abs(totalDebit - totalCredit);
              return (
                <div className="space-y-2">
                  <div className={`flex flex-col sm:flex-row sm:items-center sm:justify-between p-3 rounded-xl border text-xs font-mono font-bold gap-2 ${
                    isBalanced
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                      : "bg-rose-500/10 border-rose-500/30 text-rose-400"
                  }`}>
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-md px-2.5 py-1 text-[11px] font-bold tracking-wide border ${
                          isBalanced
                            ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                            : "bg-rose-500/20 text-rose-300 border-rose-500/40"
                        }`}
                      >
                        {isBalanced ? "✓ BALANCED (Rs. 0.00 Variance)" : `⚠ UNBALANCED by Rs. ${variance.toLocaleString("en-PK", { minimumFractionDigits: 2 })}`}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-xs">
                      <span className="text-emerald-400 font-medium">Debit: {currency} {totalDebit.toLocaleString("en-PK", { minimumFractionDigits: 2 })}</span>
                      <span className="text-rose-400 font-medium">Credit: {currency} {totalCredit.toLocaleString("en-PK", { minimumFractionDigits: 2 })}</span>
                    </div>
                  </div>

                  {!isBalanced && (
                    <p className="text-[11px] text-amber-400/90 pl-1">
                      Double-entry rules require Total Debits to equal Total Credits. Posting is disabled until variance is Rs. 0.00.
                    </p>
                  )}
                </div>
              );
            })()}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !isBalanced}
              className={`rounded-xl px-5 py-2 text-xs font-semibold text-white shadow transition-all ${
                isBalanced
                  ? "bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/30"
                  : "bg-slate-800 cursor-not-allowed text-slate-500 opacity-60"
              }`}
            >
              {submitting ? "Posting..." : isBalanced ? "Post Journal Entry" : "Unbalanced — Cannot Post"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
