"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Building2,
  Check,
  CheckCircle2,
  ClipboardCheck,
  Copy,
  CreditCard,
  Eye,
  FileText,
  Landmark,
  Loader2,
  LogOut,
  Mail,
  RefreshCw,
  Save,
  Search,
  Settings2,
  ShieldCheck,
  WalletCards,
  X,
  XCircle,
} from "lucide-react";
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

const emptySettings: Omit<PaymentSettings, "id"> = {
  bank_name: "",
  account_title: "",
  account_number: "",
  iban: "",
  amount: "0",
  instructions: "",
  is_active: true,
};

type Section = "overview" | "review" | "settings";

export default function SuperAdminPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [settings, setSettings] = useState<Omit<PaymentSettings, "id">>(emptySettings);
  const [section, setSection] = useState<Section>("overview");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [receiptUrl, setReceiptUrl] = useState("");

  async function load(currentToken: string, silent = false) {
    if (silent) setRefreshing(true);
    else setLoading(true);
    setError("");

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
        localStorage.removeItem("nexora_superadmin_refresh");
        router.replace("/superadmin/login");
        return;
      }
      setError(err instanceof Error ? err.message : "Unable to load admin data.");
    } finally {
      setLoading(false);
      setRefreshing(false);
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

  const filteredRegistrations = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return registrations;
    return registrations.filter((item) =>
      [item.company_name, item.owner_name, item.owner_email, item.organization_code]
        .join(" ")
        .toLowerCase()
        .includes(term),
    );
  }, [registrations, search]);

  async function saveSettings() {
    if (!token) return;
    setSaving(true);
    setError("");
    setNotice("");

    try {
      const saved = await savePaymentSettings(token, {
        ...settings,
        bank_name: settings.bank_name.trim(),
        account_title: settings.account_title.trim(),
        account_number: settings.account_number.trim(),
        iban: settings.iban.trim(),
        instructions: settings.instructions.trim(),
      });
      const { id: _id, ...rest } = saved;
      setSettings(rest);
      setNotice("Payment instructions saved successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save payment settings.");
    } finally {
      setSaving(false);
    }
  }

  async function approve(id: string) {
    if (!token) return;
    setBusyId(id);
    setError("");
    setNotice("");
    try {
      await approveRegistration(token, id);
      setRegistrations((items) => items.filter((item) => item.id !== id));
      setNotice("Payment verified. The ISP account has been activated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to approve payment.");
    } finally {
      setBusyId("");
    }
  }

  async function reject(id: string) {
    if (!token) return;
    const reason = window.prompt(
      "Reason for rejecting this payment:",
      "Payment could not be verified from the submitted receipt.",
    );
    if (reason === null) return;

    setBusyId(id);
    setError("");
    setNotice("");
    try {
      await rejectRegistration(token, id, reason.trim());
      setRegistrations((items) => items.filter((item) => item.id !== id));
      setNotice("Payment rejected. The applicant can resubmit a receipt.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reject payment.");
    } finally {
      setBusyId("");
    }
  }

  async function viewReceipt(id: string) {
    if (!token) return;
    setError("");
    try {
      if (receiptUrl) URL.revokeObjectURL(receiptUrl);
      setReceiptUrl(await getReceiptObjectUrl(token, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load receipt.");
    }
  }

  async function copyValue(value: string, label: string) {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setNotice(`${label} copied to clipboard.`);
    } catch {
      setError(`Unable to copy ${label.toLowerCase()}.`);
    }
  }

  function logout() {
    localStorage.removeItem("nexora_superadmin_access");
    localStorage.removeItem("nexora_superadmin_refresh");
    router.replace("/superadmin/login");
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070A0F] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-7 w-7 animate-spin text-blue-400" />
          <p className="text-sm text-slate-500">Loading Nexora administration…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#070A0F] text-white">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 shrink-0 border-r border-[#1B2430] bg-[#0A0E14] lg:flex lg:flex-col">
          <div className="border-b border-[#1B2430] px-6 py-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600/15 ring-1 ring-blue-500/20">
                <ShieldCheck className="h-5 w-5 text-blue-400" />
              </div>
              <div>
                <p className="font-semibold tracking-tight">NEXORA</p>
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Super Admin</p>
              </div>
            </div>
          </div>

          <nav className="flex-1 space-y-1 px-3 py-5">
            <SidebarButton active={section === "overview"} icon={<WalletCards className="h-4 w-4" />} label="Overview" onClick={() => setSection("overview")} />
            <SidebarButton active={section === "review"} icon={<ClipboardCheck className="h-4 w-4" />} label="Payment Review" badge={registrations.length} onClick={() => setSection("review")} />
            <SidebarButton active={section === "settings"} icon={<Settings2 className="h-4 w-4" />} label="Payment Settings" onClick={() => setSection("settings")} />
          </nav>

          <div className="border-t border-[#1B2430] p-3">
            <button onClick={logout} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-400 transition hover:bg-white/[0.04] hover:text-white">
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 border-b border-[#1B2430] bg-[#070A0F]/90 px-5 py-4 backdrop-blur-xl sm:px-8">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-blue-400">Platform Administration</p>
                <h1 className="mt-1 text-xl font-semibold tracking-tight sm:text-2xl">{section === "overview" ? "Command Center" : section === "review" ? "Payment Review" : "Payment Settings"}</h1>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => token && void load(token, true)}
                  disabled={refreshing}
                  className="flex h-10 items-center gap-2 rounded-xl border border-[#263142] bg-[#0D1117] px-3 text-sm text-slate-300 transition hover:border-[#344154] hover:text-white disabled:opacity-50"
                >
                  <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                  <span className="hidden sm:inline">Refresh</span>
                </button>
                <button onClick={logout} className="flex h-10 items-center justify-center rounded-xl border border-[#263142] bg-[#0D1117] px-3 text-slate-400 hover:text-white lg:hidden">
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="mt-4 flex gap-1 overflow-x-auto lg:hidden">
              <MobileTab active={section === "overview"} label="Overview" onClick={() => setSection("overview")} />
              <MobileTab active={section === "review"} label={`Review${registrations.length ? ` (${registrations.length})` : ""}`} onClick={() => setSection("review")} />
              <MobileTab active={section === "settings"} label="Settings" onClick={() => setSection("settings")} />
            </div>
          </header>

          <div className="mx-auto max-w-[1400px] space-y-7 px-5 py-6 sm:px-8 sm:py-8">
            {(error || notice) && (
              <div className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${error ? "border-red-500/20 bg-red-500/[0.06] text-red-300" : "border-emerald-500/20 bg-emerald-500/[0.06] text-emerald-300"}`}>
                {error ? <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> : <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />}
                <span>{error || notice}</span>
              </div>
            )}

            {section === "overview" && (
              <>
                <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  <StatCard icon={<ClipboardCheck className="h-5 w-5" />} label="Awaiting Verification" value={registrations.length.toString()} tone="blue" />
                  <StatCard icon={<Building2 className="h-5 w-5" />} label="Registration Flow" value="Payment Gated" tone="slate" />
                  <StatCard icon={<CreditCard className="h-5 w-5" />} label="Payment Method" value="Manual Review" tone="slate" />
                  <StatCard icon={<CheckCircle2 className="h-5 w-5" />} label="Activation Rule" value="Admin Approval" tone="emerald" />
                </section>

                <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
                  <div className="overflow-hidden rounded-2xl border border-[#1B2430] bg-[#0D1117]">
                    <div className="flex flex-col gap-4 border-b border-[#1B2430] p-5 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Needs attention</p>
                        <h2 className="mt-1 text-lg font-semibold">Payment Verification Queue</h2>
                      </div>
                      <button onClick={() => setSection("review")} className="text-sm font-medium text-blue-400 hover:text-blue-300">Open queue →</button>
                    </div>
                    {registrations.length === 0 ? (
                      <EmptyState icon={<CheckCircle2 className="h-6 w-6" />} title="Queue is clear" description="No payment receipts are waiting for verification." />
                    ) : (
                      <div className="divide-y divide-[#1B2430]">
                        {registrations.slice(0, 5).map((item) => (
                          <QueueRow key={item.id} item={item} onReceipt={() => void viewReceipt(item.id)} onApprove={() => void approve(item.id)} busy={busyId === item.id} />
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="rounded-2xl border border-[#1B2430] bg-[#0D1117] p-5">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-300 ring-1 ring-amber-500/15"><Landmark className="h-5 w-5" /></div>
                      <div><p className="text-xs uppercase tracking-[0.16em] text-slate-500">Customer payment details</p><h2 className="font-semibold">Bank configuration</h2></div>
                    </div>
                    <div className="mt-6 space-y-4">
                      <InfoLine label="Bank" value={settings.bank_name || "Not configured"} />
                      <InfoLine label="Account title" value={settings.account_title || "Not configured"} />
                      <InfoLine label="Account number" value={settings.account_number || "Not configured"} copyable onCopy={() => void copyValue(settings.account_number, "Account number")} />
                      <InfoLine label="IBAN" value={settings.iban || "Not configured"} copyable onCopy={() => void copyValue(settings.iban, "IBAN")} />
                      <InfoLine label="Registration fee" value={settings.amount && settings.amount !== "0" ? `Rs. ${settings.amount}` : "Not configured"} />
                    </div>
                    <button onClick={() => setSection("settings")} className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl border border-[#263142] bg-[#101720] py-2.5 text-sm font-medium text-slate-200 transition hover:border-blue-500/30 hover:bg-blue-500/[0.06]"> <Settings2 className="h-4 w-4" /> Manage payment details</button>
                  </div>
                </section>
              </>
            )}

            {section === "review" && (
              <section className="space-y-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.16em] text-blue-400">Manual payment verification</p>
                    <h2 className="mt-1 text-2xl font-semibold">Review submitted receipts</h2>
                    <p className="mt-1 text-sm text-slate-500">Verify the receipt before activating the ISP account.</p>
                  </div>
                  <div className="relative w-full sm:w-72">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                    <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search ISP, owner or code" className="h-10 w-full rounded-xl border border-[#263142] bg-[#0D1117] pl-9 pr-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-blue-500/50" />
                  </div>
                </div>

                {filteredRegistrations.length === 0 ? (
                  <EmptyState icon={<ClipboardCheck className="h-6 w-6" />} title={search ? "No matching registrations" : "No pending verifications"} description={search ? "Try another search term." : "New receipt submissions will appear here for review."} />
                ) : (
                  <div className="space-y-4">
                    {filteredRegistrations.map((item) => (
                      <ReviewCard key={item.id} item={item} busy={busyId === item.id} onReceipt={() => void viewReceipt(item.id)} onApprove={() => void approve(item.id)} onReject={() => void reject(item.id)} />
                    ))}
                  </div>
                )}
              </section>
            )}

            {section === "settings" && (
              <section className="mx-auto max-w-5xl space-y-6">
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-blue-400">Customer-facing payment setup</p>
                  <h2 className="mt-1 text-2xl font-semibold">Payment Instructions</h2>
                  <p className="mt-1 text-sm text-slate-500">These exact details are displayed to new ISP registrations before receipt upload.</p>
                </div>

                <div className="grid gap-6 lg:grid-cols-[1fr_0.7fr]">
                  <div className="rounded-2xl border border-[#1B2430] bg-[#0D1117] p-6">
                    <div className="mb-6 flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-300 ring-1 ring-blue-500/15"><Landmark className="h-5 w-5" /></div>
                      <div><h3 className="font-semibold">Bank account</h3><p className="text-xs text-slate-500">Do not leave these fields blank in production.</p></div>
                    </div>

                    <div className="grid gap-5 sm:grid-cols-2">
                      <Field label="Bank name" value={settings.bank_name} onChange={(value) => setSettings({ ...settings, bank_name: value })} placeholder="e.g. HBL" required />
                      <Field label="Account title" value={settings.account_title} onChange={(value) => setSettings({ ...settings, account_title: value })} placeholder="Registered business name" required />
                      <Field label="Account number" value={settings.account_number} onChange={(value) => setSettings({ ...settings, account_number: value })} placeholder="Bank account number" required />
                      <Field label="IBAN" value={settings.iban} onChange={(value) => setSettings({ ...settings, iban: value })} placeholder="PK00 XXXX …" />
                      <Field label="Registration fee (PKR)" value={settings.amount} onChange={(value) => setSettings({ ...settings, amount: value })} placeholder="0.00" type="number" required />
                    </div>

                    <div className="mt-5">
                      <label className="mb-2 block text-sm font-medium text-slate-300">Payment instructions</label>
                      <textarea value={settings.instructions} onChange={(e) => setSettings({ ...settings, instructions: e.target.value })} rows={5} placeholder="Tell the applicant how to make the transfer and what to include in the receipt." className="w-full rounded-xl border border-[#263142] bg-[#101720] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-blue-500/50" />
                    </div>

                    <button onClick={() => void saveSettings()} disabled={saving} className="mt-6 flex h-11 items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 text-sm font-semibold shadow-lg shadow-blue-900/20 transition hover:bg-blue-500 disabled:opacity-50">
                      {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                      Save payment configuration
                    </button>
                  </div>

                  <div className="space-y-5">
                    <div className="rounded-2xl border border-blue-500/15 bg-blue-500/[0.04] p-5">
                      <div className="flex items-start gap-3"><FileText className="mt-0.5 h-5 w-5 text-blue-400" /><div><h3 className="font-semibold">Customer flow</h3><p className="mt-1 text-sm leading-6 text-slate-400">Applicants see these details after registration, transfer the fee, then upload a receipt. Their account stays disabled until you approve it.</p></div></div>
                    </div>
                    <div className="rounded-2xl border border-[#1B2430] bg-[#0D1117] p-5">
                      <div className="flex items-center justify-between"><div><p className="text-xs uppercase tracking-[0.16em] text-slate-500">Configuration status</p><h3 className="mt-1 font-semibold">Payment setup</h3></div><StatusPill active={Boolean(settings.bank_name && settings.account_title && settings.account_number && settings.amount !== "0")} /></div>
                      <div className="mt-5 space-y-3 text-sm"><ChecklistItem label="Bank name" complete={Boolean(settings.bank_name)} /><ChecklistItem label="Account title" complete={Boolean(settings.account_title)} /><ChecklistItem label="Account number" complete={Boolean(settings.account_number)} /><ChecklistItem label="Registration fee" complete={Boolean(settings.amount && settings.amount !== "0")} /></div>
                    </div>
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>
      </div>

      {receiptUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4 backdrop-blur-sm" onClick={() => { URL.revokeObjectURL(receiptUrl); setReceiptUrl(""); }}>
          <div className="flex max-h-[94vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-[#293445] bg-[#0D1117] shadow-2xl" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-[#1B2430] px-5 py-4">
              <div><p className="text-xs uppercase tracking-[0.16em] text-blue-400">Secure document viewer</p><h3 className="font-semibold">Payment Receipt</h3></div>
              <button onClick={() => { URL.revokeObjectURL(receiptUrl); setReceiptUrl(""); }} className="rounded-lg p-2 text-slate-400 hover:bg-white/[0.05] hover:text-white"><X className="h-5 w-5" /></button>
            </div>
            <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto bg-[#080B10] p-5"><img src={receiptUrl} alt="Payment receipt submitted by ISP applicant" className="max-h-[78vh] max-w-full rounded-lg object-contain" /></div>
            <div className="border-t border-[#1B2430] px-5 py-3 text-xs text-slate-500">Review the transaction details against your bank record before approving.</div>
          </div>
        </div>
      )}
    </main>
  );
}

function SidebarButton({ active, icon, label, badge, onClick }: { active: boolean; icon: React.ReactNode; label: string; badge?: number; onClick: () => void }) {
  return <button onClick={onClick} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${active ? "bg-blue-500/10 text-blue-300 ring-1 ring-blue-500/10" : "text-slate-400 hover:bg-white/[0.04] hover:text-white"}`}>{icon}<span className="flex-1 text-left">{label}</span>{badge ? <span className="rounded-full bg-blue-500/15 px-2 py-0.5 text-[11px] font-semibold text-blue-300">{badge}</span> : null}</button>;
}

function MobileTab({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return <button onClick={onClick} className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-medium ${active ? "bg-blue-500/10 text-blue-300" : "text-slate-500"}`}>{label}</button>;
}

function StatCard({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: string; tone: "blue" | "emerald" | "slate" }) {
  const styles = tone === "blue" ? "border-blue-500/15 bg-blue-500/[0.04] text-blue-300" : tone === "emerald" ? "border-emerald-500/15 bg-emerald-500/[0.04] text-emerald-300" : "border-[#1B2430] bg-[#0D1117] text-slate-300";
  return <div className={`rounded-2xl border p-5 ${styles}`}><div className="flex items-center justify-between"><span className="text-current opacity-80">{icon}</span><span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">Nexora</span></div><p className="mt-5 text-xs text-slate-500">{label}</p><p className="mt-1 text-lg font-semibold text-white">{value}</p></div>;
}

function QueueRow({ item, onReceipt, onApprove, busy }: { item: Registration; onReceipt: () => void; onApprove: () => void; busy: boolean }) {
  return <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><div className="flex items-center gap-2"><p className="truncate font-medium">{item.company_name}</p><span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-300">Pending</span></div><p className="mt-1 truncate text-sm text-slate-500">{item.owner_name} · {item.owner_email}</p><p className="mt-2 text-xs text-slate-600">{item.organization_code} · Rs. {item.amount_due}</p></div><div className="flex shrink-0 items-center gap-2"><button onClick={onReceipt} className="flex h-9 items-center gap-2 rounded-lg border border-[#263142] px-3 text-xs text-slate-300 hover:bg-white/[0.04]"><Eye className="h-3.5 w-3.5" /> Receipt</button><button onClick={onApprove} disabled={busy} className="flex h-9 items-center gap-2 rounded-lg bg-emerald-600 px-3 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"><Check className="h-3.5 w-3.5" /> Approve</button></div></div>;
}

function ReviewCard({ item, busy, onReceipt, onApprove, onReject }: { item: Registration; busy: boolean; onReceipt: () => void; onApprove: () => void; onReject: () => void }) {
  return <article className="rounded-2xl border border-[#1B2430] bg-[#0D1117] p-5 sm:p-6"><div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between"><div className="grid min-w-0 flex-1 gap-5 sm:grid-cols-2 xl:grid-cols-4"><Detail label="ISP / Company" value={item.company_name} icon={<Building2 className="h-4 w-4" />} /><Detail label="Owner" value={item.owner_name} icon={<Mail className="h-4 w-4" />} sub={item.owner_email} /><Detail label="Organization code" value={item.organization_code} icon={<FileText className="h-4 w-4" />} /><Detail label="Amount due" value={`Rs. ${item.amount_due}`} icon={<CreditCard className="h-4 w-4" />} /></div><div className="flex flex-wrap items-center gap-2 border-t border-[#1B2430] pt-4 xl:border-0 xl:pt-0"><button onClick={onReceipt} disabled={!item.receipt_url} className="flex h-10 items-center gap-2 rounded-xl border border-[#263142] px-4 text-sm text-slate-300 hover:bg-white/[0.04] disabled:cursor-not-allowed disabled:opacity-40"><Eye className="h-4 w-4" /> View receipt</button><button onClick={onReject} disabled={busy} className="flex h-10 items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/[0.05] px-4 text-sm font-medium text-red-300 hover:bg-red-500/10 disabled:opacity-50"><XCircle className="h-4 w-4" /> Reject</button><button onClick={onApprove} disabled={busy} className="flex h-10 items-center gap-2 rounded-xl bg-emerald-600 px-5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Approve & activate</button></div></div></article>;
}

function Detail({ label, value, sub, icon }: { label: string; value: string; sub?: string; icon: React.ReactNode }) {
  return <div className="min-w-0"><div className="flex items-center gap-2 text-xs text-slate-500">{icon}{label}</div><p className="mt-2 truncate font-medium text-slate-100">{value}</p>{sub ? <p className="mt-0.5 truncate text-xs text-slate-500">{sub}</p> : null}</div>;
}

function InfoLine({ label, value, copyable, onCopy }: { label: string; value: string; copyable?: boolean; onCopy?: () => void }) {
  return <div className="flex items-start justify-between gap-4 border-b border-[#1B2430] pb-3 last:border-0 last:pb-0"><div><p className="text-xs text-slate-500">{label}</p><p className="mt-1 break-all text-sm font-medium text-slate-200">{value}</p></div>{copyable && value !== "Not configured" ? <button onClick={onCopy} className="rounded-lg p-1.5 text-slate-500 hover:bg-white/[0.04] hover:text-white"><Copy className="h-3.5 w-3.5" /></button> : null}</div>;
}

function Field({ label, value, onChange, placeholder, type = "text", required }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; type?: string; required?: boolean }) {
  return <div><label className="mb-2 block text-sm font-medium text-slate-300">{label}{required ? <span className="ml-1 text-blue-400">*</span> : null}</label><input required={required} type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="h-11 w-full rounded-xl border border-[#263142] bg-[#101720] px-3.5 text-sm text-white outline-none placeholder:text-slate-600 focus:border-blue-500/50" /></div>;
}

function ChecklistItem({ label, complete }: { label: string; complete: boolean }) {
  return <div className="flex items-center gap-3 text-sm"><span className={`flex h-5 w-5 items-center justify-center rounded-full ${complete ? "bg-emerald-500/15 text-emerald-300" : "bg-slate-500/10 text-slate-600"}`}>{complete ? <Check className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}</span><span className={complete ? "text-slate-300" : "text-slate-500"}>{label}</span></div>;
}

function StatusPill({ active }: { active: boolean }) {
  return <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${active ? "bg-emerald-500/10 text-emerald-300" : "bg-amber-500/10 text-amber-300"}`}>{active ? "Configured" : "Incomplete"}</span>;
}

function EmptyState({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return <div className="flex min-h-64 flex-col items-center justify-center px-6 text-center"><div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/[0.04] text-slate-500">{icon}</div><h3 className="mt-4 font-medium text-slate-200">{title}</h3><p className="mt-1 max-w-sm text-sm text-slate-600">{description}</p></div>;
}
