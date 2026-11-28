"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, KeyRound, Loader2, LogIn, Pencil, UserPlus, Users, X } from "lucide-react";
import { toast } from "sonner";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import EmployeeCashList from "@/components/dealers/EmployeeCashList";
import { ApiError } from "@/services/api-error";
import {
  DEALER_RIGHT_GROUPS,
  DEFAULT_EMPLOYEE_RIGHTS,
  dealerPortalService,
  type DealerEmployee,
  type DealerRightGroup,
  type DealerRights,
} from "@/services/dealer-portal.service";
import { pushJumpSession } from "@/services/jump-session";

const inputClass =
  "mt-1 h-11 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

const EMPTY_FORM = { first_name: "", last_name: "", phone: "", email: "", password: "" };

function initialRightsForActor(meRights: DealerRights, isDealer: boolean): DealerRights {
  if (isDealer) return { ...DEFAULT_EMPLOYEE_RIGHTS };
  const result = { ...DEFAULT_EMPLOYEE_RIGHTS };
  (Object.keys(result) as (keyof DealerRights)[]).forEach((key) => {
    if (!meRights[key]) result[key] = false;
  });
  return result;
}

function GroupedRightsChecklist({
  groups,
  rights,
  onChange,
  onChangeGroup,
  actorRights,
  isDealer,
  disabled,
}: {
  groups: DealerRightGroup[];
  rights: DealerRights;
  onChange: (key: keyof DealerRights, value: boolean) => void;
  onChangeGroup: (keys: (keyof DealerRights)[], value: boolean) => void;
  actorRights: DealerRights;
  isDealer: boolean;
  disabled?: boolean;
}) {
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(groups.map((g, idx) => [g.key, idx === 0])),
  );

  const toggleOpen = (key: string) => {
    setOpenGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-2.5">
      {groups.map((group) => {
        const isOpen = !!openGroups[group.key];
        const total = group.rights.length;
        const checkedCount = group.rights.filter((r) => rights[r.key]).length;
        const toggleableKeys = group.rights
          .filter((r) => isDealer || actorRights[r.key] || rights[r.key])
          .map((r) => r.key);
        const canGrantKeys = group.rights
          .filter((r) => isDealer || actorRights[r.key])
          .map((r) => r.key);
        const allAllowedChecked = canGrantKeys.length > 0 && canGrantKeys.every((k) => rights[k]);

        return (
          <div key={group.key} className="overflow-hidden rounded-xl border border-[#263142] bg-[#070A0F]">
            <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2.5">
              <button
                type="button"
                onClick={() => toggleOpen(group.key)}
                className="flex min-w-0 flex-1 items-center gap-2 text-left"
              >
                {isOpen ? (
                  <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
                ) : (
                  <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
                )}
                <span className="text-sm font-semibold text-white">{group.label}</span>
                <span className="rounded-full border border-[#263142] bg-[#0D1117] px-2 py-0.5 text-[11px] font-medium text-slate-400">
                  {checkedCount}/{total}
                </span>
              </button>
              <button
                type="button"
                disabled={disabled || (allAllowedChecked ? toggleableKeys.length === 0 : canGrantKeys.length === 0)}
                onClick={() => {
                  const targetValue = !allAllowedChecked;
                  const keys = targetValue ? canGrantKeys : toggleableKeys;
                  onChangeGroup(keys, targetValue);
                }}
                className="min-h-[32px] rounded-md border border-[#263142] px-2.5 py-1 text-xs font-medium text-blue-400 hover:bg-[#121821] disabled:cursor-not-allowed disabled:opacity-40"
              >
                {allAllowedChecked ? "Clear group" : "Select all in group"}
              </button>
            </div>
            {isOpen && (
              <div className="grid grid-cols-1 gap-2 border-t border-[#1C2431] p-3 sm:grid-cols-2">
                {group.rights.map((right) => {
                  const actorLacks = !isDealer && !actorRights[right.key];
                  const itemDisabled = disabled || (actorLacks && !rights[right.key]);
                  return (
                    <label
                      key={right.key}
                      className={`flex min-h-[44px] cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 ${
                        rights[right.key]
                          ? "border-blue-500/50 bg-blue-500/10"
                          : "border-[#1C2431] bg-[#0D1117]"
                      } ${itemDisabled ? "cursor-not-allowed opacity-50" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={rights[right.key]}
                        disabled={itemDisabled}
                        onChange={(e) => onChange(right.key, e.target.checked)}
                        className="size-4 shrink-0 accent-blue-500"
                      />
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-slate-200">{right.label}</span>
                        {actorLacks && (
                          <span className="block text-[10px] text-slate-500">Not in your rights</span>
                        )}
                      </span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function DealerEmployeesPage() {
  const me = useDealerMe();
  const canManage = me.is_dealer || me.rights.can_manage_employees;
  const groups = me.right_groups ?? DEALER_RIGHT_GROUPS;

  const [employees, setEmployees] = useState<DealerEmployee[]>([]);
  const [rightGroups, setRightGroups] = useState<DealerRightGroup[]>(groups);
  const [maxEmployees, setMaxEmployees] = useState(25);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [newRights, setNewRights] = useState<DealerRights>(() =>
    initialRightsForActor(me.rights, me.is_dealer),
  );
  const [editing, setEditing] = useState<DealerEmployee | null>(null);
  const [editForm, setEditForm] = useState({ first_name: "", last_name: "", phone: "" });
  const [editRights, setEditRights] = useState<DealerRights>(DEFAULT_EMPLOYEE_RIGHTS);
  const [saving, setSaving] = useState("");
  const [passwordFor, setPasswordFor] = useState<DealerEmployee | null>(null);
  const [newPassword, setNewPassword] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await dealerPortalService.getEmployees();
      setEmployees(data.results);
      setMaxEmployees(data.max_employees);
      if (data.right_groups?.length) {
        setRightGroups(data.right_groups);
      }
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load your employees.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (canManage) void load();
  }, [canManage, load]);

  if (!canManage) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
        You do not have permission to manage employees.
      </div>
    );
  }

  const replace = (row: DealerEmployee) => setEmployees((rows) => rows.map((r) => (r.id === row.id ? row : r)));

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setSaving("new");
    try {
      const payloadRights: Partial<DealerRights> = {};
      (Object.keys(newRights) as (keyof DealerRights)[]).forEach((key) => {
        if (me.is_dealer || me.rights[key]) {
          payloadRights[key] = newRights[key];
        }
      });
      const row = await dealerPortalService.createEmployee({ ...form, rights: payloadRights });
      setEmployees((rows) => [...rows, row]);
      toast.success(`${row.full_name} can now sign in with ${row.email}.`);
      setForm(EMPTY_FORM);
      setNewRights(initialRightsForActor(me.rights, me.is_dealer));
      setAdding(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to add the employee.");
    } finally {
      setSaving("");
    }
  }

  function openEdit(employee: DealerEmployee) {
    setEditing(employee);
    setEditForm({
      first_name: employee.first_name,
      last_name: employee.last_name,
      phone: employee.phone,
    });
    setEditRights({ ...DEFAULT_EMPLOYEE_RIGHTS, ...employee.rights });
  }

  async function saveEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!editing) return;
    setSaving(`edit-${editing.id}`);
    try {
      const isSelf = !me.is_dealer && me.employee_id === editing.id;
      const changedRights: Partial<DealerRights> = {};
      if (!isSelf) {
        (Object.keys(editRights) as (keyof DealerRights)[]).forEach((key) => {
          if (editRights[key] !== editing.rights[key]) {
            changedRights[key] = editRights[key];
          }
        });
      }
      const row = await dealerPortalService.updateEmployee(editing.id, {
        first_name: editForm.first_name,
        last_name: editForm.last_name,
        phone: editForm.phone,
        ...(Object.keys(changedRights).length ? { rights: changedRights } : {}),
      });
      replace(row);
      toast.success(`Updated ${row.full_name}.`);
      setEditing(null);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to update employee.");
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

  async function handleJumpEmployee(employee: DealerEmployee) {
    setSaving(`jump-${employee.id}`);
    try {
      const res = await dealerPortalService.jumpIntoEmployee(employee.id);
      pushJumpSession(res, {
        returnTo: "/dealer/employees",
        viewerLabel: `Viewing as ${employee.full_name} (Employee)`,
      });
      window.location.href = "/dealer";
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to open employee portal.");
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
            onClick={() => {
              setNewRights(initialRightsForActor(me.rights, me.is_dealer));
              setAdding(true);
            }}
            className="flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500"
          >
            <UserPlus className="h-4 w-4" /> Add Employee
          </button>
        )}
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

      {adding && (
        <form onSubmit={create} className="mb-5 rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">New employee</h2>
            <button type="button" onClick={() => setAdding(false)} className="text-slate-400 hover:text-white" aria-label="Close">
              <X className="h-4 w-4" />
            </button>
          </div>
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
          <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Rights</p>
          <GroupedRightsChecklist
            groups={rightGroups}
            rights={newRights}
            actorRights={me.rights}
            isDealer={me.is_dealer}
            onChange={(key, value) => setNewRights((prev) => ({ ...prev, [key]: value }))}
            onChangeGroup={(keys, value) =>
              setNewRights((prev) => {
                const next = { ...prev };
                keys.forEach((k) => {
                  next[k] = value;
                });
                return next;
              })
            }
          />
          <p className="mt-3 text-[11px] text-slate-500">
            They sign in on the same login page with this email. They only ever see your dealer&apos;s customers.
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

      {me.is_dealer && (
        <div className="mb-4">
          <EmployeeCashList
            load={dealerPortalService.getTeamCash}
            receive={dealerPortalService.receiveEmployeeCash}
            receiverLabel="Cash received"
          />
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-blue-500" /></div>
      ) : employees.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">
          <Users className="mx-auto mb-2 h-6 w-6 text-slate-600" />
          No employees yet.
        </div>
      ) : (
        <ul className="space-y-3">
          {employees.map((employee) => {
            const isSelf = !me.is_dealer && me.employee_id === employee.id;
            const enabledCount = Object.values(employee.rights).filter(Boolean).length;
            return (
              <li key={employee.id} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold text-white">
                      {employee.full_name}
                      {isSelf && <span className="ml-2 text-xs font-normal text-blue-400">You</span>}
                      {!employee.is_active && <span className="ml-2 text-xs font-normal text-red-400">Login off</span>}
                      {!employee.rights.can_web_login && (
                        <span className="ml-2 text-xs font-normal text-amber-400">Web login off</span>
                      )}
                    </p>
                    <p className="text-xs text-slate-500">
                      {employee.email}{employee.phone ? ` · ${employee.phone}` : ""} · {enabledCount} rights
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {me.is_dealer && (
                      <button
                        type="button"
                        onClick={() => void handleJumpEmployee(employee)}
                        disabled={saving === `jump-${employee.id}` || !employee.is_active}
                        title={employee.is_active ? "Open this employee's portal" : "Turn on employee login first"}
                        className="flex h-9 items-center gap-1.5 rounded-lg border border-blue-500/40 bg-blue-600/15 px-3 text-xs font-medium text-blue-300 hover:bg-blue-600/25 disabled:cursor-not-allowed disabled:border-[#263142] disabled:bg-transparent disabled:text-slate-500"
                      >
                        {saving === `jump-${employee.id}` ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <LogIn className="h-3.5 w-3.5" />
                        )}
                        Jump
                      </button>
                    )}
                    <button
                      onClick={() => openEdit(employee)}
                      className="flex h-9 items-center gap-1.5 rounded-lg border border-[#263142] px-3 text-xs text-slate-200 hover:bg-[#121821]"
                    >
                      <Pencil className="h-3.5 w-3.5" /> Edit
                    </button>
                    <button
                      onClick={() => { setPasswordFor(employee); setNewPassword(""); }}
                      className="flex h-9 items-center gap-1.5 rounded-lg border border-[#263142] px-3 text-xs text-slate-300 hover:bg-[#121821]"
                    >
                      <KeyRound className="h-3.5 w-3.5" /> Password
                    </button>
                    <button
                      onClick={() => void toggleActive(employee)}
                      disabled={saving === employee.id || isSelf}
                      className={`h-9 rounded-lg border px-3 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-50 ${
                        employee.is_active
                          ? "border-red-500/40 text-red-400 hover:bg-red-500/10"
                          : "border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
                      }`}
                    >
                      {employee.is_active ? "Turn off login" : "Turn on login"}
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center" onClick={() => setEditing(null)}>
          <form
            onSubmit={saveEdit}
            onClick={(e) => e.stopPropagation()}
            className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">Edit {editing.full_name}</h3>
                <p className="text-xs text-slate-500">{editing.email}</p>
              </div>
              <button type="button" onClick={() => setEditing(null)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <label className="text-xs text-slate-400">
                First name *
                <input
                  value={editForm.first_name}
                  onChange={(e) => setEditForm((f) => ({ ...f, first_name: e.target.value }))}
                  className={inputClass}
                />
              </label>
              <label className="text-xs text-slate-400">
                Last name
                <input
                  value={editForm.last_name}
                  onChange={(e) => setEditForm((f) => ({ ...f, last_name: e.target.value }))}
                  className={inputClass}
                />
              </label>
              <label className="text-xs text-slate-400">
                Mobile
                <input
                  inputMode="tel"
                  value={editForm.phone}
                  onChange={(e) => setEditForm((f) => ({ ...f, phone: e.target.value }))}
                  className={inputClass}
                />
              </label>
            </div>
            <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Rights
              {!me.is_dealer && me.employee_id === editing.id && " (you cannot change your own rights)"}
            </p>
            <GroupedRightsChecklist
              groups={rightGroups}
              rights={editRights}
              actorRights={me.rights}
              isDealer={me.is_dealer}
              disabled={!me.is_dealer && me.employee_id === editing.id}
              onChange={(key, value) => setEditRights((prev) => ({ ...prev, [key]: value }))}
              onChangeGroup={(keys, value) =>
                setEditRights((prev) => {
                  const next = { ...prev };
                  keys.forEach((k) => {
                    next[k] = value;
                  });
                  return next;
                })
              }
            />
            <div className="mt-5 flex gap-2">
              <button type="button" onClick={() => setEditing(null)}
                className="h-11 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">Cancel</button>
              <button
                type="submit"
                disabled={!editForm.first_name.trim() || saving === `edit-${editing.id}`}
                className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500"
              >
                {saving === `edit-${editing.id}` && <Loader2 className="h-4 w-4 animate-spin" />} Save Changes
              </button>
            </div>
          </form>
        </div>
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
