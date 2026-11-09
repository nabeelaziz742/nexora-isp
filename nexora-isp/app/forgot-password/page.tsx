"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, MailCheck, RadioTower } from "lucide-react";

import { ApiError } from "@/services/api-error";
import { requestPasswordReset } from "@/services/auth.service";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState("");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSending(true);
    setError("");
    try {
      const result = await requestPasswordReset(email.trim().toLowerCase());
      setSent(result.detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to send the reset email. Please try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#070A0F] px-4 text-slate-100">
      <div className="w-full max-w-sm rounded-2xl border border-[#1C2431] bg-[#0D1117] p-6">
        <div className="mb-5 flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
            <RadioTower className="h-5 w-5 text-white" />
          </div>
          <span className="text-sm font-bold tracking-[0.12em] text-white">NEXORA ISP</span>
        </div>

        {sent ? (
          <div>
            <MailCheck className="h-8 w-8 text-emerald-400" />
            <h1 className="mt-3 text-lg font-bold text-white">Check your email</h1>
            <p className="mt-2 text-sm text-slate-400">{sent}</p>
            <p className="mt-3 text-xs text-slate-500">
              No email? Ask your ISP owner to reset your password from the Staff page. ISP owners can contact Nexora support.
            </p>
          </div>
        ) : (
          <form onSubmit={submit}>
            <h1 className="text-lg font-bold text-white">Forgot your password?</h1>
            <p className="mt-1 text-sm text-slate-400">Enter your login email and we will send you a link to set a new one.</p>
            <label className="mt-5 block text-xs font-medium text-slate-300">
              Email
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                className="mt-1.5 h-11 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </label>
            {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
            <button
              type="submit"
              disabled={sending || !email.trim()}
              className="mt-5 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500"
            >
              {sending && <Loader2 className="h-4 w-4 animate-spin" />} Send Reset Link
            </button>
          </form>
        )}

        <Link href="/" className="mt-5 inline-flex items-center gap-1.5 text-xs text-blue-400 hover:underline">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to sign in
        </Link>
      </div>
    </main>
  );
}
