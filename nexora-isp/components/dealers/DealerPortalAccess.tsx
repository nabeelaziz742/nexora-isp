"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, KeyRound, Loader2, MessageCircle, X } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerPortalAccess as AccessState } from "@/services/dealer-portal.service";

const inputClass =
  "mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

// Owner/admin control for a dealer's portal login. The ISP never sees or sets the
// password: the system makes one and sends it to the dealer's WhatsApp.
// Unused while sign-in is email + password only:
// function storedOrganizationCode() {
//   try {
//     return (JSON.parse(window.localStorage.getItem("nexora_organization") ?? "{}") as { code?: string }).code ?? "";
//   } catch {
//     return "";
//   }
// }

export default function DealerPortalAccess({ dealerId }: { dealerId: string }) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<AccessState | null>(null);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sentTo, setSentTo] = useState("");

  useEffect(() => {
    if (!open) return;
    let active = true;
    dealerPortalService
      .getAccess(dealerId)
      .then((data) => {
        if (!active) return;
        setState(data);
        setEmail(data.email);
      })
      .catch((err) => active && setError(err instanceof ApiError ? err.message : "Unable to load portal access."));
    return () => {
      active = false;
    };
  }, [open, dealerId]);

  async function send() {
    if (state?.has_login && !window.confirm("Send a new password to the dealer's WhatsApp? Their old password will stop working.")) return;
    setBusy(true);
    setError("");
    try {
      const data = await dealerPortalService.sendLogin(dealerId, email.trim());
      setState(data);
      setSentTo(data.sent_to ?? "");
      toast.success(state?.has_login ? "New password sent on WhatsApp." : "Login sent on WhatsApp.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The login could not be sent.");
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
      setSentTo("");
      toast.success("Dealer login disabled.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to disable the login.");
    } finally {
      setBusy(false);
    }
  }

  function close() {
    setOpen(false);
    setSentTo("");
    setError("");
  }

  const emailChanged = Boolean(state?.has_login && email.trim().toLowerCase() !== state.email);

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
                  The password is made by the system and sent only to the dealer&apos;s WhatsApp. Nobody at the ISP sees it.
                </p>
              </div>
              <button onClick={close} aria-label="Close"><X className="h-5 w-5 text-slate-400" /></button>
            </div>

            {!state ? (
              <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-blue-500" /></div>
            ) : sentTo ? (
              <div className="mt-4 space-y-3">
                <div className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>Login details sent on WhatsApp to {sentTo}. The dealer can sign in now and change the password from their panel.</span>
                </div>
                <button onClick={close} className="h-9 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500">
                  Done
                </button>
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
                {emailChanged && (
                  <p className="text-[11px] text-amber-400">The login email will change to this one, with a new password.</p>
                )}
                {error && <p className="text-xs text-red-400">{error}</p>}
                <div className="flex flex-wrap gap-2 pt-1">
                  <button
                    onClick={() => void send()}
                    disabled={busy || !email.trim()}
                    className="flex h-9 items-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-500"
                  >
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageCircle className="h-4 w-4" />}
                    {state.has_login ? "Resend Password on WhatsApp" : "Send Login on WhatsApp"}
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
