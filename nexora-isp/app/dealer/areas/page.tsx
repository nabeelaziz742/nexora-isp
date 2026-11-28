"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, MapPin, Pencil, Plus, Power, X } from "lucide-react";
import { toast } from "sonner";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerArea } from "@/services/dealer-portal.service";

const inputClass =
  "mt-1 h-11 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

const EMPTY_FORM = { name: "", city: "", notes: "" };

export default function DealerAreasPage() {
  const me = useDealerMe();
  const canView = me.is_dealer || me.rights.can_view_areas || me.rights.can_manage_areas;
  const canManage = me.is_dealer || me.rights.can_manage_areas;

  const [areas, setAreas] = useState<DealerArea[]>([]);
  const [statusFilter, setStatusFilter] = useState<"" | "active" | "inactive">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<DealerArea | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [togglingId, setTogglingId] = useState("");

  const load = useCallback(async (filter: "" | "active" | "inactive") => {
    setLoading(true);
    try {
      const res = await dealerPortalService.getAreas(filter);
      setAreas(res.results);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load areas.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (canView) void load(statusFilter);
  }, [canView, statusFilter, load]);

  if (!canView) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
        You do not have permission to view areas.
      </div>
    );
  }

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setModalOpen(true);
  }

  function openEdit(area: DealerArea) {
    setEditing(area);
    setForm({ name: area.name, city: area.city, notes: area.notes });
    setModalOpen(true);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      if (editing) {
        const updated = await dealerPortalService.updateArea(editing.id, form);
        setAreas((rows) => rows.map((r) => (r.id === updated.id ? updated : r)));
        toast.success(`Updated area "${updated.name}".`);
      } else {
        const created = await dealerPortalService.createArea(form);
        setAreas((rows) => [...rows, created].sort((a, b) => a.name.localeCompare(b.name)));
        toast.success(`Added area "${created.name}".`);
      }
      setModalOpen(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to save area.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus(area: DealerArea) {
    setTogglingId(area.id);
    try {
      const updated = await dealerPortalService.toggleAreaStatus(area.id);
      setAreas((rows) => rows.map((r) => (r.id === updated.id ? updated : r)));
      toast.success(updated.is_active ? `"${updated.name}" activated.` : `"${updated.name}" deactivated.`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to update status.");
    } finally {
      setTogglingId("");
    }
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Areas</h1>
          <p className="text-sm text-slate-400">Your own coverage areas used in your customer forms.</p>
        </div>
        {canManage && (
          <button
            onClick={openCreate}
            className="flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500"
          >
            <Plus className="h-4 w-4" /> Add Area
          </button>
        )}
      </div>

      <div className="mb-4 flex gap-1.5">
        {[
          { value: "", label: "All" },
          { value: "active", label: "Active" },
          { value: "inactive", label: "Inactive" },
        ].map((tab) => (
          <button
            key={tab.value}
            onClick={() => setStatusFilter(tab.value as "" | "active" | "inactive")}
            className={`h-9 rounded-lg border px-3 text-xs font-medium ${
              statusFilter === tab.value
                ? "border-blue-600 bg-blue-600 text-white"
                : "border-[#263142] text-slate-300 hover:bg-[#121821]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-blue-500" /></div>
      ) : areas.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">
          <MapPin className="mx-auto mb-2 h-6 w-6 text-slate-600" />
          No areas yet.
        </div>
      ) : (
        <ul className="space-y-2.5">
          {areas.map((area) => (
            <li key={area.id} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-white">{area.name}</p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        area.is_active
                          ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                          : "border border-slate-600/40 bg-slate-700/20 text-slate-400"
                      }`}
                    >
                      {area.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  {area.city && <p className="mt-0.5 text-xs text-slate-400">{area.city}</p>}
                  {area.notes && <p className="mt-1 text-xs text-slate-500">{area.notes}</p>}
                </div>

                {canManage && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => openEdit(area)}
                      className="flex h-9 items-center gap-1.5 rounded-lg border border-[#263142] px-3 text-xs text-slate-300 hover:bg-[#121821]"
                    >
                      <Pencil className="h-3.5 w-3.5" /> Edit
                    </button>
                    <button
                      onClick={() => void toggleStatus(area)}
                      disabled={togglingId === area.id}
                      className={`flex h-9 items-center gap-1.5 rounded-lg border px-3 text-xs font-semibold disabled:opacity-50 ${
                        area.is_active
                          ? "border-red-500/40 text-red-400 hover:bg-red-500/10"
                          : "border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
                      }`}
                    >
                      <Power className="h-3.5 w-3.5" />
                      {area.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center" onClick={() => !saving && setModalOpen(false)}>
          <form
            onSubmit={submit}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">{editing ? "Edit area" : "Add area"}</h2>
              <button type="button" onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <label className="mt-4 block text-xs text-slate-400">
              Area name *
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Johar Town Block C"
                className={inputClass}
              />
            </label>
            <label className="mt-3 block text-xs text-slate-400">
              City
              <input
                value={form.city}
                onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
                placeholder="e.g. Lahore"
                className={inputClass}
              />
            </label>
            <label className="mt-3 block text-xs text-slate-400">
              Notes
              <textarea
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                rows={2}
                placeholder="Optional coverage details"
                className="mt-1 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </label>
            <div className="mt-5 flex gap-2">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                disabled={saving}
                className="h-11 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!form.name.trim() || saving}
                className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                {editing ? "Save Changes" : "Add Area"}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
