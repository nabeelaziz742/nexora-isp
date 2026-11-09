"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Ban, CheckCircle2, Copy, Download, KeyRound, Loader2, Plus, Save } from "lucide-react";

import {
  ErrorBanner,
  StatusBadge,
  daysLeftLabel,
  formatDate,
  formatPKR,
  useSuperAdminErrorHandler,
} from "@/components/superadmin/ui";
import {
  activateISP,
  downloadSubscriptionReceipt,
  getISP,
  recordISPPayment,
  resetISPOwnerPassword,
  suspendISP,
  updateISPSubscription,
  type ISPDetail,
} from "@/services/onboarding.service";

const METHODS = [
  { value: "BANK_TRANSFER", label: "Bank Transfer" },
  { value: "MOBILE_WALLET", label: "JazzCash / Easypaisa" },
  { value: "CASH", label: "Cash" },
  { value: "OTHER", label: "Other" },
];

const inputClass =
  "h-10 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

function Info({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm text-slate-200">{value === null || value === undefined || value === "" ? "—" : value}</p>
    </div>
  );
}

export default function ISPDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [isp, setIsp] = useState<ISPDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const handleError = useSuperAdminErrorHandler(setError);

  const [fee, setFee] = useState("");
  const [paidUntil, setPaidUntil] = useState("");
  const [notes, setNotes] = useState("");
  const [payment, setPayment] = useState({ amount: "", months: 1, method: "BANK_TRANSFER", reference: "" });
  const [suspendReason, setSuspendReason] = useState("");
  const [showSuspend, setShowSuspend] = useState(false);
  const [ownerReset, setOwnerReset] = useState<{ email: string; temporary_password: string; organization_code: string } | null>(null);

  async function downloadReceipt(paymentId: string, receiptNumber: string) {
    setBusy(`receipt-${paymentId}`);
    setError("");
    try {
      await downloadSubscriptionReceipt(paymentId, `${receiptNumber || "receipt"}-${isp?.code ?? ""}.pdf`);
    } catch (err) {
      handleError(err, "Unable to download the receipt.");
    } finally {
      setBusy("");
    }
  }

  async function resetOwner() {
    if (!window.confirm("Set a new temporary password for this ISP's owner? Their current password stops working.")) return;
    setBusy("owner");
    setError("");
    try {
      setOwnerReset(await resetISPOwnerPassword(id));
    } catch (err) {
      handleError(err, "Unable to reset the owner's password.");
    } finally {
      setBusy("");
    }
  }

  const apply = useCallback((data: ISPDetail) => {
    setIsp(data);
    setFee(data.monthly_fee);
    setPaidUntil(data.paid_until ?? "");
    setNotes(data.notes);
    setPayment((current) => ({ ...current, amount: data.monthly_fee }));
  }, []);

  const load = useCallback(async () => {
    try {
      apply(await getISP(id));
      setError("");
    } catch (err) {
      handleError(err, "Unable to load this ISP.");
    } finally {
      setLoading(false);
    }
  }, [apply, handleError, id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(key: string, action: () => Promise<ISPDetail>, done: string) {
    setBusy(key);
    setError("");
    setNotice("");
    try {
      apply(await action());
      setNotice(done);
    } catch (err) {
      handleError(err, "That action could not be completed.");
    } finally {
      setBusy("");
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
      </div>
    );
  }
  if (!isp) return <ErrorBanner message={error || "ISP not found."} />;

  const canManage = isp.status !== "PENDING" && isp.status !== "REJECTED";
  const amountNumber = Number(payment.amount);
  const paymentValid = payment.amount !== "" && Number.isFinite(amountNumber) && amountNumber >= 0;

  return (
    <>
      <Link href="/superadmin/isps" className="mb-3 inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200">
        <ArrowLeft className="h-3.5 w-3.5" /> All ISPs
      </Link>

      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-white">{isp.name}</h1>
            <StatusBadge status={isp.status} />
          </div>
          <p className="mt-1 text-sm text-slate-400">{isp.code} · joined {formatDate(isp.joined_at)}</p>
        </div>
        {canManage && (
          isp.is_active ? (
            <button
              onClick={() => setShowSuspend(true)}
              className="flex h-10 items-center gap-2 rounded-lg bg-red-600 px-4 text-sm font-semibold text-white hover:bg-red-700"
            >
              <Ban className="h-4 w-4" /> Suspend ISP
            </button>
          ) : (
            <button
              onClick={() => void run("activate", () => activateISP(isp.id), "ISP activated. Its staff can sign in again.")}
              disabled={busy === "activate"}
              className="flex h-10 items-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
            >
              <CheckCircle2 className="h-4 w-4" /> Activate ISP
            </button>
          )
        )}
      </div>

      <ErrorBanner message={error} />
      {notice && (
        <div className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-400">{notice}</div>
      )}
      {!isp.is_active && isp.suspension_reason && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          {isp.suspension_kind === "EXPIRED" ? "Locked automatically: " : "Suspended: "}
          {isp.suspension_reason}
          {isp.suspended_at && ` (${formatDate(isp.suspended_at)})`}
          {isp.suspension_kind === "EXPIRED" && " Recording a payment below unlocks it."}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5 lg:col-span-1">
          <h2 className="mb-4 text-sm font-semibold text-white">Organization</h2>
          <div className="grid gap-4">
            <Info label="Owner" value={<>{isp.owner_name}<br /><span className="text-xs text-slate-500">{isp.owner_email}</span></>} />
            <Info label="City" value={isp.city} />
            <Info label="Phone" value={isp.phone} />
            <Info label="Email" value={isp.email} />
            <Info label="Address" value={isp.address} />
            {isp.registration && (
              <Info label="Registration" value={`${isp.registration.status} · ${formatPKR(isp.registration.amount_due)}`} />
            )}
          </div>
          {isp.owner_email && (
            <button
              onClick={() => void resetOwner()}
              disabled={busy === "owner"}
              className="mt-4 flex h-9 items-center gap-2 rounded-lg border border-[#263142] px-3 text-xs font-semibold text-slate-300 hover:bg-[#121821] disabled:opacity-60"
            >
              <KeyRound className="h-3.5 w-3.5" /> Reset Owner Password
            </button>
          )}
          {ownerReset && (
            <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs">
              <p className="text-emerald-400">Temporary password set. Share it privately; it is shown only now.</p>
              <pre className="mt-2 whitespace-pre-wrap text-slate-200">{`Organization code: ${ownerReset.organization_code}
Email: ${ownerReset.email}
Password: ${ownerReset.temporary_password}`}</pre>
              <button
                onClick={() => void navigator.clipboard.writeText(`Organization code: ${ownerReset.organization_code}
Email: ${ownerReset.email}
Password: ${ownerReset.temporary_password}`)}
                className="mt-2 flex items-center gap-1.5 text-blue-400 hover:underline"
              >
                <Copy className="h-3.5 w-3.5" /> Copy
              </button>
            </div>
          )}
        </section>

        <section className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5 lg:col-span-2">
          <h2 className="mb-4 text-sm font-semibold text-white">Usage</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Info label="Customers" value={isp.customer_count} />
            <Info label="Active connections" value={isp.active_service_count} />
            <Info label="Suspended connections" value={isp.suspended_service_count} />
            <Info label="New this month" value={isp.new_customers_this_month} />
            <Info label="Staff accounts" value={isp.staff_count} />
          </div>
          <p className="mt-4 text-xs text-slate-500">Counts only. Customer records stay private to the ISP.</p>
        </section>
      </div>

      {canManage && (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <section className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5">
            <h2 className="text-sm font-semibold text-white">Subscription</h2>
            <p className="mb-4 mt-1 text-xs text-slate-500">
              {isp.paid_until ? `Paid until ${formatDate(isp.paid_until)} · ${daysLeftLabel(isp.days_left)}` : "No paid-until date yet, so this ISP is never locked automatically."}
              {isp.reminder_sent_at && ` · Last reminder emailed ${formatDate(isp.reminder_sent_at)}`}
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-slate-400">
                Monthly fee (PKR)
                <input type="number" min="0" value={fee} onChange={(e) => setFee(e.target.value)} className={`${inputClass} mt-1`} />
              </label>
              <label className="text-xs text-slate-400">
                Paid until
                <input type="date" value={paidUntil} onChange={(e) => setPaidUntil(e.target.value)} className={`${inputClass} mt-1`} />
              </label>
              <label className="text-xs text-slate-400 sm:col-span-2">
                Notes
                <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
                  className="mt-1 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none" />
              </label>
            </div>
            <button
              onClick={() => void run(
                "subscription",
                () => updateISPSubscription(isp.id, { monthly_fee: fee || "0", paid_until: paidUntil || null, notes }),
                "Subscription saved.",
              )}
              disabled={busy === "subscription"}
              className="mt-4 flex h-9 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
            >
              <Save className="h-4 w-4" /> Save
            </button>
          </section>

          <section className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5">
            <h2 className="text-sm font-semibold text-white">Record a payment</h2>
            <p className="mb-4 mt-1 text-xs text-slate-500">Extends the paid-until date by the months paid.</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-slate-400">
                Amount (PKR)
                <input type="number" min="0" value={payment.amount}
                  onChange={(e) => setPayment({ ...payment, amount: e.target.value })} className={`${inputClass} mt-1`} />
              </label>
              <label className="text-xs text-slate-400">
                Months
                <select value={payment.months} onChange={(e) => setPayment({ ...payment, months: Number(e.target.value) })}
                  className={`${inputClass} mt-1`}>
                  {[1, 2, 3, 6, 12].map((m) => <option key={m} value={m}>{m} month{m > 1 ? "s" : ""}</option>)}
                </select>
              </label>
              <label className="text-xs text-slate-400">
                Method
                <select value={payment.method} onChange={(e) => setPayment({ ...payment, method: e.target.value })}
                  className={`${inputClass} mt-1`}>
                  {METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </label>
              <label className="text-xs text-slate-400">
                Reference
                <input value={payment.reference} placeholder="Transaction ID"
                  onChange={(e) => setPayment({ ...payment, reference: e.target.value })} className={`${inputClass} mt-1`} />
              </label>
            </div>
            <button
              onClick={() => void run(
                "payment",
                () => recordISPPayment(isp.id, payment),
                "Payment recorded and paid-until extended.",
              )}
              disabled={busy === "payment" || !paymentValid}
              className="mt-4 flex h-9 items-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-500"
            >
              <Plus className="h-4 w-4" /> Record Payment
            </button>
          </section>
        </div>
      )}

      <section className="mt-6 overflow-x-auto rounded-xl border border-[#1C2431] bg-[#0D1117]">
        <h2 className="border-b border-[#1C2431] px-5 py-3 text-sm font-semibold text-white">Subscription payments</h2>
        {isp.payments.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-500">No payments recorded yet.</p>
        ) : (
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-2">Receipt</th>
                <th className="px-5 py-2">Recorded</th>
                <th className="px-5 py-2">Amount</th>
                <th className="px-5 py-2">Period</th>
                <th className="px-5 py-2">Method</th>
                <th className="px-5 py-2">Reference</th>
                <th className="px-5 py-2">By</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1C2431]">
              {isp.payments.map((p) => (
                <tr key={p.id}>
                  <td className="px-5 py-2 font-mono text-xs text-slate-300">{p.receipt_number || "—"}</td>
                  <td className="px-5 py-2 text-slate-400">{formatDate(p.created_at)}</td>
                  <td className="px-5 py-2 text-slate-200">{formatPKR(p.amount)}</td>
                  <td className="px-5 py-2 text-slate-300">{formatDate(p.period_start)} – {formatDate(p.period_end)}</td>
                  <td className="px-5 py-2 text-slate-300">{METHODS.find((m) => m.value === p.method)?.label ?? p.method}</td>
                  <td className="px-5 py-2 text-slate-400">{p.reference || "—"}</td>
                  <td className="px-5 py-2 text-slate-400">{p.recorded_by || "System"}</td>
                  <td className="px-5 py-2 text-right">
                    <button
                      onClick={() => void downloadReceipt(p.id, p.receipt_number)}
                      disabled={busy === `receipt-${p.id}`}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-[#263142] px-3 py-1.5 text-xs font-semibold text-blue-300 hover:bg-blue-500/10 disabled:opacity-50"
                    >
                      {busy === `receipt-${p.id}` ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                      PDF
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {showSuspend && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setShowSuspend(false)}>
          <div className="w-full max-w-md rounded-xl border border-[#263142] bg-[#0D1117] p-5" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-base font-bold text-white">Suspend {isp.name}?</h3>
            <p className="mt-2 text-sm text-slate-400">
              Its owner and staff will not be able to sign in, and its daily billing jobs will pause until you activate it again.
            </p>
            <label className="mt-4 block text-xs text-slate-400">
              Reason *
              <textarea value={suspendReason} onChange={(e) => setSuspendReason(e.target.value)} rows={3}
                placeholder="e.g. Subscription fee unpaid for two months"
                className="mt-1 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-red-500 focus:outline-none" />
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowSuspend(false)} className="h-9 rounded-lg border border-[#263142] px-4 text-sm text-slate-300">
                Cancel
              </button>
              <button
                disabled={!suspendReason.trim() || busy === "suspend"}
                onClick={async () => {
                  await run("suspend", () => suspendISP(isp.id, suspendReason.trim()), "ISP suspended.");
                  setShowSuspend(false);
                  setSuspendReason("");
                }}
                className="h-9 rounded-lg bg-red-600 px-4 text-sm font-semibold text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-slate-500"
              >
                Confirm Suspension
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
