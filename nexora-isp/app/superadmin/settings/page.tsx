"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Save } from "lucide-react";

import { ErrorBanner, PageHeader, useSuperAdminErrorHandler } from "@/components/superadmin/ui";
import { getPaymentSettings, savePaymentSettings, type PaymentSettings } from "@/services/onboarding.service";

type Form = Omit<PaymentSettings, "id">;

const EMPTY: Form = {
  bank_name: "",
  account_title: "",
  account_number: "",
  iban: "",
  amount: "0",
  instructions: "",
  subscription_grace_days: 7,
  is_active: true,
};

const inputClass =
  "mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

export default function PaymentSettingsPage() {
  const [form, setForm] = useState<Form>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const handleError = useSuperAdminErrorHandler(setError);

  const load = useCallback(async () => {
    try {
      const data = await getPaymentSettings();
      if (data) {
        const { id: _id, ...rest } = data;
        void _id;
        setForm({ ...EMPTY, ...rest });
      }
    } catch (err) {
      handleError(err, "Unable to load payment settings.");
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  useEffect(() => {
    void load();
  }, [load]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const token = localStorage.getItem("nexora_superadmin_access") ?? "";
      const { id: _id, ...rest } = await savePaymentSettings(token, form);
      void _id;
      setForm({ ...EMPTY, ...rest });
      setSaved(true);
    } catch (err) {
      handleError(err, "Unable to save payment settings.");
    } finally {
      setSaving(false);
    }
  }

  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((current) => ({ ...current, [key]: value }));

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <>
      <PageHeader title="Payment Settings" subtitle="Shown to new ISPs when they register, and used for subscription rules." />
      <ErrorBanner message={error} />
      {saved && (
        <div className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-400">Settings saved.</div>
      )}

      <form onSubmit={save} className="max-w-2xl space-y-5 rounded-xl border border-[#1C2431] bg-[#0D1117] p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-xs text-slate-400">
            Bank / wallet name
            <input required value={form.bank_name} onChange={(e) => set("bank_name", e.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            Account title
            <input required value={form.account_title} onChange={(e) => set("account_title", e.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            Account number
            <input required value={form.account_number} onChange={(e) => set("account_number", e.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            IBAN
            <input value={form.iban} onChange={(e) => set("iban", e.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            Default fee for new ISPs (PKR)
            <input required type="number" min="0" value={form.amount} onChange={(e) => set("amount", e.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            Grace days before an unpaid ISP is locked
            <input required type="number" min="0" max="90" value={form.subscription_grace_days ?? 7}
              onChange={(e) => set("subscription_grace_days", Number(e.target.value))} className={inputClass} />
          </label>
        </div>
        <label className="block text-xs text-slate-400">
          Instructions for ISPs
          <textarea value={form.instructions} onChange={(e) => set("instructions", e.target.value)} rows={4}
            className="mt-1 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none" />
        </label>
        <button type="submit" disabled={saving}
          className="flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save Settings
        </button>
      </form>
    </>
  );
}
