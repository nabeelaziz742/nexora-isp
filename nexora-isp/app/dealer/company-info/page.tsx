"use client";

import { useCallback, useEffect, useState } from "react";
import { Building2, Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerCompanyInfo } from "@/services/dealer-portal.service";

const inputClass =
  "mt-1 h-10 w-full rounded-lg border border-[#263142] bg-[#070B12] px-3 text-sm text-white disabled:cursor-not-allowed disabled:opacity-60 focus:border-blue-500 focus:outline-none";

export default function DealerCompanyInfoPage() {
  const [info, setInfo] = useState<DealerCompanyInfo | null>(null);
  const [form, setForm] = useState({
    company_name: "",
    phone: "",
    alternate_phone: "",
    email: "",
    address_line: "",
    city: "",
    area: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await dealerPortalService.getCompanyInfo();
      setInfo(res);
      setForm({
        company_name: res.company_name || "",
        phone: res.phone || "",
        alternate_phone: res.alternate_phone || "",
        email: res.email || "",
        address_line: res.address_line || "",
        city: res.city || "",
        area: res.area || "",
      });
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load company info.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    if (!info?.can_edit) return;
    setSaving(true);
    try {
      const updated = await dealerPortalService.updateCompanyInfo(form);
      setInfo(updated);
      toast.success("Company contact details updated.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to save company info.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="mb-4 flex items-center gap-2.5">
        <Building2 className="h-5 w-5 text-blue-400" />
        <div>
          <h1 className="text-xl font-bold text-white">Company Info</h1>
          <p className="text-sm text-slate-400">
            Your shop / office contact details. Commission rates and ISP settings stay locked.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
        </div>
      ) : info ? (
        <form onSubmit={handleSave} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-[#1C2431] pb-3 text-xs text-slate-400">
            <span>
              Dealer: <strong className="text-white">{info.name}</strong> ({info.dealer_code})
            </span>
            {!info.can_edit && (
              <span className="rounded bg-amber-500/15 px-2 py-0.5 text-amber-300">
                Read-only (ask your dealer for edit permission)
              </span>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-xs text-slate-400">
              Company / Shop Name
              <input
                disabled={!info.can_edit}
                value={form.company_name}
                onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
                className={inputClass}
              />
            </label>
            <label className="text-xs text-slate-400">
              Email
              <input
                type="email"
                disabled={!info.can_edit}
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className={inputClass}
              />
            </label>
            <label className="text-xs text-slate-400">
              Phone *
              <input
                disabled={!info.can_edit}
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                className={inputClass}
              />
            </label>
            <label className="text-xs text-slate-400">
              Alternate Phone
              <input
                disabled={!info.can_edit}
                value={form.alternate_phone}
                onChange={(e) => setForm((f) => ({ ...f, alternate_phone: e.target.value }))}
                className={inputClass}
              />
            </label>
            <label className="text-xs text-slate-400 sm:col-span-2">
              Shop / Office Address *
              <input
                disabled={!info.can_edit}
                value={form.address_line}
                onChange={(e) => setForm((f) => ({ ...f, address_line: e.target.value }))}
                className={inputClass}
              />
            </label>
            <label className="text-xs text-slate-400">
              City *
              <input
                disabled={!info.can_edit}
                value={form.city}
                onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
                className={inputClass}
              />
            </label>
            <label className="text-xs text-slate-400">
              Area
              <input
                disabled={!info.can_edit}
                value={form.area}
                onChange={(e) => setForm((f) => ({ ...f, area: e.target.value }))}
                className={inputClass}
              />
            </label>
          </div>

          {info.can_edit && (
            <div className="mt-5 flex justify-end">
              <button
                type="submit"
                disabled={saving || !form.phone.trim() || !form.address_line.trim() || !form.city.trim()}
                className="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-600"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save Changes
              </button>
            </div>
          )}
        </form>
      ) : null}
    </>
  );
}
