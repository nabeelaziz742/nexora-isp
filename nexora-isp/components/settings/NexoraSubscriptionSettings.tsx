"use client";

import { useEffect, useState } from "react";
import { Download, Loader2, ReceiptText } from "lucide-react";

import { useToast } from "@/hooks/useToast";
import { ApiError } from "@/services/api-error";
import {
  getOwnerSubscription,
  getOwnerSubscriptionReceipt,
  type OwnerSubscriptionStatus,
} from "@/services/auth.service";
import { saveFile } from "@/services/onboarding.service";

function formatDate(value: string) {
  return new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

const pkr = (value: string) => `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

// The ISP owner's own Nexora plan and the receipts for what they paid. Hidden for other roles.
export default function NexoraSubscriptionSettings() {
  const { error: toastError } = useToast();
  const [status, setStatus] = useState<OwnerSubscriptionStatus | null>(null);
  const [downloading, setDownloading] = useState("");

  useEffect(() => {
    try {
      if (window.localStorage.getItem("nexora_role") !== "OWNER") return;
    } catch {
      return;
    }
    getOwnerSubscription().then(setStatus).catch(() => undefined);
  }, []);

  async function download(paymentId: string, receiptNumber: string) {
    setDownloading(paymentId);
    try {
      saveFile(await getOwnerSubscriptionReceipt(paymentId), `${receiptNumber || "receipt"}.pdf`);
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Unable to download the receipt.");
    } finally {
      setDownloading("");
    }
  }

  if (!status) return null;

  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center bg-blue-500/10">
            <ReceiptText className="h-4 w-4 text-blue-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-100">Nexora Subscription</h2>
            <p className="mt-1 text-xs text-slate-500">Your plan with Nexora and receipts for the fees you have paid.</p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 border-b border-[#202938] p-5 sm:grid-cols-3">
        <div>
          <p className="text-[11px] uppercase tracking-wider text-slate-500">Monthly fee</p>
          <p className="mt-1 text-sm font-semibold text-slate-100">{pkr(status.monthly_fee)}</p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wider text-slate-500">Paid until</p>
          <p className="mt-1 text-sm font-semibold text-slate-100">{status.paid_until ? formatDate(status.paid_until) : "—"}</p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wider text-slate-500">Pay to</p>
          <p className="mt-1 text-sm text-slate-300">
            {status.payment.bank_name} · {status.payment.account_title} · {status.payment.account_number}
          </p>
        </div>
      </div>

      {status.payments.length === 0 ? (
        <p className="p-6 text-center text-sm text-slate-500">No payments recorded yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[620px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-2">Receipt</th>
                <th className="px-5 py-2">Paid on</th>
                <th className="px-5 py-2">Amount</th>
                <th className="px-5 py-2">Period</th>
                <th className="px-5 py-2">Method</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[#202938]">
              {status.payments.map((p) => (
                <tr key={p.id}>
                  <td className="px-5 py-2 font-mono text-xs text-slate-300">{p.receipt_number || "—"}</td>
                  <td className="px-5 py-2 text-slate-400">{formatDate(p.created_at)}</td>
                  <td className="px-5 py-2 text-slate-200">{pkr(p.amount)}</td>
                  <td className="px-5 py-2 text-slate-300">{formatDate(p.period_start)} – {formatDate(p.period_end)}</td>
                  <td className="px-5 py-2 text-slate-400">{p.method}</td>
                  <td className="px-5 py-2 text-right">
                    <button
                      onClick={() => void download(p.id, p.receipt_number)}
                      disabled={downloading === p.id}
                      className="inline-flex items-center gap-1.5 border border-[#263142] px-3 py-1.5 text-xs font-semibold text-blue-300 hover:bg-blue-500/10 disabled:opacity-50"
                    >
                      {downloading === p.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                      Receipt PDF
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
