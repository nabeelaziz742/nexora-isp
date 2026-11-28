"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Ban, Loader2, Megaphone, Send, X } from "lucide-react";
import { toast } from "sonner";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import {
  dealerPortalService,
  type DealerComplaintCustomerOption,
  type DealerSmsLogRow,
  type DealerSmsTemplate,
} from "@/services/dealer-portal.service";

const inputClass =
  "mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070B12] px-3 text-sm text-white focus:border-blue-500 focus:outline-none";

function smsStatusClass(status: string) {
  if (status === "SENT") return "bg-emerald-500/15 text-emerald-400";
  if (status === "FAILED") return "bg-red-500/15 text-red-400";
  if (status === "CANCELLED") return "bg-slate-500/15 text-slate-400";
  return "bg-amber-500/15 text-amber-400";
}

export default function DealerSmsLogPage() {
  const me = useDealerMe();
  const canViewLog = me.is_dealer || me.rights.can_view_sms_log;
  const canSend = me.is_dealer || me.rights.can_send_sms;
  const canBroadcast = me.is_dealer || me.rights.can_broadcast_sms;
  const allowed = canViewLog || canSend || canBroadcast;

  const [banner, setBanner] = useState("");
  const [rows, setRows] = useState<DealerSmsLogRow[]>([]);
  const [templates, setTemplates] = useState<DealerSmsTemplate[]>([]);
  const [customers, setCustomers] = useState<DealerComplaintCustomerOption[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Send single modal
  const [sendOpen, setSendOpen] = useState(false);
  const [sendCustomerId, setSendCustomerId] = useState("");
  const [sendTemplateId, setSendTemplateId] = useState("");
  const [sendMessage, setSendMessage] = useState("");
  const [sending, setSending] = useState(false);

  // Broadcast modal
  const [broadcastOpen, setBroadcastOpen] = useState(false);
  const [audience, setAudience] = useState<"ALL" | "DUE" | "EXPIRING">("ALL");
  const [broadcastTemplateId, setBroadcastTemplateId] = useState("");
  const [broadcastMessage, setBroadcastMessage] = useState("");
  const [broadcasting, setBroadcasting] = useState(false);

  const load = useCallback(async () => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [opts, logRes] = await Promise.all([
        dealerPortalService.getSmsOptions(),
        canViewLog ? dealerPortalService.getSmsLog(statusFilter) : Promise.resolve(null),
      ]);
      setTemplates(opts.templates);
      setCustomers(opts.customers);
      setBanner(logRes ? logRes.banner : opts.banner);
      setRows(logRes ? logRes.results : []);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load SMS workspace.");
    } finally {
      setLoading(false);
    }
  }, [allowed, canViewLog, statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  function openSendModal() {
    setSendCustomerId(customers[0]?.customer_id ?? "");
    setSendTemplateId("");
    setSendMessage("");
    setSendOpen(true);
  }

  function openBroadcastModal() {
    setAudience("ALL");
    setBroadcastTemplateId("");
    setBroadcastMessage("");
    setBroadcastOpen(true);
  }

  async function handleSend(event: React.FormEvent) {
    event.preventDefault();
    if (!sendCustomerId) return;
    setSending(true);
    try {
      const res = await dealerPortalService.sendSms({
        customer_id: sendCustomerId,
        template_id: sendTemplateId || null,
        message: sendMessage.trim(),
      });
      toast.success(res.gateway_connected ? "SMS queued for delivery." : "SMS queued. Waiting for ISP gateway.");
      setSendOpen(false);
      void load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to queue SMS.");
    } finally {
      setSending(false);
    }
  }

  async function handleBroadcast(event: React.FormEvent) {
    event.preventDefault();
    setBroadcasting(true);
    try {
      const res = await dealerPortalService.broadcastSms({
        audience,
        template_id: broadcastTemplateId || null,
        message: broadcastMessage.trim(),
      });
      toast.success(`Queued SMS for ${res.queued} customer(s).`);
      setBroadcastOpen(false);
      void load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to queue broadcast.");
    } finally {
      setBroadcasting(false);
    }
  }

  async function handleCancel(queueId: string) {
    try {
      await dealerPortalService.cancelSms(queueId);
      toast.success("Pending SMS cancelled.");
      void load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not cancel SMS.");
    }
  }

  if (!allowed) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
        You do not have permission to send or view SMS.
      </div>
    );
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">SMS Log & Messaging</h1>
          <p className="text-sm text-slate-400">Send individual or broadcast SMS to your customers.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canSend && (
            <button
              type="button"
              onClick={openSendModal}
              disabled={customers.length === 0}
              className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-600"
            >
              <Send className="h-4 w-4" /> Send SMS
            </button>
          )}
          {canBroadcast && (
            <button
              type="button"
              onClick={openBroadcastModal}
              disabled={customers.length === 0}
              className="inline-flex h-10 items-center gap-1.5 rounded-lg border border-blue-500/40 bg-blue-600/15 px-3.5 text-sm font-semibold text-blue-300 hover:bg-blue-600/25 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Megaphone className="h-4 w-4" /> Broadcast
            </button>
          )}
        </div>
      </div>

      {banner && (
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2.5 text-sm text-amber-200">
          <AlertCircle className="h-4 w-4 shrink-0 text-amber-400" />
          <span>{banner}</span>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {canViewLog && (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            {[
              { value: "", label: "All" },
              { value: "PENDING", label: "Pending" },
              { value: "SENT", label: "Sent" },
              { value: "FAILED", label: "Failed" },
              { value: "CANCELLED", label: "Cancelled" },
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

          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
            </div>
          ) : rows.length === 0 ? (
            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">
              No SMS messages in this filter.
            </div>
          ) : (
            <ul className="divide-y divide-[#1C2431] rounded-xl border border-[#1C2431] bg-[#0D1117]">
              {rows.map((row) => (
                <li key={row.id} className="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-white">{row.customer_name}</span>
                      <span className="text-xs text-slate-500">{row.recipient}</span>
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${smsStatusClass(row.status)}`}>
                        {row.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-300">{row.message}</p>
                    <p className="mt-0.5 text-[11px] text-slate-500">
                      {row.template_name} · {new Date(row.created_at).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                  {row.can_cancel && (
                    <button
                      type="button"
                      onClick={() => void handleCancel(row.id)}
                      className="inline-flex h-8 shrink-0 items-center gap-1 rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 text-xs font-medium text-red-300 hover:bg-red-500/20"
                    >
                      <Ban className="h-3.5 w-3.5" /> Cancel
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {sendOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center"
          onClick={() => !sending && setSendOpen(false)}
        >
          <form
            onSubmit={handleSend}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">Send SMS</h2>
              <button type="button" onClick={() => setSendOpen(false)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <label className="mt-4 block text-xs text-slate-400">
              Customer *
              <select value={sendCustomerId} onChange={(e) => setSendCustomerId(e.target.value)} className={inputClass}>
                {customers.map((c) => (
                  <option key={c.service_id} value={c.customer_id}>
                    {c.customer_name} · {c.phone}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-3 block text-xs text-slate-400">
              Template (optional)
              <select
                value={sendTemplateId}
                onChange={(e) => {
                  const id = e.target.value;
                  setSendTemplateId(id);
                  const found = templates.find((t) => t.id === id);
                  if (found) setSendMessage(found.body);
                }}
                className={inputClass}
              >
                <option value="">Custom message</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-3 block text-xs text-slate-400">
              Message *
              <textarea
                rows={4}
                value={sendMessage}
                onChange={(e) => setSendMessage(e.target.value)}
                placeholder="Type message or pick a template above"
                className="mt-1 w-full rounded-lg border border-[#263142] bg-[#070B12] p-2.5 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </label>
            <div className="mt-5 flex gap-2">
              <button type="button" onClick={() => setSendOpen(false)} disabled={sending} className="h-10 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">
                Cancel
              </button>
              <button
                type="submit"
                disabled={sending || (!sendMessage.trim() && !sendTemplateId)}
                className="flex h-10 flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-600"
              >
                {sending && <Loader2 className="h-4 w-4 animate-spin" />}
                Queue SMS
              </button>
            </div>
          </form>
        </div>
      )}

      {broadcastOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center"
          onClick={() => !broadcasting && setBroadcastOpen(false)}
        >
          <form
            onSubmit={handleBroadcast}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg rounded-t-2xl border border-[#263142] bg-[#0D1117] p-5 sm:rounded-2xl"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">Broadcast SMS</h2>
              <button type="button" onClick={() => setBroadcastOpen(false)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <label className="mt-4 block text-xs text-slate-400">
              Audience
              <select value={audience} onChange={(e) => setAudience(e.target.value as "ALL" | "DUE" | "EXPIRING")} className={inputClass}>
                <option value="ALL">All my customers</option>
                <option value="DUE">Customers with due balance</option>
                <option value="EXPIRING">Expiring within 3 days</option>
              </select>
            </label>
            <label className="mt-3 block text-xs text-slate-400">
              Template (optional)
              <select
                value={broadcastTemplateId}
                onChange={(e) => {
                  const id = e.target.value;
                  setBroadcastTemplateId(id);
                  const found = templates.find((t) => t.id === id);
                  if (found) setBroadcastMessage(found.body);
                }}
                className={inputClass}
              >
                <option value="">Custom message</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-3 block text-xs text-slate-400">
              Message *
              <textarea
                rows={4}
                value={broadcastMessage}
                onChange={(e) => setBroadcastMessage(e.target.value)}
                placeholder="Supports {name}, {package}, {amount}, {expiry}, {due}"
                className="mt-1 w-full rounded-lg border border-[#263142] bg-[#070B12] p-2.5 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </label>
            <div className="mt-5 flex gap-2">
              <button type="button" onClick={() => setBroadcastOpen(false)} disabled={broadcasting} className="h-10 flex-1 rounded-lg border border-[#263142] text-sm text-slate-300">
                Cancel
              </button>
              <button
                type="submit"
                disabled={broadcasting || (!broadcastMessage.trim() && !broadcastTemplateId)}
                className="flex h-10 flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-600"
              >
                {broadcasting && <Loader2 className="h-4 w-4 animate-spin" />}
                Queue Broadcast
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
