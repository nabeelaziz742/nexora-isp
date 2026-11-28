"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, MessageSquareWarning, Plus, X } from "lucide-react";
import { toast } from "sonner";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import {
  dealerPortalService,
  type DealerComplaintCustomerOption,
  type DealerComplaintRow,
} from "@/services/dealer-portal.service";

const inputClass =
  "mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070B12] px-3 text-sm text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none";

function statusBadge(status: string) {
  if (status === "RESOLVED" || status === "CLOSED" || status === "CUSTOMER_CONFIRMED") {
    return "bg-emerald-500/15 text-emerald-400";
  }
  if (status === "CANCELLED") {
    return "bg-slate-500/15 text-slate-400";
  }
  if (status === "ESCALATED") {
    return "bg-red-500/15 text-red-400";
  }
  return "bg-amber-500/15 text-amber-400";
}

export default function DealerComplaintsPage() {
  const me = useDealerMe();
  const allowed = me.is_dealer || me.rights.can_manage_complaints;

  const [rows, setRows] = useState<DealerComplaintRow[]>([]);
  const [customers, setCustomers] = useState<DealerComplaintCustomerOption[]>([]);
  const [categories, setCategories] = useState<{ value: string; label: string }[]>([]);
  const [priorities, setPriorities] = useState<{ value: string; label: string }[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [openModal, setOpenModal] = useState(false);
  const [selectedServiceId, setSelectedServiceId] = useState("");
  const [category, setCategory] = useState("CONNECTIVITY");
  const [priority, setPriority] = useState("MEDIUM");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async (filter: string) => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await dealerPortalService.getComplaints(filter);
      setRows(res.results);
      setCustomers(res.customers);
      setCategories(res.categories);
      setPriorities(res.priorities);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load complaints.");
    } finally {
      setLoading(false);
    }
  }, [allowed]);

  useEffect(() => {
    void load(statusFilter);
  }, [load, statusFilter]);

  function openNewModal() {
    const first = customers[0];
    setSelectedServiceId(first ? first.service_id : "");
    setCategory(categories[0]?.value ?? "CONNECTIVITY");
    setPriority("MEDIUM");
    setSubject("");
    setDescription("");
    setOpenModal(true);
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    const chosen = customers.find((c) => c.service_id === selectedServiceId);
    if (!chosen) {
      toast.error("Select a customer first.");
      return;
    }
    if (!subject.trim() || !description.trim()) {
      toast.error("Subject and details are required.");
      return;
    }
    setSaving(true);
    try {
      await dealerPortalService.createComplaint({
        customer_id: chosen.customer_id,
        service_account_id: chosen.service_id,
        category,
        priority,
        subject: subject.trim(),
        description: description.trim(),
      });
      toast.success("Complaint sent to the ISP support team.");
      setOpenModal(false);
      void load(statusFilter);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not log complaint.");
    } finally {
      setSaving(false);
    }
  }

  if (!allowed) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
        You do not have permission to view or log complaints.
      </div>
    );
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Complaints</h1>
          <p className="text-sm text-slate-400">
            Log customer issues for the ISP support desk and track their status.
          </p>
        </div>
        <button
          type="button"
          onClick={openNewModal}
          disabled={customers.length === 0}
          className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-600"
        >
          <Plus className="h-4 w-4" /> New Complaint
        </button>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {[
          { value: "", label: "All" },
          { value: "OPEN", label: "Open" },
          { value: "IN_PROGRESS", label: "In Progress" },
          { value: "RESOLVED", label: "Resolved" },
        ].map((chip) => (
          <button
            key={chip.label}
            type="button"
            onClick={() => setStatusFilter(chip.value)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
              statusFilter === chip.value
                ? "bg-blue-600 text-white"
                : "border border-[#1C2431] bg-[#0D1117] text-slate-400 hover:text-white"
            }`}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
        </div>
      ) : rows.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">
          <MessageSquareWarning className="mx-auto mb-2 h-6 w-6 text-slate-600" />
          No complaints found.
        </div>
      ) : (
        <ul className="space-y-2.5">
          {rows.map((row) => (
            <li key={row.id} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-slate-500">{row.complaint_number}</span>
                    <span className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${statusBadge(row.status)}`}>
                      {row.status_label}
                    </span>
                    <span className="rounded bg-[#111927] px-1.5 py-0.5 text-[11px] text-slate-400">
                      {row.category_label} · {row.priority_label}
                    </span>
                  </div>
                  <p className="mt-1.5 text-sm font-semibold text-white">{row.subject}</p>
                  <p className="mt-0.5 text-xs text-slate-400">
                    {row.customer_name} · {row.service_number || row.customer_phone}
                  </p>
                </div>
                <span className="text-xs text-slate-500">
                  {new Date(row.created_at).toLocaleDateString("en-GB", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  })}
                </span>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-xs text-slate-300">{row.description}</p>
              {row.resolution_summary && (
                <div className="mt-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-300">
                  Resolution: {row.resolution_summary}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {openModal && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center"
          onClick={() => !saving && setOpenModal(false)}
        >
          <form
            onSubmit={handleCreate}
            onClick={(e) => e.stopPropagation()}
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">Log customer complaint</h2>
              <button
                type="button"
                onClick={() => setOpenModal(false)}
                className="text-slate-400 hover:text-white"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <label className="mt-4 block text-xs text-slate-400">
              Customer *
              <select
                value={selectedServiceId}
                onChange={(e) => setSelectedServiceId(e.target.value)}
                className={inputClass}
              >
                {customers.map((c) => (
                  <option key={c.service_id} value={c.service_id}>
                    {c.customer_name} · {c.service_number} ({c.phone})
                  </option>
                ))}
              </select>
            </label>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-slate-400">
                Category
                <select value={category} onChange={(e) => setCategory(e.target.value)} className={inputClass}>
                  {categories.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-slate-400">
                Priority
                <select value={priority} onChange={(e) => setPriority(e.target.value)} className={inputClass}>
                  {priorities.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="mt-3 block text-xs text-slate-400">
              Subject *
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Red light blinking on ONU"
                className={inputClass}
              />
            </label>
            <label className="mt-3 block text-xs text-slate-400">
              Problem details *
              <textarea
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the issue and customer availability"
                className="mt-1 w-full rounded-lg border border-[#263142] bg-[#070B12] p-2.5 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </label>
            <div className="mt-5 flex gap-2">
              <button
                type="button"
                onClick={() => setOpenModal(false)}
                disabled={saving}
                className="h-10 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving || !subject.trim() || !description.trim()}
                className="flex h-10 flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-600"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                Submit Complaint
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
