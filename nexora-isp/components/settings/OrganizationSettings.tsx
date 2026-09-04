"use client";

import { useEffect, useState } from "react";
import { Building2, CheckCircle2, ShieldCheck } from "lucide-react";

import { companyService, CompanyProfile } from "@/services/company.service";
import { useToast } from "@/hooks/useToast";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { SkeletonCard } from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";
import { ApiError } from "@/services/api-error";

export default function OrganizationSettings() {
  const { success, error: toastError } = useToast();

  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [role, setRole] = useState<string>("");

  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
    address: "",
    city: "",
    timezone: "",
    currency: "",
  });

  async function loadProfile() {
    try {
      setLoading(true);
      setError(null);
      const data = await companyService.getProfile();
      setProfile(data);
      setForm({
        name: data.name || "",
        phone: data.phone || "",
        email: data.email || "",
        address: data.address || "",
        city: data.city || "",
        timezone: data.timezone || "UTC",
        currency: data.currency || "PKR",
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to load company organization profile.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    try {
      const storedRole = window.localStorage.getItem("nexora_role") || "";
      setRole(storedRole);
    } catch {
      setRole("");
    }
    loadProfile();
  }, []);

  const isOwner = role === "OWNER";

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!isOwner) {
      toastError("Only organization owners can modify company settings.");
      return;
    }

    if (!form.name.trim()) {
      toastError("Company name cannot be empty.");
      return;
    }

    setSaving(true);
    try {
      const updated = await companyService.updateProfile(form);
      setProfile(updated);
      success("Company organization profile saved successfully.");
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Failed to update organization profile.";
      toastError(msg);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <SkeletonCard className="min-h-[300px]" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadProfile} />;
  }

  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="flex flex-col gap-2 border-b border-[#202938] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-100">
              ISP Company & Organization Profile
            </h2>
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-semibold text-emerald-400">
              <CheckCircle2 className="h-2.5 w-2.5" />
              Active Tenant
            </span>
          </div>

          <p className="mt-1 text-xs text-slate-500">
            Tenant identity, contact details, regional operating city, timezone, and currency.
          </p>
        </div>

        <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
          <Building2 className="h-3.5 w-3.5 text-blue-400" />
          <span>Code: {profile?.code}</span>
        </div>
      </div>

      <form onSubmit={handleSave}>
        <div className="grid gap-5 p-5 md:grid-cols-2 xl:grid-cols-3">
          {/* Organization Name */}
          <label className="block">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
              Company / ISP Name *
            </span>
            <input
              type="text"
              disabled={!isOwner}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="mt-2 h-10 w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 text-xs text-slate-200 outline-none transition focus:border-blue-500 disabled:opacity-50"
            />
          </label>

          {/* Organization Code (Immutable) */}
          <label className="block">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
              Organization Code (Tenant ID)
            </span>
            <input
              type="text"
              disabled
              value={profile?.code || ""}
              className="mt-2 h-10 w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 text-xs uppercase font-mono text-slate-400 outline-none cursor-not-allowed opacity-60"
            />
          </label>

          {/* Contact Phone */}
          <label className="block">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
              Support / Helpline Phone
            </span>
            <input
              type="text"
              disabled={!isOwner}
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="e.g. +92 300 1234567"
              className="mt-2 h-10 w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 text-xs text-slate-200 outline-none transition focus:border-blue-500 disabled:opacity-50"
            />
          </label>

          {/* Contact Email */}
          <label className="block">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
              Operations Email
            </span>
            <input
              type="email"
              disabled={!isOwner}
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="e.g. support@isp.com"
              className="mt-2 h-10 w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 text-xs text-slate-200 outline-none transition focus:border-blue-500 disabled:opacity-50"
            />
          </label>

          {/* Operating City */}
          <label className="block">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
              Primary Operating City
            </span>
            <input
              type="text"
              disabled={!isOwner}
              value={form.city}
              onChange={(e) => setForm({ ...form, city: e.target.value })}
              placeholder="e.g. Lahore, Islamabad"
              className="mt-2 h-10 w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 text-xs text-slate-200 outline-none transition focus:border-blue-500 disabled:opacity-50"
            />
          </label>

          {/* Office Address */}
          <label className="block">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
              Head Office Address
            </span>
            <input
              type="text"
              disabled={!isOwner}
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
              placeholder="e.g. Building 12, Main Boulevard"
              className="mt-2 h-10 w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 text-xs text-slate-200 outline-none transition focus:border-blue-500 disabled:opacity-50"
            />
          </label>

          {/* Timezone */}
          <label className="block">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
              System Timezone
            </span>
            <select
              disabled={!isOwner}
              value={form.timezone}
              onChange={(e) => setForm({ ...form, timezone: e.target.value })}
              className="mt-2 h-10 w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 text-xs text-slate-200 outline-none transition focus:border-blue-500 disabled:opacity-50"
            >
              <option value="Asia/Karachi">Asia/Karachi (PKT +05:00)</option>
              <option value="Asia/Dubai">Asia/Dubai (GST +04:00)</option>
              <option value="UTC">UTC (+00:00)</option>
            </select>
          </label>

          {/* Currency */}
          <label className="block">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
              Billing Currency
            </span>
            <select
              disabled={!isOwner}
              value={form.currency}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
              className="mt-2 h-10 w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 text-xs text-slate-200 outline-none transition focus:border-blue-500 disabled:opacity-50"
            >
              <option value="PKR">PKR — Pakistani Rupee (Rs.)</option>
              <option value="USD">USD — US Dollar ($)</option>
              <option value="AED">AED — UAE Dirham (AED)</option>
            </select>
          </label>
        </div>

        <div className="flex items-center justify-between border-t border-[#202938] px-5 py-4">
          <div className="text-[11px] text-slate-500">
            {!isOwner && (
              <span>Only organization owners have permission to edit company profile.</span>
            )}
          </div>

          {isOwner && (
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-md transition hover:bg-blue-500 disabled:opacity-50"
            >
              {saving && <LoadingSpinner size="xs" tone="white" />}
              Save Organization Settings
            </button>
          )}
        </div>
      </form>
    </section>
  );
}