"use client";

import { use, useEffect, useState } from "react";
import { CheckCircle2, Clock3, Loader2, Upload, XCircle } from "lucide-react";

import { ApiError } from "@/services/api-error";
import { getRegistration, uploadRegistrationReceipt, type Registration } from "@/services/onboarding.service";

export default function RegistrationStatusPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [registration, setRegistration] = useState<Registration | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      setRegistration(await getRegistration(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load registration.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  async function submitReceipt() {
    if (!file) return;
    setUploading(true);
    setError("");
    setMessage("");
    try {
      await uploadRegistrationReceipt(token, file);
      setFile(null);
      setMessage("Receipt submitted. Your payment is now waiting for admin verification.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to upload receipt.");
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return <main className="flex min-h-screen items-center justify-center bg-[#070A0F] text-white"><Loader2 className="h-7 w-7 animate-spin" /></main>;
  }

  if (!registration) {
    return <main className="flex min-h-screen items-center justify-center bg-[#070A0F] px-6 text-red-400">{error || "Registration not found."}</main>;
  }

  const pendingPayment = registration.status === "PENDING_PAYMENT" || registration.status === "REJECTED";
  const payment = registration.payment;

  return (
    <main className="min-h-screen bg-[#070A0F] px-6 py-12 text-white">
      <div className="mx-auto max-w-2xl rounded-2xl border border-[#1C2431] bg-[#0D1117] p-8 shadow-2xl">
        <h1 className="text-2xl font-bold">Account Activation</h1>
        <p className="mt-2 text-sm text-slate-400">{registration.company_name} · {registration.owner_email}</p>

        <div className="mt-8 rounded-xl border border-[#263142] bg-[#101720] p-5">
          <p className="text-xs uppercase tracking-wider text-slate-500">Organization Code</p>
          <p className="mt-1 text-xl font-semibold">{registration.organization_code}</p>
          <p className="mt-4 text-xs uppercase tracking-wider text-slate-500">Status</p>
          <div className="mt-2 flex items-center gap-2 font-medium">
            {registration.status === "ACTIVE" && <CheckCircle2 className="h-5 w-5 text-emerald-400" />}
            {registration.status === "REJECTED" && <XCircle className="h-5 w-5 text-red-400" />}
            {registration.status === "PENDING_PAYMENT" && <Clock3 className="h-5 w-5 text-amber-400" />}
            {registration.status === "PENDING_VERIFICATION" && <Clock3 className="h-5 w-5 text-blue-400" />}
            {registration.status.replaceAll("_", " ")}
          </div>
        </div>

        {pendingPayment && (
          <div className="mt-6 space-y-5 rounded-xl border border-blue-500/20 bg-blue-500/5 p-5">
            <div>
              <h2 className="font-semibold">Complete Your Payment</h2>
              <p className="mt-1 text-sm text-slate-400">Transfer the required amount and upload the payment receipt below.</p>
            </div>

            {payment && (
              <div className="grid gap-3 rounded-lg border border-[#263142] bg-[#0D1117] p-4 text-sm text-slate-300">
                <p><span className="text-slate-500">Bank:</span> {payment.bank_name}</p>
                <p><span className="text-slate-500">Account Title:</span> {payment.account_title}</p>
                <p><span className="text-slate-500">Account Number:</span> {payment.account_number}</p>
                {payment.iban && <p><span className="text-slate-500">IBAN:</span> {payment.iban}</p>}
                <p><span className="text-slate-500">Amount:</span> Rs. {registration.amount_due}</p>
                {payment.instructions && <p className="text-slate-400">{payment.instructions}</p>}
              </div>
            )}

            {registration.rejection_reason && <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{registration.rejection_reason}</div>}
            <div>
              <label className="mb-2 block text-sm text-slate-300">Payment Receipt</label>
              <input type="file" accept="image/*" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="block w-full text-sm text-slate-300" />
            </div>
            <button onClick={submitReceipt} disabled={!file || uploading} className="flex h-11 items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 font-medium hover:bg-blue-700 disabled:opacity-50">
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              Submit Receipt
            </button>
          </div>
        )}

        {registration.status === "PENDING_VERIFICATION" && (
          <div className="mt-6 rounded-xl border border-blue-500/20 bg-blue-500/5 p-5 text-sm text-blue-200">Your receipt has been submitted. Login will remain disabled until the payment is verified by Nexora administration.</div>
        )}

        {registration.status === "ACTIVE" && (
          <div className="mt-6 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 text-sm text-emerald-200">Your payment has been verified and your account is active. You can now sign in using your organization code, email, and password.</div>
        )}

        {message && <p className="mt-5 text-sm text-emerald-400">{message}</p>}
        {error && <p className="mt-5 text-sm text-red-400">{error}</p>}
      </div>
    </main>
  );
}
