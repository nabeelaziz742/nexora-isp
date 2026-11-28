"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, MessageSquareText, Pencil, Plus, Power, X } from "lucide-react";
import { toast } from "sonner";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerSmsTemplate } from "@/services/dealer-portal.service";

const inputClass =
  "mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070B12] px-3 text-sm text-white focus:border-blue-500 focus:outline-none";

const PLACEHOLDERS = ["{name}", "{phone}", "{package}", "{amount}", "{expiry}", "{due}"];

export default function DealerSmsTemplatesPage() {
  const me = useDealerMe();
  const allowed = me.is_dealer || me.rights.can_manage_sms_templates;

  const [rows, setRows] = useState<DealerSmsTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<DealerSmsTemplate | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setRows((await dealerPortalService.getSmsTemplates()).results);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load SMS templates.");
    } finally {
      setLoading(false);
    }
  }, [allowed]);

  useEffect(() => {
    void load();
  }, [load]);

  function openAdd() {
    setEditing(null);
    setName("");
    setBody("");
    setModalOpen(true);
  }

  function openEdit(tpl: DealerSmsTemplate) {
    setEditing(tpl);
    setName(tpl.name);
    setBody(tpl.body);
    setModalOpen(true);
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim() || !body.trim()) return;
    setSaving(true);
    try {
      if (editing) {
        await dealerPortalService.updateSmsTemplate(editing.id, { name: name.trim(), body: body.trim() });
        toast.success("Template updated.");
      } else {
        await dealerPortalService.createSmsTemplate({ name: name.trim(), body: body.trim() });
        toast.success("Template created.");
      }
      setModalOpen(false);
      void load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save template.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus(tpl: DealerSmsTemplate) {
    try {
      await dealerPortalService.updateSmsTemplate(tpl.id, { is_active: !tpl.is_active });
      toast.success(tpl.is_active ? "Template deactivated." : "Template activated.");
      void load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update status.");
    }
  }

  if (!allowed) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
        You do not have permission to manage SMS templates.
      </div>
    );
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">SMS Templates</h1>
          <p className="text-sm text-slate-400">Reusable message templates for payment reminders and notices.</p>
        </div>
        <button
          type="button"
          onClick={openAdd}
          className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 text-sm font-semibold text-white hover:bg-blue-500"
        >
          <Plus className="h-4 w-4" /> New Template
        </button>
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
          <MessageSquareText className="mx-auto mb-2 h-6 w-6 text-slate-600" />
          No templates yet. Create your first SMS template.
        </div>
      ) : (
        <ul className="space-y-2.5">
          {rows.map((tpl) => (
            <li key={tpl.id} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-white">{tpl.name}</p>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                        tpl.is_active ? "bg-emerald-500/15 text-emerald-400" : "bg-slate-500/15 text-slate-400"
                      }`}
                    >
                      {tpl.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  <p className="mt-1.5 whitespace-pre-wrap text-xs text-slate-300">{tpl.body}</p>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => openEdit(tpl)}
                    className="inline-flex h-8 items-center gap-1 rounded-lg border border-[#263142] bg-[#111927] px-2.5 text-xs text-slate-200 hover:bg-[#182235]"
                  >
                    <Pencil className="h-3.5 w-3.5" /> Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => void toggleStatus(tpl)}
                    className="inline-flex h-8 items-center gap-1 rounded-lg border border-[#263142] bg-[#111927] px-2.5 text-xs text-slate-300 hover:bg-[#182235]"
                  >
                    <Power className="h-3.5 w-3.5" /> {tpl.is_active ? "Disable" : "Enable"}
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {modalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center"
          onClick={() => !saving && setModalOpen(false)}
        >
          <form
            onSubmit={save}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">{editing ? "Edit SMS template" : "New SMS template"}</h2>
              <button type="button" onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <label className="mt-4 block text-xs text-slate-400">
              Template Name *
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Monthly Bill Reminder" className={inputClass} />
            </label>
            <label className="mt-3 block text-xs text-slate-400">
              Message Body *
              <textarea
                rows={4}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Dear {name}, your {package} bill of PKR {amount} is due on {expiry}."
                className="mt-1 w-full rounded-lg border border-[#263142] bg-[#070B12] p-2.5 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </label>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] text-slate-500">Insert:</span>
              {PLACEHOLDERS.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => setBody((prev) => `${prev}${prev && !prev.endsWith(" ") ? " " : ""}${tag}`)}
                  className="rounded border border-[#263142] bg-[#111927] px-2 py-0.5 font-mono text-[11px] text-blue-300 hover:bg-[#182235]"
                >
                  {tag}
                </button>
              ))}
            </div>
            <div className="mt-5 flex gap-2">
              <button type="button" onClick={() => setModalOpen(false)} disabled={saving} className="h-10 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving || !name.trim() || !body.trim()}
                className="flex h-10 flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-600"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                Save Template
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
