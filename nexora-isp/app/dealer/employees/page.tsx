"use client";

import { useCallback, useEffect, useState } from "react";
import { KeyRound, Loader2, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import EmployeeCashList from "@/components/dealers/EmployeeCashList";
import { ApiError } from "@/services/api-error";
import {
  dealerPortalService,
  type DealerEmployee,
  type DealerRights,
} from "@/services/dealer-portal.service";

const RIGHTS: { key: keyof DealerRights; label: string; hint: string }[] = [
  { key: "can_view_customers", label: "See customers", hint: "List, phone numbers, dues" },
  { key: "can_collect_payments", label: "Collect payments", hint: "Take cash / wallet payments" },
  { key: "can_recharge", label: "Recharge", hint: "Recharge prepaid connections" },
  { key: "can_request_customers", label: "New customers", hint: "Send new connections to the office" },
  { key: "can_view_collections", label: "Collections report", hint: "See what they collected" },
];

const DEFAULT_RIGHTS: DealerRights = {
  can_view_customers: true,
  can_collect_payments: true,
  can_recharge: false,
  can_request_customers: false,
  can_view_collections: false,
};

const inputClass =
  "mt-1 h-11 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

const EMPTY_FORM = { first_name: "", last_name: "", phone: "", email: "", password: "" };

function RightsChecklist({
  rights,
  onChange,
  disabled,
}: {
  rights: DealerRights;
  onChange: (key: keyof DealerRights, value: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {RIGHTS.map((right) => (
        <label
          key={right.key}
          className={`flex cursor-pointer items-start gap-2.5 rounded-lg border p-2.5 ${
            rights[right.key] ? "border-blue-500/50 bg-blue-500/10" : "border-[#263142]"
          } ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
        >
          <input
            type="checkbox"
            checked={rights[right.key]}
            disabled={disabled}
            onChange={(e) => onChange(right.key, e.target.checked)}
            className="mt-0.5 size-4 accent-blue-500"
          />
          <span>
            <span className="block text-sm font-medium text-slate-200">{right.label}</span>
            <span className="block text-[11px] text-slate-500">{right.hint}</span>
          </span>
        </label>
      ))}
    </div>
  );
}

export default function DealerEmployeesPage() {
  const me = useDealerMe();
  const [employees, setEmployees] = useState<DealerEmployee[]>([]);
  const [maxEmployees, setMaxEmployees] = useState(25);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [newRights, setNewRights] = useState<DealerRights>(DEFAULT_RIGHTS);
  const [saving, setSaving] = useState("");
  const [passwordFor, setPasswordFor] = useState<DealerEmployee | null>(null);
  const [newPassword, setNewPassword] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await dealerPortalService.getEmployees();
      setEmployees(data.results);
      setMaxEmployees(data.max_employees);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load your employees.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (me.is_dealer) void load();
  }, [me.is_dealer, load]);

  if (!me.is_dealer) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
        Only the dealer can manage employees.
      </div>
    );
  }

  const replace = (row: DealerEmployee) => setEmployees((rows) => rows.map((r) => (r.id === row.id ? row : r)));

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setSaving("new");
    try {
      const row = await dealerPortalService.createEmployee({ ...form, rights: newRights });
      setEmployees((rows) => [...rows, row]);
      toast.success(`${row.full_name} can now sign in with ${row.email}.`);
      setForm(EMPTY_FORM);
      setNewRights(DEFAULT_RIGHTS);
      setAdding(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to add the employee.");
    } finally {
      setSaving("");
    }
  }

  async function changeRight(employee: DealerEmployee, key: keyof DealerRights, value: boolean) {
    setSaving(employee.id);
    try {
      replace(await dealerPortalService.updateEmployee(employee.id, { rights: { [key]: value } }));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to save.");
    } finally {
      setSaving("");
    }
  }

  async function toggleActive(employee: DealerEmployee) {
    setSaving(employee.id);
    try {
      const row = await dealerPortalService.updateEmployee(employee.id, { is_active: !employee.is_active });
      replace(row);
      toast.success(row.is_active ? `${row.full_name} can sign in again.` : `${row.full_name} can no longer sign in.`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to save.");
    } finally {
      setSaving("");
    }
  }

  async function resetPassword(event: React.FormEvent) {
    event.preventDefault();
    if (!passwordFor) return;
    setSaving(`password-${passwordFor.id}`);
    try {
      await dealerPortalService.resetEmployeePassword(passwordFor.id, newPassword);
      toast.success(`New password set for ${passwordFor.full_name}.`);
      setPasswordFor(null);
      setNewPassword("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to change the password.");
    } finally {
      setSaving("");
    }
  }

  const canAdd = form.first_name.trim() && form.email.trim() && form.password.length >= 8 && saving !== "new";

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Employees</h1>
          <p className="text-sm text-slate-400">
            Give your collectors and counter staff their own login, and choose what each one can do.
          </p>
        </div>
        {!adding && employees.length < maxEmployees && (
          <button
            onClick={() => setAdding(true)}
            className="flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500"
          >
            <UserPlus className="h-4 w-4" /> Add Employee
          </button>
        )}
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

      {adding && (
        <form onSubmit={create} className="mb-5 rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
          <h2 className="text-sm font-semibold text-white">New employee</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="text-xs text-slate-400">
              First name *
              <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} className={inputClass} />
            </label>
            <label className="text-xs text-slate-400">
              Last name
              <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} className={inputClass} />
            </label>
            <label className="text-xs text-slate-400">
              Mobile
              <input inputMode="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="03001234567" className={inputClass} />
            </label>
            <label className="text-xs text-slate-400">
              Login email *
              <input type="email" autoComplete="off" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                className={inputClass} />
            </label>
            <label className="text-xs text-slate-400 sm:col-span-2">
              Password * (at least 8 characters)
              <input type="password" autoComplete="new-password" value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} className={inputClass} />
            </label>
          </div>
          <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wider text-slate-500">What can they do?</p>
          <RightsChecklist rights={newRights} onChange={(key, value) => setNewRights({ ...newRights, [key]: value })} />
          <p className="mt-3 text-[11px] text-slate-500">
            They sign in on the same login page with your ISP code and this email. They only ever see your customers.
          </p>
          <div className="mt-4 flex gap-2">
            <button type="button" onClick={() => setAdding(false)}
              className="h-11 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300 sm:flex-none sm:px-5">
              Cancel
            </button>
            <button type="submit" disabled={!canAdd}
              className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500 sm:flex-none sm:px-5">
              {saving === "new" ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />} Add Employee
            </button>
          </div>
        </form>
      )}

      <div className="mb-4">
        <EmployeeCashList
          load={dealerPortalService.getTeamCash}
          receive={dealerPortalService.receiveEmployeeCash}
          receiverLabel="Cash received"
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-blue-500" /></div>
      ) : employees.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">
          <Users className="mx-auto mb-2 h-6 w-6 text-slate-600" />
          No employees yet.
        </div>
      ) : (
        <ul className="space-y-3">
          {employees.map((employee) => (
            <li key={employee.id} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold text-white">
                    {employee.full_name}
                    {!employee.is_active && <span className="ml-2 text-xs font-normal text-red-400">Login off</span>}
                  </p>
                  <p className="text-xs text-slate-500">
                    {employee.email}{employee.phone ? ` · ${employee.phone}` : ""}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => { setPasswordFor(employee); setNewPassword(""); }}
                    className="flex h-9 items-center gap-1.5 rounded-lg border border-[#263142] px-3 text-xs text-slate-300 hover:bg-[#121821]"
                  >
                    <KeyRound className="h-3.5 w-3.5" /> Password
                  </button>
                  <button
                    onClick={() => void toggleActive(employee)}
                    disabled={saving === employee.id}
                    className={`h-9 rounded-lg border px-3 text-xs font-semibold disabled:opacity-50 ${
                      employee.is_active
                        ? "border-red-500/40 text-red-400 hover:bg-red-500/10"
                        : "border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
                    }`}
                  >
                    {employee.is_active ? "Turn off login" : "Turn on login"}
                  </button>
                </div>
              </div>
              <div className="mt-3">
                <RightsChecklist
                  rights={employee.rights}
                  disabled={saving === employee.id}
                  onChange={(key, value) => void changeRight(employee, key, value)}
                />
              </div>
            </li>
          ))}
        </ul>
      )}

      {passwordFor && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center" onClick={() => setPasswordFor(null)}>
          <form onSubmit={resetPassword} onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl">
            <h3 className="text-base font-bold text-white">New password for {passwordFor.full_name}</h3>
            <p className="mt-1 text-xs text-slate-400">Their old password stops working. Tell them the new one yourself.</p>
            <input type="password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
              placeholder="At least 8 characters" className={inputClass} />
            <div className="mt-4 flex gap-2">
              <button type="button" onClick={() => setPasswordFor(null)}
                className="h-11 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">Cancel</button>
              <button type="submit" disabled={newPassword.length < 8 || saving.startsWith("password-")}
                className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-500">
                {saving.startsWith("password-") && <Loader2 className="h-4 w-4 animate-spin" />} Save Password
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
