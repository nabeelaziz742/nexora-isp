"use client";

import { useEffect, useState } from "react";
import { Copy, KeyRound, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerPortalAccess as AccessState } from "@/services/dealer-portal.service";

const inputClass =
  "mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

function generatePassword() {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
  const bytes = new Uint32Array(10);
  crypto.getRandomValues(bytes);
  return `Dl-${Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("")}`;
}

// Owner/admin control for a dealer's portal login (create, reset, disable).
function storedOrganizationCode() {
  try {
    return (JSON.parse(window.localStorage.getItem("nexora_organization") ?? "{}") as { code?: string }).code ?? "";
  } catch {
    return "";
  }
}

export default function DealerPortalAccess({ dealerId }: { dealerId: string }) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<AccessState | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [shared, setShared] = useState("");

  useEffect(() => {
    if (!open) return;
    let active = true;
    dealerPortalService
      .getAccess(dealerId)
      .then((data) => {
        if (!active) return;
        setState(data);
        setEmail(data.email);
        setPassword(generatePassword());
      })
      .catch((err) => active && setError(err instanceof ApiError ? err.message : "Unable to load portal access."));
    return () => {
      active = false;
    };
  }, [open, dealerId]);

  async function save() {
    setBusy(true);
    setError("");
    try {
      const data = await dealerPortalService.setAccess(dealerId, { email: email.trim(), password });
      setState(data);
      const portalUrl = `${window.location.origin}/`;
      setShared(
        `Dealer portal login\nLink: ${portalUrl}\nOrganization code: ${storedOrganizationCode()}\nEmail: ${data.email}\nPassword: ${password}`,
      );
      toast.success(state?.has_login ? "Dealer login reset." : "Dealer login created.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to save the dealer login.");
    } finally {
      setBusy(false);
    }
  }

  async function disable() {
    if (!window.confirm("Disable this dealer's portal login? They will not be able to sign in.")) return;
    setBusy(true);
    setError("");
    try {
      setState(await dealerPortalService.revokeAccess(dealerId));
      setShared("");
      toast.success("Dealer login disabled.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to disable the login.");
    } finally {
      setBusy(false);
    }
  }

  function close() {
    setOpen(false);
    setShared("");
    setError("");
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3.5 py-2 text-xs font-semibold text-blue-400 transition hover:bg-blue-500/20"
      >
        <KeyRound className="h-3.5 w-3.5" /> Portal Login
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={close}>
          <div className="w-full max-w-md rounded-xl border border-[#263142] bg-[#0D1117] p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-base font-bold text-white">Dealer portal login</h3>
                <p className="mt-1 text-xs text-slate-400">
                  The dealer signs in on the normal login page and only sees their own customers, collections and commission.
                </p>
              </div>
              <button onClick={close} aria-label="Close"><X className="h-5 w-5 text-slate-400" /></button>
            </div>

            {!state ? (
              <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-blue-500" /></div>
            ) : shared ? (
              <div className="mt-4">
                <p className="text-sm text-emerald-400">Share these details with the dealer privately:</p>
                <pre className="mt-2 whitespace-pre-wrap rounded-lg border border-[#263142] bg-[#070A0F] p-3 text-xs text-slate-200">{shared}</pre>
                <button
                  onClick={() => {
                    void navigator.clipboard.writeText(shared);
                    toast.success("Copied.");
                  }}
                  className="mt-3 flex h-9 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500"
                >
                  <Copy className="h-4 w-4" /> Copy
                </button>
                <p className="mt-2 text-[11px] text-slate-500">The password is shown only now. Reset it here if the dealer forgets it.</p>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                <p className="text-xs">
                  Status:{" "}
                  <span className={state.is_enabled ? "font-semibold text-emerald-400" : "font-semibold text-slate-400"}>
                    {state.is_enabled ? "Login active" : state.has_login ? "Login disabled" : "No login yet"}
                  </span>
                </p>
                <label className="block text-xs text-slate-400">
                  Login email
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="dealer@example.com" className={inputClass} />
                </label>
                <label className="block text-xs text-slate-400">
                  {state.has_login ? "New password" : "Password"}
                  <div className="flex gap-2">
                    <input value={password} onChange={(e) => setPassword(e.target.value)} className={`${inputClass} font-mono`} />
                    <button type="button" onClick={() => setPassword(generatePassword())}
                      className="mt-1 h-10 shrink-0 rounded-lg border border-[#263142] px-3 text-xs text-slate-300 hover:bg-[#121821]">
                      New
                    </button>
                  </div>
                </label>
                {error && <p className="text-xs text-red-400">{error}</p>}
                <div className="flex flex-wrap gap-2 pt-1">
                  <button
                    onClick={() => void save()}
                    disabled={busy || !email.trim() || password.length < 8}
                    className="flex h-9 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500"
                  >
                    {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                    {state.has_login ? (state.is_enabled ? "Reset Password" : "Enable & Reset") : "Create Login"}
                  </button>
                  {state.is_enabled && (
                    <button onClick={() => void disable()} disabled={busy}
                      className="h-9 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 text-sm font-semibold text-rose-400 hover:bg-rose-500/20">
                      Disable Login
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
