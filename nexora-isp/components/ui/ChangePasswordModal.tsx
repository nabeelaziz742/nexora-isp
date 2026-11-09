"use client";

import { useState } from "react";
import { Eye, EyeOff, Loader2, X } from "lucide-react";
import { toast } from "sonner";

const inputClass =
  "mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 pr-10 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

// Shared by the staff workspace, the dealer portal and the super admin panel;
// each passes the request that changes the password for its own session type.
export default function ChangePasswordModal({
  onClose,
  submit,
}: {
  onClose: () => void;
  submit: (currentPassword: string, newPassword: string) => Promise<unknown>;
}) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const mismatch = confirm.length > 0 && next !== confirm;
  const canSave = current.length > 0 && next.length >= 8 && next === confirm && !saving;

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!canSave) return;
    setSaving(true);
    setError("");
    try {
      await submit(current, next);
      toast.success("Password changed. Use the new password next time you sign in.");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to change the password.");
    } finally {
      setSaving(false);
    }
  }

  const field = (label: string, value: string, set: (v: string) => void, autoComplete: string) => (
    <label className="block text-xs text-slate-400">
      {label}
      <div className="relative">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => set(e.target.value)}
          autoComplete={autoComplete}
          className={inputClass}
        />
      </div>
    </label>
  );

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4" onClick={() => !saving && onClose()}>
      <form
        onSubmit={save}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-xl border border-[#263142] bg-[#0D1117] p-5"
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h3 className="text-base font-bold text-white">Change password</h3>
            <p className="mt-1 text-xs text-slate-400">At least 8 characters; avoid common or all-number passwords.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close"><X className="h-5 w-5 text-slate-400" /></button>
        </div>
        <div className="space-y-3">
          {field("Current password", current, setCurrent, "current-password")}
          {field("New password", next, setNext, "new-password")}
          {field("Confirm new password", confirm, setConfirm, "new-password")}
        </div>
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          className="mt-2 flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200"
        >
          {show ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
          {show ? "Hide passwords" : "Show passwords"}
        </button>
        {mismatch && <p className="mt-2 text-xs text-amber-400">The new passwords do not match.</p>}
        {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} disabled={saving} className="h-9 rounded-lg border border-[#263142] px-4 text-sm text-slate-300">
            Cancel
          </button>
          <button
            type="submit"
            disabled={!canSave}
            className="flex h-9 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />} Change Password
          </button>
        </div>
      </form>
    </div>
  );
}
