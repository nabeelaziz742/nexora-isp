"use client";

import { useState } from "react";
import { Copy, KeyRound, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/services/api-error";
import { staffService, type OrganizationStaff } from "@/services/staff-service";

function generatePassword() {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
  const bytes = new Uint32Array(10);
  crypto.getRandomValues(bytes);
  return `St-${Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("")}`;
}

// Owner/admin sets a new password for a staff member who forgot theirs.
export default function StaffPasswordReset({ member }: { member: OrganizationStaff }) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  function start() {
    setPassword(generatePassword());
    setDone(false);
    setError("");
    setOpen(true);
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      await staffService.resetPassword(member.id, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to reset the password.");
    } finally {
      setSaving(false);
    }
  }

  const shareText = `Nexora ISP login\nEmail: ${member.email}\nNew password: ${password}\nPlease change it after signing in (profile menu → Change Password).`;

  return (
    <>
      <button
        onClick={start}
        title="Reset password"
        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-slate-700 hover:text-white"
      >
        <KeyRound className="h-3.5 w-3.5" />
        Reset Password
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 text-left" onClick={() => !saving && setOpen(false)}>
          <div className="w-full max-w-sm rounded-xl border border-[#263142] bg-[#0D1117] p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-base font-bold text-white">Reset password</h3>
                <p className="mt-1 text-xs text-slate-400">{member.full_name} · {member.email}</p>
              </div>
              <button onClick={() => setOpen(false)} aria-label="Close"><X className="h-5 w-5 text-slate-400" /></button>
            </div>

            {done ? (
              <div className="mt-4">
                <p className="text-sm text-emerald-400">Password reset. Share it with them privately:</p>
                <pre className="mt-2 whitespace-pre-wrap rounded-lg border border-[#263142] bg-[#070A0F] p-3 text-xs text-slate-200">{shareText}</pre>
                <button
                  onClick={() => {
                    void navigator.clipboard.writeText(shareText);
                    toast.success("Copied.");
                  }}
                  className="mt-3 flex h-9 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500"
                >
                  <Copy className="h-4 w-4" /> Copy
                </button>
              </div>
            ) : (
              <div className="mt-4">
                <label className="block text-xs text-slate-400">
                  New password
                  <div className="flex gap-2">
                    <input
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 font-mono text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                    />
                    <button type="button" onClick={() => setPassword(generatePassword())}
                      className="mt-1 h-10 shrink-0 rounded-lg border border-[#263142] px-3 text-xs text-slate-300 hover:bg-[#121821]">
                      New
                    </button>
                  </div>
                </label>
                <p className="mt-2 text-[11px] text-slate-500">Their old password stops working immediately.</p>
                {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
                <div className="mt-4 flex justify-end gap-2">
                  <button onClick={() => setOpen(false)} disabled={saving} className="h-9 rounded-lg border border-[#263142] px-4 text-sm text-slate-300">
                    Cancel
                  </button>
                  <button
                    onClick={() => void save()}
                    disabled={saving || password.length < 8}
                    className="flex h-9 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500"
                  >
                    {saving && <Loader2 className="h-4 w-4 animate-spin" />} Reset Password
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
