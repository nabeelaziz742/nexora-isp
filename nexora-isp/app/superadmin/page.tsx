"use client";

import { useEffect, useState } from "react";
import { Check, Eye, Loader2, LogOut, Save, ShieldCheck, X } from "lucide-react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/services/api-error";
import {
  approveRegistration,
  getAdminRegistrations,
  getPaymentSettings,
  getReceiptObjectUrl,
  rejectRegistration,
  savePaymentSettings,
  type PaymentSettings,
  type Registration,
} from "@/services/onboarding.service";

const emptySettings = { bank_name: "", account_title: "", account_number: "", iban: "", amount: "0", instructions: "", is_active: true };

export default function SuperAdminPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [settings, setSettings] = useState<Omit<PaymentSettings, "id">>(emptySettings);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [receiptUrl, setReceiptUrl] = useState("");

  async function load(currentToken: string) {
    setLoading(true);
    try {
      const [items, payment] = await Promise.all([
        getAdminRegistrations(currentToken, "PENDING_VERIFICATION"),
        getPaymentSettings(currentToken),
      ]);
      setRegistrations(items);
      if (payment) {
        const { id: _id, ...rest } = payment;
        setSettings(rest);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        localStorage.removeItem("nexora_superadmin_access");
        router.replace("/superadmin/login");
        return;
      }
      setError(err instanceof Error ? err.message : "Unable to load admin data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const currentToken = localStorage.getItem("nexora_superadmin_access");
    if (!currentToken) {
      router.replace("/superadmin/login");
      return;
    }
    setToken(currentToken);
    void load(currentToken);
  }, [router]);

  async function saveSettings() {
    if (!token) return;
    setSaving(true);
    setError("");
    try {
      const saved = await savePaymentSettings(token, settings);
      const { id: _id, ...rest } = saved;
      setSettings(rest);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save payment settings.");
    } finally {
      setSaving(false);
    }
  }

  async function approve(id: string) {
    if (!token) return;
    setBusyId(id);
    try {
      await approveRegistration(token, id);
      setRegistrations((items) => items.filter((item) => item.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to approve payment.");
    } finally {
      setBusyId("");
    }
  }

  async function reject(id: string) {
    if (!token) return;
    const reason = window.prompt("Reason for rejecting this payment:", "Payment could not be verified.");
    if (reason === null) return;
    setBusyId(id);
    try {
      await rejectRegistration(token, id, reason);
      setRegistrations((items) => items.filter((item) => item.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reject payment.");
    } finally {
      setBusyId("");
    }
  }

  async function viewReceipt(id: string) {
    if (!token) return;
    try {
      if (receiptUrl) URL.revokeObjectURL(receiptUrl);
      setReceiptUrl(await getReceiptObjectUrl(token, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load receipt.");
    }
  }

  function logout() {
    localStorage.removeItem("nexora_superadmin_access");
    localStorage.removeItem("nexora_superadmin_refresh");
    router.replace("/superadmin/login");
  }

  if (loading) {
    return <main className="flex min-h-screen items-center justify-center bg-[#070A0F] text-white"><Loader2 className="h-7 w-7 animate-spin" /></main>;
  }

  return (
    <main className="min-h-screen bg-[#070A0F] text-white">
      <header className="border-b border-[#1C2431] bg-[#0D1117] px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3"><ShieldCheck className="h-6 w-6 text-blue-400" /><div><p className="font-semibold">Nexora Super Admin</p><p className="text-xs text-slate-500">Platform administration</p></div></div>
          <button onClick={logout} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white"><LogOut className="h-4 w-4" /> Sign out</button>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-8 px-6 py-8">
        {error && <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

        <section>
          <div className="mb-4"><h1 className="text-2xl font-bold">Payment Verification</h1><p className="text-sm text-slate-400">Review submitted receipts before activating ISP accounts.</p></div>
          {registrations.length === 0 ? (
            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-slate-500">No pending payment verifications.</div>
          ) : (
            <div className="space-y-4">
              {registrations.map((item) => (
                <div key={item.id} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5">
                  <div className="grid gap-5 lg:grid-cols-[1fr_auto]">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div><p className="text-xs text-slate-500">ISP</p><p className="font-semibold">{item.company_name}</p></div>
                      <div><p className="text-xs text-slate-500">Owner</p><p>{item.owner_name}</p><p className="text-xs text-slate-500">{item.owner_email}</p></div>
                      <div><p className="text-xs text-slate-500">Organization Code</p><p>{item.organization_code}</p></div>
                      <div><p className="text-xs text-slate-500">Amount</p><p>Rs. {item.amount_due}</p></div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                      <button onClick={() => void viewReceipt(item.id)} disabled={!item.receipt_url} className="flex h-10 items-center gap-2 rounded-lg border border-[#263142] px-4 text-sm hover:bg-[#151D27] disabled:opacity-40"><Eye className="h-4 w-4" /> Receipt</button>
                      <button onClick={() => void approve(item.id)} disabled={busyId === item.id} className="flex h-10 items-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"><Check className="h-4 w-4" /> Approve</button>
                      <button onClick={() => void reject(item.id)} disabled={busyId === item.id} className="flex h-10 items-center gap-2 rounded-lg bg-red-600 px-4 text-sm font-medium hover:bg-red-700 disabled:opacity-50"><X className="h-4 w-4" /> Reject</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-6">
          <div className="mb-5"><h2 className="text-xl font-semibold">Payment Instructions</h2><p className="text-sm text-slate-400">These details are shown to new ISP registrations.</p></div>
          <div className="grid gap-4 md:grid-cols-2">
            {(["bank_name", "account_title", "account_number", "iban", "amount"] as const).map((key) => (
              <div key={key}><label className="mb-2 block text-sm capitalize text-slate-300">{key.replaceAll("_", " ")}</label><input value={settings[key]} onChange={(e) => setSettings({ ...settings, [key]: e.target.value })} className="w-full rounded-lg border border-[#263142] bg-[#101720] px-4 py-3 text-white outline-none focus:border-blue-500" /></div>
            ))}
            <div className="md:col-span-2"><label className="mb-2 block text-sm text-slate-300">Instructions</label><textarea rows={3} value={settings.instructions} onChange={(e) => setSettings({ ...settings, instructions: e.target.value })} className="w-full rounded-lg border border-[#263142] bg-[#101720] px-4 py-3 text-white outline-none focus:border-blue-500" /></div>
          </div>
          <button onClick={() => void saveSettings()} disabled={saving} className="mt-5 flex h-11 items-center gap-2 rounded-lg bg-blue-600 px-5 font-medium hover:bg-blue-700 disabled:opacity-50">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save Payment Settings</button>
        </section>
      </div>

      {receiptUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-6" onClick={() => { URL.revokeObjectURL(receiptUrl); setReceiptUrl(""); }}>
          <div className="max-h-[90vh] max-w-4xl overflow-auto rounded-xl bg-[#0D1117] p-4" onClick={(event) => event.stopPropagation()}>
            <div className="mb-3 flex justify-end"><button onClick={() => { URL.revokeObjectURL(receiptUrl); setReceiptUrl(""); }}><X /></button></div>
            <img src={receiptUrl} alt="Payment receipt" className="max-h-[78vh] max-w-full object-contain" />
          </div>
        </div>
      )}
    </main>
  );
}
