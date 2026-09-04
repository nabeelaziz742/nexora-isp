"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Building2,
  Calendar,
  CheckCircle2,
  CircleDollarSign,
  Download,
  FileSpreadsheet,
  Filter,
  Layers,
  Plus,
  Receipt,
  RefreshCw,
  Search,
  TrendingDown,
  Wallet,
  X,
} from "lucide-react";

import { expensesService, type CreateExpensePayload, type ExpenseRecord } from "@/services/expenses.service";
import { type Account } from "@/services/accounting.service";
import Skeleton from "@/components/ui/Skeleton";

export default function ExpensesPage() {
  const [expenses, setExpenses] = useState<ExpenseRecord[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // New Expense Form State
  const [formData, setFormData] = useState<CreateExpensePayload>({
    expense_account_id: "",
    payment_account_id: "",
    amount: "",
    date: new Date().toISOString().split("T")[0],
    payee: "",
    category: "OPERATING",
    reference: "",
    description: "",
  });

  const loadData = async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    setRefreshing(true);
    try {
      const [expData, accData] = await Promise.all([
        expensesService.getExpenses({
          category: categoryFilter !== "ALL" ? categoryFilter : undefined,
          search: searchQuery || undefined,
        }),
        expensesService.getAccounts(),
      ]);
      setExpenses(expData || []);
      setAccounts(accData || []);
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err?.message || "Failed to load operational expenses.",
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [categoryFilter]);

  const expenseAccounts = useMemo(() => {
    return accounts.filter((a) => a.category === "EXPENSE" && a.is_active);
  }, [accounts]);

  const paymentAccounts = useMemo(() => {
    return accounts.filter((a) => a.category === "ASSET" && a.is_active);
  }, [accounts]);

  // Financial Metrics
  const metrics = useMemo(() => {
    const totalAmount = expenses.reduce((sum, e) => sum + parseFloat(e.amount || "0"), 0);
    const count = expenses.length;
    const avgExpense = count > 0 ? totalAmount / count : 0;
    return { totalAmount, count, avgExpense };
  }, [expenses]);

  const filteredExpenses = useMemo(() => {
    return expenses.filter((e) => {
      const matchSearch =
        !searchQuery ||
        e.expense_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.payee.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.reference.toLowerCase().includes(searchQuery.toLowerCase());
      return matchSearch;
    });
  }, [expenses, searchQuery]);

  const handleCreateExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.expense_account_id || !formData.payment_account_id || !formData.amount) {
      setNotification({ type: "error", message: "Please fill all mandatory fields." });
      return;
    }

    setSubmitting(true);
    try {
      await expensesService.createExpense(formData);
      setNotification({ type: "success", message: "Operational expense recorded and posted to GL successfully!" });
      setShowCreateModal(false);
      setFormData({
        expense_account_id: "",
        payment_account_id: "",
        amount: "",
        date: new Date().toISOString().split("T")[0],
        payee: "",
        category: "OPERATING",
        reference: "",
        description: "",
      });
      loadData(false);
    } catch (err: any) {
      setNotification({ type: "error", message: err?.message || "Failed to record expense." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">Operational Expenses</h1>
            <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/20">
              General Ledger Integrated
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Record, track, and audit operational ISP disbursements with automated double-entry GL journal posting.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData(false)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-500 transition"
          >
            <Plus className="h-4 w-4" />
            Record Expense
          </button>
        </div>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div
          className={`flex items-center justify-between rounded-lg border p-4 ${
            notification.type === "success"
              ? "border-emerald-500/30 bg-emerald-950/40 text-emerald-300"
              : "border-rose-500/30 bg-rose-950/40 text-rose-300"
          }`}
        >
          <div className="flex items-center gap-3">
            {notification.type === "success" ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />
            ) : (
              <AlertCircle className="h-5 w-5 text-rose-400" />
            )}
            <span className="text-sm font-medium">{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-slate-400 hover:text-slate-200">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Recorded</span>
            <div className="rounded-lg bg-rose-500/10 p-2 text-rose-400">
              <TrendingDown className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-100">
            PKR {metrics.totalAmount.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
          </p>
          <p className="mt-1 text-xs text-slate-500">Gross operational disbursements</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Voucher Count</span>
            <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
              <Receipt className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-100">{metrics.count}</p>
          <p className="mt-1 text-xs text-slate-500">Audited expense records</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Average Voucher</span>
            <div className="rounded-lg bg-amber-500/10 p-2 text-amber-400">
              <CircleDollarSign className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-100">
            PKR {metrics.avgExpense.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
          </p>
          <p className="mt-1 text-xs text-slate-500">Mean per voucher expense</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by voucher #, payee, or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 py-2 pl-9 pr-4 text-xs text-slate-100 placeholder-slate-400 focus:border-emerald-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none"
            >
              <option value="ALL">All Categories</option>
              <option value="OPERATING">Operating Expenses</option>
              <option value="BANDWIDTH">Bandwidth & Transit</option>
              <option value="MAINTENANCE">Fiber / Network Maintenance</option>
              <option value="FUEL">Fuel & Power</option>
              <option value="SALARY">Salaries & Compensation</option>
              <option value="OFFICE">Office & Rent</option>
              <option value="OTHER">Other / Misc</option>
            </select>
          </div>
        </div>
      </div>

      {/* Expenses Table */}
      <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm">
        {loading ? (
          <div className="p-8 space-y-4">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : filteredExpenses.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-center">
            <Receipt className="h-12 w-12 text-slate-600 mb-3" />
            <h3 className="text-base font-semibold text-slate-300">No Expenses Recorded</h3>
            <p className="mt-1 text-xs text-slate-500 max-w-sm">
              No operational disbursements match your filters. Click Record Expense above to add your first expense.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="border-b border-slate-800 bg-slate-950/60 font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-4 py-3.5">Voucher #</th>
                  <th className="px-4 py-3.5">Date</th>
                  <th className="px-4 py-3.5">Expense Head / Category</th>
                  <th className="px-4 py-3.5">Payment Account</th>
                  <th className="px-4 py-3.5">Payee</th>
                  <th className="px-4 py-3.5">Reference</th>
                  <th className="px-4 py-3.5 text-right">Amount (PKR)</th>
                  <th className="px-4 py-3.5">GL Entry</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredExpenses.map((exp) => (
                  <tr key={exp.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3.5 font-mono font-medium text-slate-100">{exp.expense_number}</td>
                    <td className="px-4 py-3.5 text-slate-400">{exp.date}</td>
                    <td className="px-4 py-3.5">
                      <div className="font-medium text-slate-200">
                        {exp.expense_account_name || "Operational Expense"}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        Code: {exp.expense_account_code || "5000"} • {exp.category || "General"}
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="font-medium text-slate-300">{exp.payment_account_name || "Cash on Hand"}</div>
                      <div className="text-[11px] text-slate-500">Code: {exp.payment_account_code || "1000"}</div>
                    </td>
                    <td className="px-4 py-3.5 text-slate-200">{exp.payee || "—"}</td>
                    <td className="px-4 py-3.5 text-slate-400 font-mono text-[11px]">{exp.reference || "—"}</td>
                    <td className="px-4 py-3.5 text-right font-mono font-semibold text-rose-400">
                      {parseFloat(exp.amount).toLocaleString("en-PK", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3.5">
                      {exp.journal_entry_number ? (
                        <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-mono text-emerald-400 border border-emerald-500/20">
                          {exp.journal_entry_number}
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Record Expense Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2">
                <Receipt className="h-5 w-5 text-emerald-400" />
                <h3 className="text-base font-semibold text-slate-100">Record Operational Expense</h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateExpense} className="mt-5 space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300">Expense Account / Head *</label>
                  <select
                    required
                    value={formData.expense_account_id}
                    onChange={(e) => setFormData({ ...formData, expense_account_id: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="">Select Expense Head</option>
                    {expenseAccounts.map((acc) => (
                      <option key={acc.id} value={acc.id}>
                        {acc.code} - {acc.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300">Paid From Account *</label>
                  <select
                    required
                    value={formData.payment_account_id}
                    onChange={(e) => setFormData({ ...formData, payment_account_id: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="">Select Asset/Bank</option>
                    {paymentAccounts.map((acc) => (
                      <option key={acc.id} value={acc.id}>
                        {acc.code} - {acc.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300">Amount (PKR) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    placeholder="e.g. 15000"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300">Date *</label>
                  <input
                    type="date"
                    required
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300">Payee / Vendor</label>
                  <input
                    type="text"
                    placeholder="e.g. PTCL / Fuel Pump / Landlord"
                    value={formData.payee}
                    onChange={(e) => setFormData({ ...formData, payee: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300">Invoice / Slip Reference</label>
                  <input
                    type="text"
                    placeholder="e.g. SLIP-8871"
                    value={formData.reference}
                    onChange={(e) => setFormData({ ...formData, reference: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">Description / Purpose</label>
                <textarea
                  rows={2}
                  placeholder="Enter details of the operational expense..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {submitting && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                  Confirm & Post to GL
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
