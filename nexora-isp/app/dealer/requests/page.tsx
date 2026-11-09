"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Send, UserPlus } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/services/api-error";
import {
  dealerPortalService,
  type DealerRequestPayload,
  type DealerRequestRow,
} from "@/services/dealer-portal.service";

const inputClass =
  "mt-1 h-11 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none";

const EMPTY: DealerRequestPayload = {
  full_name: "",
  phone: "",
  alternate_phone: "",
  cnic: "",
  address_line: "",
  city: "",
  area: "",
  preferred_package: "",
  notes: "",
};

function statusClass(status: string) {
  if (status === "CONVERTED") return "text-emerald-400";
  if (["LOST", "CANCELLED", "NOT_FEASIBLE"].includes(status)) return "text-slate-500";
  return "text-amber-400";
}

export default function DealerRequestsPage() {
  const [rows, setRows] = useState<DealerRequestRow[]>([]);
  const [packages, setPackages] = useState<{ id: string; name: string; monthly_price: string }[]>([]);
  const [form, setForm] = useState<DealerRequestPayload>(EMPTY);
  const [defaultCity, setDefaultCity] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await dealerPortalService.getRequests();
      setRows(data.results);
      setPackages(data.packages);
      setDefaultCity(data.default_city);
      setForm((current) => (current.city ? current : { ...current, city: data.default_city }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load your requests.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const set = <K extends keyof DealerRequestPayload>(key: K, value: DealerRequestPayload[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const row = await dealerPortalService.createRequest({
        ...form,
        preferred_package: form.preferred_package || null,
      });
      toast.success(`Sent to the office as ${row.inquiry_number}. They will install the connection.`);
      setForm({ ...EMPTY, city: defaultCity });
      setRows((current) => [row, ...current]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to send the request.");
    } finally {
      setSaving(false);
    }
  }

  const canSubmit = form.full_name.trim() && form.phone.trim() && form.address_line.trim() && form.city.trim() && !saving;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
      <form onSubmit={submit} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
        <div className="flex items-center gap-2">
          <UserPlus className="h-5 w-5 text-blue-400" />
          <h1 className="text-lg font-bold text-white">New customer</h1>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          Send a new connection to the office. They check the area, install it and the customer is added under you.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="text-xs text-slate-400 sm:col-span-2">
            Customer name *
            <input value={form.full_name} onChange={(e) => set("full_name", e.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            Mobile number *
            <input inputMode="tel" value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="03001234567" className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            Other number
            <input inputMode="tel" value={form.alternate_phone} onChange={(e) => set("alternate_phone", e.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-slate-400 sm:col-span-2">
            Address *
            <input value={form.address_line} onChange={(e) => set("address_line", e.target.value)} placeholder="House / street / block" className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            Area
            <input value={form.area} onChange={(e) => set("area", e.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            City *
            <input value={form.city} onChange={(e) => set("city", e.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            CNIC
            <input value={form.cnic} onChange={(e) => set("cnic", e.target.value)} placeholder="35202-1234567-1" className={inputClass} />
          </label>
          <label className="text-xs text-slate-400">
            Package
            <select value={form.preferred_package ?? ""} onChange={(e) => set("preferred_package", e.target.value)} className={inputClass}>
              <option value="">Not decided</option>
              {packages.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} · PKR {Number(p.monthly_price).toLocaleString("en-PK", { maximumFractionDigits: 0 })}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-400 sm:col-span-2">
            Notes for the office
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)} rows={2}
              placeholder="e.g. best time to visit"
              className="mt-1 w-full rounded-lg border border-[#263142] bg-[#070A0F] px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none" />
          </label>
        </div>

        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={!canSubmit}
          className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-500"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Send to Office
        </button>
      </form>

      <section>
        <h2 className="mb-2 text-sm font-semibold text-white">My requests</h2>
        {loading ? (
          <div className="flex justify-center py-10"><Loader2 className="h-5 w-5 animate-spin text-blue-500" /></div>
        ) : rows.length === 0 ? (
          <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-6 text-center text-sm text-slate-500">No requests yet.</div>
        ) : (
          <ul className="divide-y divide-[#1C2431] rounded-xl border border-[#1C2431] bg-[#0D1117]">
            {rows.map((row) => (
              <li key={row.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">{row.full_name}</p>
                  <p className="text-xs text-slate-500">
                    {row.phone}{row.area ? ` · ${row.area}` : ""}{row.package_name ? ` · ${row.package_name}` : ""}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {row.inquiry_number} · {new Date(row.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
                  </p>
                </div>
                <span className={`shrink-0 text-xs font-semibold ${statusClass(row.status)}`}>{row.status_label}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
