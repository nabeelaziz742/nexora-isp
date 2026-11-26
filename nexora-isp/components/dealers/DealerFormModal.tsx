"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, KeyRound, Loader2, MessageCircle, Plus, Trash2, X } from "lucide-react";

import { ApiError } from "@/services/api-error";
import {
  dealersService,
  type CommissionType,
  type DealerCreatePayload,
  type DealerItem,
} from "@/services/dealers.service";

const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none";
const labelClass = "mb-1 block text-xs font-medium text-slate-300";

// Starting rows when a dealer is switched to monthly pay: the ISP fills in the amounts.
const SUGGESTED_SLAB_USERS = [200, 500, 1000, 2000, 5000, 10000];

const PAY_TYPES: { value: CommissionType; title: string; hint: string }[] = [
  { value: "MONTHLY_SLAB", title: "Monthly fixed", hint: "Fixed amount by active users (slabs)" },
  { value: "PERCENTAGE", title: "Percentage", hint: "% of money collected" },
  { value: "FLAT_PER_USER", title: "Per user", hint: "Fixed PKR for each active user" },
];

type SlabRow = { users: string; amount: string };


type FormState = {
  name: string;
  company_name: string;
  cnic: string;
  phone: string;
  alternate_phone: string;
  email: string;
  address_line: string;
  city: string;
  area: string;
  joining_date: string;
  notes: string;
  commission_type: CommissionType;
  commission_rate_percentage: string;
  parent_dealer: string;
  slabs: SlabRow[];
};

function initialState(dealer?: DealerItem | null): FormState {
  return {
    name: dealer?.name ?? "",
    company_name: dealer?.company_name ?? "",
    cnic: dealer?.cnic ?? "",
    phone: dealer?.phone ?? "",
    alternate_phone: dealer?.alternate_phone ?? "",
    email: dealer?.email ?? "",
    address_line: dealer?.address_line ?? "",
    city: dealer?.city ?? "",
    area: dealer?.area ?? "",
    joining_date: dealer?.joining_date ?? new Date().toISOString().split("T")[0],
    notes: dealer?.notes ?? "",
    commission_type: dealer?.commission_type ?? "MONTHLY_SLAB",
    commission_rate_percentage: dealer ? String(Number(dealer.commission_rate_percentage)) : "0",
    parent_dealer: dealer?.parent_dealer ?? "",
    slabs: dealer?.payout_slabs?.length
      ? dealer.payout_slabs.map((slab) => ({ users: String(slab.min_active_users), amount: String(Number(slab.monthly_amount)) }))
      : SUGGESTED_SLAB_USERS.map((users) => ({ users: String(users), amount: "" })),
  };
}

// Register a new dealer, or edit one (details, how they are paid, and whose sub dealer they are).
export default function DealerFormModal({
  dealer,
  onClose,
  onSaved,
}: {
  dealer?: DealerItem | null;
  onClose: () => void;
  onSaved: (dealer: DealerItem) => void;
}) {
  const editing = Boolean(dealer);
  const [form, setForm] = useState<FormState>(() => initialState(dealer));
  const [dealers, setDealers] = useState<DealerItem[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  // New dealers get their sign-in in the same step; they change the password later themselves.
  const [giveLogin, setGiveLogin] = useState(true);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginEmailTouched, setLoginEmailTouched] = useState(false);
  const [created, setCreated] = useState<{ dealer: DealerItem; sentTo: string } | null>(null);

  useEffect(() => {
    dealersService.getDealers().then(setDealers).catch(() => setDealers([]));
  }, []);

  // A parent must be a top-level dealer other than this one.
  const parentOptions = useMemo(
    () => dealers.filter((d) => d.id !== dealer?.id && !d.parent_dealer),
    [dealers, dealer?.id],
  );
  const hasSubDealers = (dealer?.sub_dealers_count ?? 0) > 0;
  const isSubDealer = Boolean(form.parent_dealer);
  const parentName = parentOptions.find((d) => d.id === form.parent_dealer)?.name ?? dealer?.parent_dealer_name ?? "";

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }));
  const setSlab = (index: number, key: keyof SlabRow, value: string) =>
    setForm((f) => ({ ...f, slabs: f.slabs.map((row, i) => (i === index ? { ...row, [key]: value } : row)) }));

  const filledSlabs = form.slabs
    .filter((row) => Number(row.users) > 0 && row.amount.trim() !== "")
    .map((row) => ({ min_active_users: Math.round(Number(row.users)), monthly_amount: row.amount }))
    .sort((a, b) => a.min_active_users - b.min_active_users);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    if (!isSubDealer && form.commission_type === "MONTHLY_SLAB" && filledSlabs.length === 0) {
      setError("Enter the monthly amount for at least one slab.");
      return;
    }
    const payload: DealerCreatePayload = {
      name: form.name.trim(),
      company_name: form.company_name.trim(),
      cnic: form.cnic.trim(),
      phone: form.phone.trim(),
      alternate_phone: form.alternate_phone.trim(),
      email: form.email.trim(),
      address_line: form.address_line.trim(),
      city: form.city.trim(),
      area: form.area.trim(),
      joining_date: form.joining_date,
      notes: form.notes,
      parent_dealer: form.parent_dealer || null,
      commission_type: form.commission_type,
      commission_rate_percentage: form.commission_type === "MONTHLY_SLAB" ? 0 : Number(form.commission_rate_percentage) || 0,
    };
    if (form.commission_type === "MONTHLY_SLAB") payload.payout_slabs = filledSlabs;
    const portalEmail = (loginEmailTouched ? loginEmail : form.email).trim().toLowerCase();
    if (!editing && giveLogin) {
      if (!portalEmail) {
        setError("Enter the email the dealer will sign in with.");
        return;
      }
      payload.portal_email = portalEmail;
    }

    setSaving(true);
    try {
      const saved = editing
        ? await dealersService.updateDealer(dealer!.id, payload)
        : await dealersService.createDealer({ ...payload, status: "ACTIVE" });
      if (!editing && giveLogin) {
        const sentTo = (saved as { login_sent_to?: string | null }).login_sent_to;
        setCreated({ dealer: saved, sentTo: sentTo || portalEmail });
      } else {
        onSaved(saved);
      }
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : "Unable to save the dealer.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/80 backdrop-blur-sm sm:items-center sm:p-4">
      <div className="max-h-[95vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl border border-slate-800 bg-slate-900 p-4 shadow-2xl sm:max-h-[90vh] sm:rounded-2xl sm:p-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-lg font-bold text-white">{editing ? `Edit ${dealer!.name}` : "Register Dealer / Sub Dealer"}</h3>
            <p className="text-xs text-slate-400">
              {editing ? `${dealer!.dealer_code} · contact details, payment and parent dealer` : "Partner profile and how they are paid"}
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {created ? (
          <div className="mt-4 space-y-4">
            <div className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                {created.dealer.name} was added. Their login email and password were sent by {created.sentTo}.
                They can sign in now and change the password from their panel.
              </span>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => onSaved(created.dealer)}
                className="rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
        <form onSubmit={submit} className="mt-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass}>Contact Person Name <span className="text-rose-400">*</span></label>
              <input required value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Naveed Ahmed" className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Company / Network Name</label>
              <input value={form.company_name} onChange={(e) => set("company_name", e.target.value)} placeholder="e.g. Naveed Broadband" className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Phone <span className="text-rose-400">*</span></label>
              <input required inputMode="tel" value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="03001234567" className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Alternate Phone</label>
              <input inputMode="tel" value={form.alternate_phone} onChange={(e) => set("alternate_phone", e.target.value)} placeholder="03219876543" className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Email</label>
              <input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="dealer@example.com" className={inputClass} />
              {editing && (
                <p className="mt-1 text-[11px] text-slate-500">Contact email. The portal sign-in email and password are under &quot;Portal Login&quot;.</p>
              )}
            </div>
            <div>
              <label className={labelClass}>CNIC / Registration #</label>
              <input value={form.cnic} onChange={(e) => set("cnic", e.target.value)} placeholder="37405-XXXXXXX-X" className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>City</label>
              <input value={form.city} onChange={(e) => set("city", e.target.value)} placeholder="e.g. Rawalpindi" className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Area</label>
              <input value={form.area} onChange={(e) => set("area", e.target.value)} placeholder="e.g. Satellite Town" className={inputClass} />
            </div>
            <div className="sm:col-span-2">
              <label className={labelClass}>Address</label>
              <input value={form.address_line} onChange={(e) => set("address_line", e.target.value)} placeholder="Shop / street" className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Joining Date <span className="text-rose-400">*</span></label>
              <input type="date" required value={form.joining_date} onChange={(e) => set("joining_date", e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Works under (sub dealer of)</label>
              <select
                value={form.parent_dealer}
                onChange={(e) => set("parent_dealer", e.target.value)}
                disabled={hasSubDealers}
                className={`${inputClass} disabled:opacity-50`}
              >
                <option value="">No one — reports to the ISP</option>
                {parentOptions.map((d) => (
                  <option key={d.id} value={d.id}>{d.name} ({d.dealer_code})</option>
                ))}
              </select>
              {hasSubDealers && (
                <p className="mt-1 text-[11px] text-slate-500">This dealer has sub dealers, so they cannot work under another dealer.</p>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
            <p className="mb-2 text-xs font-semibold text-slate-300">How the ISP pays this dealer</p>
            {isSubDealer ? (
              <p className="text-sm text-slate-400">
                Sub dealers are paid by their dealer{parentName ? ` (${parentName})` : ""}, not by the ISP. Their active
                users count towards {parentName || "the dealer"}&apos;s monthly slab.
              </p>
            ) : (
              <>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {PAY_TYPES.map((type) => (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => set("commission_type", type.value)}
                      className={`rounded-lg border px-3 py-2.5 text-left ${
                        form.commission_type === type.value
                          ? "border-emerald-500 bg-emerald-500/10"
                          : "border-slate-700 hover:border-slate-500"
                      }`}
                    >
                      <span className="block text-sm font-semibold text-white">{type.title}</span>
                      <span className="block text-[11px] text-slate-400">{type.hint}</span>
                    </button>
                  ))}
                </div>

                {form.commission_type === "MONTHLY_SLAB" ? (
                  <div className="mt-3">
                    <p className="mb-2 text-[11px] text-slate-400">
                      The dealer gets the amount of the highest slab reached by their active users (their sub dealers&apos;
                      users included). Below the first slab they get nothing. Leave an amount empty to skip that slab.
                    </p>
                    <div className="grid grid-cols-[1fr_1fr_auto] gap-2 text-[11px] font-medium text-slate-400">
                      <span>Active users (at least)</span>
                      <span>Monthly amount (PKR)</span>
                      <span className="w-8" />
                    </div>
                    <div className="mt-1 space-y-2">
                      {form.slabs.map((row, index) => (
                        <div key={index} className="grid grid-cols-[1fr_1fr_auto] items-center gap-2">
                          <input
                            type="number"
                            min={1}
                            inputMode="numeric"
                            value={row.users}
                            onChange={(e) => setSlab(index, "users", e.target.value)}
                            aria-label="Active users (at least)"
                            className={`${inputClass} min-w-0`}
                          />
                          <input
                            type="number"
                            min={0}
                            inputMode="numeric"
                            value={row.amount}
                            onChange={(e) => setSlab(index, "amount", e.target.value)}
                            placeholder="e.g. 20000"
                            aria-label="Monthly amount (PKR)"
                            className={`${inputClass} min-w-0`}
                          />
                          <button
                            type="button"
                            onClick={() => setForm((f) => ({ ...f, slabs: f.slabs.filter((_, i) => i !== index) }))}
                            className="w-8 rounded-lg p-2 text-slate-500 hover:bg-slate-800 hover:text-rose-400"
                            aria-label="Remove slab"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, slabs: [...f.slabs, { users: "", amount: "" }] }))}
                      className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-emerald-400 hover:text-emerald-300"
                    >
                      <Plus className="h-3.5 w-3.5" /> Add slab
                    </button>
                  </div>
                ) : (
                  <div className="mt-3 max-w-xs">
                    <label className={labelClass}>
                      {form.commission_type === "PERCENTAGE" ? "Percentage of collections (%)" : "PKR per active user"}
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min={0}
                      max={999.99}
                      required
                      value={form.commission_rate_percentage}
                      onChange={(e) => set("commission_rate_percentage", e.target.value)}
                      className={inputClass}
                    />
                  </div>
                )}
              </>
            )}
          </div>

          {!editing && (
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
              <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-slate-300">
                <input
                  type="checkbox"
                  checked={giveLogin}
                  onChange={(e) => setGiveLogin(e.target.checked)}
                  className="h-4 w-4 accent-emerald-600"
                />
                <KeyRound className="h-3.5 w-3.5 text-emerald-400" />
                Give the dealer a login now
              </label>
              {giveLogin && (
                <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className={labelClass}>Login email <span className="text-rose-400">*</span></label>
                    <input
                      type="email"
                      value={loginEmailTouched ? loginEmail : form.email}
                      onChange={(e) => {
                        setLoginEmailTouched(true);
                        setLoginEmail(e.target.value);
                      }}
                      placeholder="dealer@example.com"
                      className={inputClass}
                    />
                  </div>
                  <div className="flex items-start gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-2.5 text-[11px] text-slate-300">
                    <MessageCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                    <span>
                      The system makes the password and emails it to the login email above, and also sends it on
                      WhatsApp when your WhatsApp is connected. Nobody at the ISP sees it; the dealer can change it
                      from their panel.
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          <div>
            <label className={labelClass}>Agreement Notes</label>
            <textarea rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} placeholder="Terms, coverage, other details..." className={inputClass} />
          </div>

          <div className="flex flex-col-reverse gap-2 border-t border-slate-800 pt-4 sm:flex-row sm:justify-end sm:gap-3">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white">
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {editing ? "Save Changes" : "Register Dealer"}
            </button>
          </div>
        </form>
        )}
      </div>
    </div>
  );
}
