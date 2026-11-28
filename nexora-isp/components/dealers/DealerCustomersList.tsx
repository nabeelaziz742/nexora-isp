"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Ban,
  BookOpen,
  Download,
  Loader2,
  Pencil,
  RefreshCw,
  Search,
  UserCheck,
  Wallet,
  X,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import { canSeeCustomers, useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import {
  dealerPortalService,
  type DealerAssignOption,
  type DealerCustomerEditPayload,
  type DealerCustomerLedger,
  type DealerCustomerRow,
  type DealerPaymentMethod,
} from "@/services/dealer-portal.service";

const METHODS: { value: DealerPaymentMethod; label: string }[] = [
  { value: "CASH", label: "Cash" },
  { value: "MOBILE_WALLET", label: "JazzCash / Easypaisa" },
  { value: "BANK_TRANSFER", label: "Bank Transfer" },
];

const FILTERS = [
  { value: "", label: "All" },
  { value: "due", label: "Payment due" },
  { value: "expiring", label: "Expiring" },
] as const;

const pkr = (value: string | number) => `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

const inputClass =
  "mt-1 h-11 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

function statusLabel(row: DealerCustomerRow) {
  if (row.status === "ACTIVE") return { text: "Active", cls: "text-emerald-400" };
  if (row.status.startsWith("SUSPENDED")) return { text: "Suspended", cls: "text-red-400" };
  return { text: row.status.replaceAll("_", " ").toLowerCase(), cls: "text-amber-400" };
}

function expiryText(row: DealerCustomerRow) {
  if (row.billing_mode !== "PREPAID" || row.days_to_expiry === null) return null;
  if (row.days_to_expiry < 0) return { text: `Expired ${Math.abs(row.days_to_expiry)}d ago`, cls: "text-red-400" };
  if (row.days_to_expiry <= 3) return { text: `${row.days_to_expiry}d left`, cls: "text-amber-400" };
  return { text: `${row.days_to_expiry}d left`, cls: "text-slate-500" };
}

function localDateString(offsetDays = 0) {
  const dt = new Date();
  dt.setDate(dt.getDate() + offsetDays);
  const year = dt.getFullYear();
  const month = String(dt.getMonth() + 1).padStart(2, "0");
  const day = String(dt.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function saveBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

type Action = { kind: "collect" | "recharge"; row: DealerCustomerRow } | null;

export default function DealerCustomersList({
  onChanged,
  showExport = false,
}: {
  onChanged?: () => void;
  showExport?: boolean;
}) {
  const me = useDealerMe();
  const showCustomers = canSeeCustomers(me.rights);
  const canAssign = me.is_dealer || me.rights.can_manage_employees;
  const canEdit = me.is_dealer || me.rights.can_edit_customers;
  const canDeactivate = me.is_dealer || me.rights.can_deactivate_customers;
  const canLedger = me.is_dealer || me.rights.can_view_ledger;
  const canExport = me.is_dealer || me.rights.can_export_customers;
  const canChangePaymentDate = me.is_dealer || me.rights.can_change_payment_date;
  const todayStr = localDateString(0);
  const minPayDateStr = localDateString(-7);

  const [rows, setRows] = useState<DealerCustomerRow[]>([]);
  const [search, setSearch] = useState("");
  const [show, setShow] = useState<"" | "due" | "expiring">("");
  const [loading, setLoading] = useState(showCustomers);
  const [error, setError] = useState("");
  const [action, setAction] = useState<Action>(null);
  const [amount, setAmount] = useState("");
  const [months, setMonths] = useState(1);
  const [method, setMethod] = useState<DealerPaymentMethod>("CASH");
  const [reference, setReference] = useState("");
  const [paidAtDate, setPaidAtDate] = useState("");
  const [saving, setSaving] = useState(false);

  // Assignment
  const [employees, setEmployees] = useState<DealerAssignOption[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [assignEmployeeId, setAssignEmployeeId] = useState<string>("");
  const [assigning, setAssigning] = useState(false);

  // Edit contact
  const [editRow, setEditRow] = useState<DealerCustomerRow | null>(null);
  const [editForm, setEditForm] = useState<DealerCustomerEditPayload>({
    first_name: "",
    last_name: "",
    phone: "",
    alternate_phone: "",
    cnic: "",
    address_line: "",
    area: "",
  });
  const [editAreas, setEditAreas] = useState<{ id: string; name: string; city: string }[]>([]);
  const [editSaving, setEditSaving] = useState(false);

  // Deactivate
  const [deactivateRow, setDeactivateRow] = useState<DealerCustomerRow | null>(null);
  const [deactivateReason, setDeactivateReason] = useState("");
  const [deactivating, setDeactivating] = useState(false);

  // Ledger
  const [ledgerRow, setLedgerRow] = useState<DealerCustomerRow | null>(null);
  const [ledgerData, setLedgerData] = useState<DealerCustomerLedger | null>(null);
  const [ledgerLoading, setLedgerLoading] = useState(false);

  // Export
  const [exporting, setExporting] = useState<"" | "xlsx" | "pdf">("");

  const loadRows = useCallback(async (query: string, filter: typeof show) => {
    if (!showCustomers) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setRows((await dealerPortalService.getCustomers({ search: query, show: filter })).results);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load your customers.");
    } finally {
      setLoading(false);
    }
  }, [showCustomers]);

  useEffect(() => {
    const timer = setTimeout(() => void loadRows(search.trim(), show), 300);
    return () => clearTimeout(timer);
  }, [search, show, loadRows]);

  useEffect(() => {
    if (!canAssign) return;
    dealerPortalService
      .getAssignOptions()
      .then((res) => setEmployees(res.employees))
      .catch(() => setEmployees([]));
  }, [canAssign]);

  if (!showCustomers) return null;

  function open(kind: "collect" | "recharge", row: DealerCustomerRow) {
    setAction({ kind, row });
    setAmount(kind === "collect" ? (Number(row.outstanding) > 0 ? row.outstanding : row.monthly_price) : "");
    setMonths(1);
    setMethod("CASH");
    setReference("");
    setPaidAtDate(todayStr);
  }

  async function submit() {
    if (!action) return;
    setSaving(true);
    try {
      const paidAtPayload = canChangePaymentDate && paidAtDate && paidAtDate !== todayStr ? paidAtDate : undefined;
      if (action.kind === "collect") {
        const result = await dealerPortalService.collectPayment(action.row.service_id, {
          amount,
          payment_method: method,
          reference,
          ...(paidAtPayload ? { paid_at: paidAtPayload } : {}),
        });
        toast.success(
          `Received ${pkr(result.receipt.amount)} from ${action.row.customer_name}. Receipt ${result.receipt.payment_number}.`,
        );
      } else {
        const result = await dealerPortalService.recharge(action.row.service_id, {
          months,
          payment_method: method,
          reference,
          ...(paidAtPayload ? { paid_at: paidAtPayload } : {}),
        });
        toast.success(
          `${action.row.customer_name} recharged until ${new Date(`${result.new_expiry_date}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}.`,
        );
      }
      setAction(null);
      onChanged?.();
      void loadRows(search.trim(), show);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "That could not be saved. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  function toggleSelect(customerId: string) {
    setSelectedIds((prev) =>
      prev.includes(customerId) ? prev.filter((id) => id !== customerId) : [...prev, customerId],
    );
  }

  async function handleAssign() {
    if (!selectedIds.length) return;
    setAssigning(true);
    try {
      await dealerPortalService.assignCustomers(selectedIds, assignEmployeeId || null);
      toast.success(
        assignEmployeeId
          ? `Assigned ${selectedIds.length} customer(s).`
          : `Unassigned ${selectedIds.length} customer(s).`,
      );
      setSelectedIds([]);
      void loadRows(search.trim(), show);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to assign customers.");
    } finally {
      setAssigning(false);
    }
  }

  async function openEdit(row: DealerCustomerRow) {
    setEditRow(row);
    setEditForm({
      first_name: row.first_name,
      last_name: row.last_name,
      phone: row.phone,
      alternate_phone: row.alternate_phone,
      cnic: row.cnic,
      address_line: row.address_line,
      area: row.area,
    });
    try {
      const opts = await dealerPortalService.getCustomerEditOptions(row.customer_id);
      setEditForm({
        first_name: opts.customer.first_name,
        last_name: opts.customer.last_name ?? "",
        phone: opts.customer.phone,
        alternate_phone: opts.customer.alternate_phone ?? "",
        cnic: opts.customer.cnic ?? "",
        address_line: opts.customer.address_line,
        area: opts.customer.area ?? "",
      });
      setEditAreas(opts.areas);
    } catch {
      setEditAreas([]);
    }
  }

  async function saveEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!editRow) return;
    setEditSaving(true);
    try {
      await dealerPortalService.updateCustomer(editRow.customer_id, editForm);
      toast.success(`Updated ${editForm.first_name}.`);
      setEditRow(null);
      void loadRows(search.trim(), show);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to update customer.");
    } finally {
      setEditSaving(false);
    }
  }

  async function handleDeactivate(event: React.FormEvent) {
    event.preventDefault();
    if (!deactivateRow || !deactivateReason.trim()) return;
    setDeactivating(true);
    try {
      await dealerPortalService.deactivateCustomer(deactivateRow.customer_id, deactivateReason.trim());
      toast.success(`${deactivateRow.customer_name} deactivated.`);
      setDeactivateRow(null);
      setDeactivateReason("");
      onChanged?.();
      void loadRows(search.trim(), show);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to deactivate customer.");
    } finally {
      setDeactivating(false);
    }
  }

  async function openLedger(row: DealerCustomerRow) {
    setLedgerRow(row);
    setLedgerData(null);
    setLedgerLoading(true);
    try {
      setLedgerData(await dealerPortalService.getCustomerLedger(row.customer_id));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to load ledger.");
      setLedgerRow(null);
    } finally {
      setLedgerLoading(false);
    }
  }

  async function handleExport(fmt: "xlsx" | "pdf") {
    setExporting(fmt);
    try {
      const blob = await dealerPortalService.exportCustomers(fmt, { search: search.trim(), show });
      saveBlob(blob, `dealer_customers.${fmt}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to export customers.");
    } finally {
      setExporting("");
    }
  }

  const amountValid = action?.kind !== "collect" || (Number(amount) >= 1 && Number.isFinite(Number(amount)));
  const rechargeTotal = action?.kind === "recharge" ? Number(action.row.monthly_price) * months : 0;

  return (
    <>
      {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

      <div className="mb-3 flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, phone or ID"
            className="h-11 w-full rounded-lg border border-[#263142] bg-[#0D1117] pl-9 pr-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((filter) => (
            <button
              key={filter.value}
              onClick={() => setShow(filter.value)}
              className={`h-11 flex-1 rounded-lg border px-3 text-sm sm:flex-none ${
                show === filter.value ? "border-blue-600 bg-blue-600 font-semibold text-white" : "border-[#263142] text-slate-300 hover:bg-[#121821]"
              }`}
            >
              {filter.label}
            </button>
          ))}
          {showExport && canExport && (
            <>
              <button
                type="button"
                onClick={() => void handleExport("xlsx")}
                disabled={exporting !== ""}
                className="flex h-11 items-center gap-1.5 rounded-lg border border-[#263142] px-3 text-xs font-medium text-slate-200 hover:bg-[#121821] disabled:opacity-50"
              >
                {exporting === "xlsx" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                Excel
              </button>
              <button
                type="button"
                onClick={() => void handleExport("pdf")}
                disabled={exporting !== ""}
                className="flex h-11 items-center gap-1.5 rounded-lg border border-[#263142] px-3 text-xs font-medium text-slate-200 hover:bg-[#121821] disabled:opacity-50"
              >
                {exporting === "pdf" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                PDF
              </button>
            </>
          )}
          <button
            onClick={() => {
              onChanged?.();
              void loadRows(search.trim(), show);
            }}
            aria-label="Refresh"
            className="h-11 rounded-lg border border-[#263142] px-3 text-slate-300 hover:bg-[#121821]"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {canAssign && selectedIds.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl border border-blue-500/30 bg-blue-500/10 p-3">
          <span className="text-xs font-semibold text-blue-300">{selectedIds.length} selected</span>
          <select
            value={assignEmployeeId}
            onChange={(e) => setAssignEmployeeId(e.target.value)}
            className="h-9 rounded-lg border border-[#263142] bg-[#070A0F] px-2.5 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="">Unassigned</option>
            {employees.map((emp) => (
              <option key={emp.id} value={emp.id}>
                {emp.full_name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => void handleAssign()}
            disabled={assigning}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-blue-600 px-3 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {assigning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <UserCheck className="h-3.5 w-3.5" />}
            Assign
          </button>
          <button
            type="button"
            onClick={() => setSelectedIds([])}
            className="h-9 rounded-lg border border-[#263142] px-2.5 text-xs text-slate-300 hover:bg-[#121821]"
          >
            Clear
          </button>
        </div>
      )}

      {loading && rows.length === 0 ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-blue-500" /></div>
      ) : rows.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">No customers here.</div>
      ) : (
        <ul className="space-y-2">
          {rows.map((row) => {
            const st = statusLabel(row);
            const exp = expiryText(row);
            const due = Number(row.outstanding);
            const isSelected = selectedIds.includes(row.customer_id);
            const canSuspend = ["ACTIVE", "GRACE_PERIOD", "SUSPENSION_PENDING"].includes(row.status);
            return (
              <li key={row.service_id} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-3.5">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-2.5">
                    {canAssign && (
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(row.customer_id)}
                        aria-label={`Select ${row.customer_name}`}
                        className="mt-1 size-4 shrink-0 accent-blue-500"
                      />
                    )}
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-white">{row.customer_name}</p>
                      <p className="text-xs text-slate-500">
                        <a href={`tel:${row.phone}`} className="text-blue-400">{row.phone}</a> · {row.service_number}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        {row.package_name} · {row.billing_mode === "PREPAID" ? "Prepaid" : "Monthly"}
                        {row.area ? ` · ${row.area}` : ""}
                        {row.assigned_employee_name ? ` · Assigned: ${row.assigned_employee_name}` : ""}
                      </p>
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className={`text-xs font-semibold ${st.cls}`}>{st.text}</p>
                    {exp && <p className={`text-xs ${exp.cls}`}>{exp.text}</p>}
                    <p className={`mt-1 text-sm font-bold ${due > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                      {due > 0 ? `${pkr(due)} due` : "Paid up"}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 empty:hidden">
                  {me.rights.can_collect_payments && (
                    <button
                      onClick={() => open("collect", row)}
                      className="flex h-10 min-w-[110px] flex-1 items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-3 text-sm font-semibold text-white hover:bg-emerald-500"
                    >
                      <Wallet className="h-4 w-4" /> Collect
                    </button>
                  )}
                  {row.billing_mode === "PREPAID" && me.rights.can_recharge && (
                    <button
                      onClick={() => open("recharge", row)}
                      className="flex h-10 min-w-[110px] flex-1 items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 text-sm font-semibold text-white hover:bg-blue-500"
                    >
                      <Zap className="h-4 w-4" /> Recharge
                    </button>
                  )}
                  {canLedger && (
                    <button
                      onClick={() => void openLedger(row)}
                      className="flex h-10 items-center justify-center gap-1.5 rounded-lg border border-[#263142] px-3 text-xs font-medium text-slate-200 hover:bg-[#121821]"
                    >
                      <BookOpen className="h-3.5 w-3.5" /> Ledger
                    </button>
                  )}
                  {canEdit && (
                    <button
                      onClick={() => void openEdit(row)}
                      className="flex h-10 items-center justify-center gap-1.5 rounded-lg border border-[#263142] px-3 text-xs font-medium text-slate-200 hover:bg-[#121821]"
                    >
                      <Pencil className="h-3.5 w-3.5" /> Edit
                    </button>
                  )}
                  {canDeactivate && canSuspend && (
                    <button
                      onClick={() => {
                        setDeactivateRow(row);
                        setDeactivateReason("");
                      }}
                      className="flex h-10 items-center justify-center gap-1.5 rounded-lg border border-red-500/40 px-3 text-xs font-medium text-red-400 hover:bg-red-500/10"
                    >
                      <Ban className="h-3.5 w-3.5" /> Deactivate
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {action && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center" onClick={() => !saving && setAction(null)}>
          <div className="w-full max-w-md rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-base font-bold text-white">
              {action.kind === "collect" ? "Collect payment" : "Recharge connection"}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              {action.row.customer_name} · {action.row.service_number}
              {Number(action.row.outstanding) > 0 && ` · ${pkr(action.row.outstanding)} due`}
            </p>

            {action.kind === "collect" ? (
              <label className="mt-4 block text-xs text-slate-400">
                Amount received (PKR)
                <input type="number" min="1" inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} className={inputClass} />
              </label>
            ) : (
              <label className="mt-4 block text-xs text-slate-400">
                Months
                <select value={months} onChange={(e) => setMonths(Number(e.target.value))} className={inputClass}>
                  {[1, 2, 3, 6, 12].map((m) => <option key={m} value={m}>{m} month{m > 1 ? "s" : ""} · {pkr(Number(action.row.monthly_price) * m)}</option>)}
                </select>
              </label>
            )}

            <label className="mt-3 block text-xs text-slate-400">
              Received as
              <select value={method} onChange={(e) => setMethod(e.target.value as DealerPaymentMethod)} className={inputClass}>
                {METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </label>
            {method !== "CASH" && (
              <label className="mt-3 block text-xs text-slate-400">
                Transaction ID
                <input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Optional" className={inputClass} />
              </label>
            )}
            {canChangePaymentDate && (
              <label className="mt-3 block text-xs text-slate-400">
                Payment date (up to 7 days back)
                <input
                  type="date"
                  min={minPayDateStr}
                  max={todayStr}
                  value={paidAtDate}
                  onChange={(e) => setPaidAtDate(e.target.value)}
                  className={inputClass}
                />
              </label>
            )}

            {action.kind === "recharge" && (
              <p className="mt-3 text-sm text-slate-300">Collect <span className="font-bold text-white">{pkr(rechargeTotal)}</span> from the customer.</p>
            )}

            <div className="mt-5 flex gap-2">
              <button onClick={() => setAction(null)} disabled={saving} className="h-11 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">
                Cancel
              </button>
              <button
                onClick={() => void submit()}
                disabled={saving || !amountValid}
                className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-emerald-600 text-sm font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-500"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                {action.kind === "collect" ? `Confirm ${amount ? pkr(amount) : ""}` : "Confirm Recharge"}
              </button>
            </div>
          </div>
        </div>
      )}

      {editRow && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center" onClick={() => !editSaving && setEditRow(null)}>
          <form
            onSubmit={saveEdit}
            onClick={(e) => e.stopPropagation()}
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">Edit contact details</h2>
              <button type="button" onClick={() => setEditRow(null)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">{editRow.customer_number} · Package and billing cannot be changed here.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-slate-400">
                First name *
                <input value={editForm.first_name} onChange={(e) => setEditForm((f) => ({ ...f, first_name: e.target.value }))} className={inputClass} />
              </label>
              <label className="text-xs text-slate-400">
                Last name
                <input value={editForm.last_name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, last_name: e.target.value }))} className={inputClass} />
              </label>
              <label className="text-xs text-slate-400">
                Phone *
                <input inputMode="tel" value={editForm.phone} onChange={(e) => setEditForm((f) => ({ ...f, phone: e.target.value }))} className={inputClass} />
              </label>
              <label className="text-xs text-slate-400">
                Alternate phone
                <input inputMode="tel" value={editForm.alternate_phone ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, alternate_phone: e.target.value }))} className={inputClass} />
              </label>
              <label className="text-xs text-slate-400">
                CNIC
                <input value={editForm.cnic ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, cnic: e.target.value }))} className={inputClass} />
              </label>
              <label className="text-xs text-slate-400">
                Area
                <select value={editForm.area ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, area: e.target.value }))} className={inputClass}>
                  <option value="">No area</option>
                  {editForm.area && !editAreas.some((a) => a.name === editForm.area) && (
                    <option value={editForm.area}>{editForm.area}</option>
                  )}
                  {editAreas.map((area) => (
                    <option key={area.id} value={area.name}>
                      {area.name}{area.city ? ` (${area.city})` : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-slate-400 sm:col-span-2">
                Address *
                <input value={editForm.address_line} onChange={(e) => setEditForm((f) => ({ ...f, address_line: e.target.value }))} className={inputClass} />
              </label>
            </div>
            <div className="mt-5 flex gap-2">
              <button type="button" onClick={() => setEditRow(null)} disabled={editSaving} className="h-11 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">
                Cancel
              </button>
              <button
                type="submit"
                disabled={editSaving || !editForm.first_name.trim() || !editForm.phone.trim() || !editForm.address_line.trim()}
                className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500"
              >
                {editSaving && <Loader2 className="h-4 w-4 animate-spin" />} Save
              </button>
            </div>
          </form>
        </div>
      )}

      {deactivateRow && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center" onClick={() => !deactivating && setDeactivateRow(null)}>
          <form onSubmit={handleDeactivate} onClick={(e) => e.stopPropagation()} className="w-full max-w-md rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl">
            <h2 className="text-base font-bold text-white">Deactivate {deactivateRow.customer_name}?</h2>
            <p className="mt-1 text-xs text-slate-400">
              This suspends the connection while keeping all records and payment history. Only the ISP can reactivate it.
            </p>
            <label className="mt-4 block text-xs text-slate-400">
              Reason *
              <input
                value={deactivateReason}
                onChange={(e) => setDeactivateReason(e.target.value)}
                placeholder="e.g. Customer requested temporary disconnection"
                className={inputClass}
              />
            </label>
            <div className="mt-5 flex gap-2">
              <button type="button" onClick={() => setDeactivateRow(null)} disabled={deactivating} className="h-11 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">
                Cancel
              </button>
              <button
                type="submit"
                disabled={deactivating || !deactivateReason.trim()}
                className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-red-600 text-sm font-semibold text-white hover:bg-red-500 disabled:cursor-not-allowed disabled:bg-slate-500"
              >
                {deactivating && <Loader2 className="h-4 w-4 animate-spin" />} Deactivate
              </button>
            </div>
          </form>
        </div>
      )}

      {ledgerRow && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center" onClick={() => setLedgerRow(null)}>
          <div onClick={(e) => e.stopPropagation()} className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl">
            <div className="flex items-center justify-between gap-2">
              <div>
                <h2 className="text-base font-bold text-white">Ledger · {ledgerRow.customer_name}</h2>
                <p className="text-xs text-slate-500">
                  {ledgerRow.customer_number}
                  {ledgerData && ` · Current balance: ${pkr(ledgerData.current_balance)}`}
                </p>
              </div>
              <button type="button" onClick={() => setLedgerRow(null)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            {ledgerLoading ? (
              <div className="flex justify-center py-10"><Loader2 className="h-5 w-5 animate-spin text-blue-500" /></div>
            ) : !ledgerData || ledgerData.entries.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">No invoices or payments yet.</p>
            ) : (
              <div className="mt-4 overflow-x-auto rounded-lg border border-[#1C2431]">
                <table className="w-full min-w-[520px] text-left text-xs">
                  <thead className="bg-[#070A0F] text-[10px] uppercase tracking-wider text-slate-500">
                    <tr>
                      <th className="px-3 py-2">Date</th>
                      <th className="px-3 py-2">Type</th>
                      <th className="px-3 py-2">Details</th>
                      <th className="px-3 py-2 text-right">Amount</th>
                      <th className="px-3 py-2 text-right">Balance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1C2431]">
                    {ledgerData.entries.map((entry) => (
                      <tr key={entry.id} className={entry.is_reversed ? "opacity-50 line-through" : ""}>
                        <td className="whitespace-nowrap px-3 py-2 text-slate-400">{entry.date}</td>
                        <td className="px-3 py-2 font-medium text-slate-200">{entry.type === "INVOICE" ? "Invoice" : "Payment"}</td>
                        <td className="px-3 py-2 text-slate-300">
                          <span className="font-mono text-[11px] text-slate-400">{entry.reference}</span> · {entry.description}
                        </td>
                        <td className={`whitespace-nowrap px-3 py-2 text-right font-semibold ${entry.type === "INVOICE" ? "text-amber-400" : "text-emerald-400"}`}>
                          {entry.type === "INVOICE" ? `+${pkr(entry.debit)}` : `-${pkr(entry.credit)}`}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-right font-mono text-white">
                          {pkr(entry.running_balance)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
