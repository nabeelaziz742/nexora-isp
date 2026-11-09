"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Eye, EyeOff, Loader2, RadioTower } from "lucide-react";

import { ApiError } from "@/services/api-error";
import { confirmPasswordReset } from "@/services/auth.service";

export default function ResetPasswordPage() {
  const [link, setLink] = useState<{ uid: string; token: string } | null>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  // The uid and token come from the emailed link; read them once in the browser.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setLink({ uid: params.get("uid") ?? "", token: params.get("token") ?? "" });
  }, []);

  const valid = Boolean(link?.uid && link?.token);
  const mismatch = confirm.length > 0 && password !== confirm;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!link || password !== confirm) return;
    setSaving(true);
    setError("");
    try {
      await confirmPasswordReset(link.uid, link.token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to update the password. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const inputClass =
    "mt-1.5 h-11 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#070A0F] px-4 text-slate-100">
      <div className="w-full max-w-sm rounded-2xl border border-[#1C2431] bg-[#0D1117] p-6">
        <div className="mb-5 flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
            <RadioTower className="h-5 w-5 text-white" />
          </div>
          <span className="text-sm font-bold tracking-[0.12em] text-white">NEXORA ISP</span>
        </div>

        {done ? (
          <div>
            <CheckCircle2 className="h-8 w-8 text-emerald-400" />
            <h1 className="mt-3 text-lg font-bold text-white">Password updated</h1>
            <p className="mt-2 text-sm text-slate-400">You can sign in with your new password now.</p>
            <Link href="/" className="mt-5 flex h-11 items-center justify-center rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500">
              Go to sign in
            </Link>
          </div>
        ) : link && !valid ? (
          <div>
            <h1 className="text-lg font-bold text-white">Link not valid</h1>
            <p className="mt-2 text-sm text-slate-400">This reset link is incomplete. Please request a new one.</p>
            <Link href="/forgot-password" className="mt-4 inline-block text-sm text-blue-400 hover:underline">Request a new link</Link>
          </div>
        ) : (
          <form onSubmit={submit}>
            <h1 className="text-lg font-bold text-white">Choose a new password</h1>
            <p className="mt-1 text-sm text-slate-400">At least 8 characters; avoid common or all-number passwords.</p>
            <label className="mt-5 block text-xs font-medium text-slate-300">
              New password
              <input type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password" className={inputClass} />
            </label>
            <label className="mt-3 block text-xs font-medium text-slate-300">
              Confirm new password
              <input type={show ? "text" : "password"} value={confirm} onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password" className={inputClass} />
            </label>
            <button type="button" onClick={() => setShow((v) => !v)}
              className="mt-2 flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200">
              {show ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              {show ? "Hide" : "Show"} passwords
            </button>
            {mismatch && <p className="mt-2 text-xs text-amber-400">The passwords do not match.</p>}
            {error && (
              <p className="mt-3 text-sm text-red-400">
                {error}{" "}
                <Link href="/forgot-password" className="text-blue-400 hover:underline">Request a new link</Link>
              </p>
            )}
            <button
              type="submit"
              disabled={saving || password.length < 8 || password !== confirm}
              className="mt-5 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />} Update Password
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
