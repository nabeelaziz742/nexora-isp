"use client";

import { use, useEffect, useState } from "react";
import {
  Check,
  CheckCircle2,
  Clock3,
  Copy,
  CreditCard,
  Loader2,
  Upload,
  XCircle,
} from "lucide-react";

import { ApiError } from "@/services/api-error";
import {
  getRegistration,
  uploadRegistrationReceipt,
  type Registration,
} from "@/services/onboarding.service";

export default function RegistrationStatusPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const [registration, setRegistration] = useState<Registration | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  async function load() {
    try {
      setRegistration(await getRegistration(token));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Unable to load registration.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  async function handleCopy(text: string, key: string) {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => {
        setCopiedKey((curr) => (curr === key ? null : curr));
      }, 2000);
    } catch {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopiedKey(key);
      setTimeout(() => {
        setCopiedKey((curr) => (curr === key ? null : curr));
      }, 2000);
    }
  }

  async function submitReceipt() {
    if (!file) return;
    setUploading(true);
    setError("");
    setMessage("");
    try {
      await uploadRegistrationReceipt(token, file);
      setFile(null);
      setMessage(
        "Receipt submitted. Your payment is now waiting for admin verification.",
      );
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Unable to upload receipt.",
      );
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070A0F] text-white">
        <Loader2 className="h-7 w-7 animate-spin text-blue-500" />
      </main>
    );
  }

  if (!registration) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070A0F] px-6 text-red-400">
        {error || "Registration not found."}
      </main>
    );
  }

  const pendingPayment =
    registration.status === "PENDING_PAYMENT" ||
    registration.status === "REJECTED";
  const payment = registration.payment;

  const bankName = payment?.bank_name || "HBL";
  const accountTitle = payment?.account_title || "Muhammad Nabeel";
  const accountNumber = payment?.account_number || "17877900894403";
  const iban = payment?.iban || "";
  const instructions =
    payment?.instructions ||
    "Please deposit the ISP registration setup fee to the designated account and upload your payment receipt.";

  return (
    <main className="min-h-screen bg-[#070A0F] px-4 py-12 text-white sm:px-6">
      <div className="mx-auto max-w-2xl rounded-2xl border border-[#1C2431] bg-[#0D1117] p-6 shadow-2xl sm:p-8">
        <div className="border-b border-[#1C2431] pb-6">
          <h1 className="text-2xl font-bold tracking-tight">Account Activation</h1>
          <p className="mt-1 text-sm text-slate-400">
            {registration.company_name} · {registration.owner_email}
          </p>
        </div>

        <div className="mt-6 rounded-xl border border-[#263142] bg-[#101720] p-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-wider text-slate-500">
                Organization Code
              </p>
              <p className="mt-1 font-mono text-xl font-semibold text-blue-400">
                {registration.organization_code}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-slate-500">
                Registration Status
              </p>
              <div className="mt-1 flex items-center gap-2 font-medium">
                {registration.status === "ACTIVE" && (
                  <>
                    <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                    <span className="text-emerald-400">Active / Verified</span>
                  </>
                )}
                {registration.status === "REJECTED" && (
                  <>
                    <XCircle className="h-5 w-5 text-red-400" />
                    <span className="text-red-400">Payment Rejected</span>
                  </>
                )}
                {registration.status === "PENDING_PAYMENT" && (
                  <>
                    <Clock3 className="h-5 w-5 text-amber-400" />
                    <span className="text-amber-400">Pending Payment</span>
                  </>
                )}
                {registration.status === "PENDING_VERIFICATION" && (
                  <>
                    <Clock3 className="h-5 w-5 text-blue-400" />
                    <span className="text-blue-400">Pending Admin Verification</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {pendingPayment && (
          <div className="mt-6 space-y-6">
            {/* Payment Instructions Card */}
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-5 sm:p-6">
              <div className="flex items-center gap-2.5 pb-2">
                <CreditCard className="h-5 w-5 text-blue-400" />
                <h2 className="text-lg font-semibold text-white">
                  Payment Instructions
                </h2>
              </div>
              <p className="text-sm text-slate-300">
                Please transfer the setup fee of{" "}
                <span className="font-semibold text-white">
                  Rs. {registration.amount_due || "5,000.00"}
                </span>{" "}
                using the bank details below:
              </p>

              <div className="mt-4 space-y-3 rounded-lg border border-[#263142] bg-[#0D1117] p-4 text-sm">
                {/* Bank Name */}
                <div className="flex flex-col justify-between gap-1 border-b border-[#1C2431] pb-3 sm:flex-row sm:items-center">
                  <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                    Bank Name
                  </span>
                  <span className="font-semibold text-white sm:text-base">
                    {bankName}
                  </span>
                </div>

                {/* Account Title */}
                <div className="flex flex-col justify-between gap-2 border-b border-[#1C2431] pb-3 sm:flex-row sm:items-center">
                  <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                    Account Title
                  </span>
                  <div className="flex items-center justify-between gap-2 sm:justify-end">
                    <span className="font-medium text-white">
                      {accountTitle}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(accountTitle, "account_title")}
                      className="inline-flex items-center gap-1.5 rounded-md border border-[#263142] bg-[#101720] px-2.5 py-1 text-xs text-slate-300 transition-colors hover:border-blue-500 hover:text-white"
                      title="Copy Account Title"
                    >
                      {copiedKey === "account_title" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5 text-slate-400" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Account Number */}
                <div className="flex flex-col justify-between gap-2 border-b border-[#1C2431] pb-3 sm:flex-row sm:items-center">
                  <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                    Account No.
                  </span>
                  <div className="flex items-center justify-between gap-2 sm:justify-end">
                    <span className="font-mono text-base font-bold tracking-wide text-blue-400">
                      {accountNumber}
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        handleCopy(accountNumber, "account_number")
                      }
                      className="inline-flex items-center gap-1.5 rounded-md border border-[#263142] bg-[#101720] px-2.5 py-1 text-xs text-slate-300 transition-colors hover:border-blue-500 hover:text-white"
                      title="Copy Account Number"
                    >
                      {copiedKey === "account_number" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5 text-slate-400" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* IBAN if available */}
                {iban && (
                  <div className="flex flex-col justify-between gap-2 border-b border-[#1C2431] pb-3 sm:flex-row sm:items-center">
                    <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                      IBAN
                    </span>
                    <div className="flex items-center justify-between gap-2 sm:justify-end">
                      <span className="font-mono text-sm text-slate-300">
                        {iban}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopy(iban, "iban")}
                        className="inline-flex items-center gap-1.5 rounded-md border border-[#263142] bg-[#101720] px-2.5 py-1 text-xs text-slate-300 transition-colors hover:border-blue-500 hover:text-white"
                        title="Copy IBAN"
                      >
                        {copiedKey === "iban" ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5 text-slate-400" />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {instructions && (
                  <p className="pt-1 text-xs leading-relaxed text-slate-400">
                    {instructions}
                  </p>
                )}
              </div>
            </div>

            {/* Rejection notice if previously rejected */}
            {registration.rejection_reason && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
                <p className="font-semibold text-red-200">
                  Payment Verification Rejected:
                </p>
                <p className="mt-1">{registration.rejection_reason}</p>
                <p className="mt-2 text-xs text-red-300/80">
                  Please check the payment details above and upload a valid receipt.
                </p>
              </div>
            )}

            {/* Receipt Upload Section */}
            <div className="rounded-xl border border-[#263142] bg-[#101720] p-5 sm:p-6">
              <h3 className="text-base font-semibold text-white">
                Upload Payment Receipt
              </h3>
              <p className="mt-1 text-xs text-slate-400">
                Attach a screenshot or photo of your payment confirmation / deposit slip.
              </p>

              <div className="mt-4">
                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  className="block w-full cursor-pointer text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-blue-700"
                />
              </div>

              <button
                onClick={submitReceipt}
                disabled={!file || uploading}
                className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
              >
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                Submit Receipt
              </button>
            </div>
          </div>
        )}

        {registration.status === "PENDING_VERIFICATION" && (
          <div className="mt-6 rounded-xl border border-blue-500/20 bg-blue-500/5 p-5 text-sm leading-relaxed text-blue-200">
            Your receipt has been submitted. Login will remain disabled until the payment is verified by Nexora administration.
          </div>
        )}

        {registration.status === "ACTIVE" && (
          <div className="mt-6 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 text-sm leading-relaxed text-emerald-200">
            Your payment has been verified and your account is active. You can now sign in using your organization code, email, and password.
          </div>
        )}

        {message && <p className="mt-5 text-sm font-medium text-emerald-400">{message}</p>}
        {error && <p className="mt-5 text-sm font-medium text-red-400">{error}</p>}
      </div>
    </main>
  );
}
