"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle2, Loader2, RadioTower, Wifi } from "lucide-react";

import { ApiError } from "@/services/api-error";
import {
  getPublicApplyForm,
  submitPublicInquiry,
  type PublicApplyForm,
} from "@/services/public-inquiry.service";

const emptyForm = {
  full_name: "",
  phone: "",
  email: "",
  address_line: "",
  city: "",
  area: "",
  preferred_package: "",
  connection_type: "FIBER",
  notes: "",
  website: "",
};

const inputClass =
  "w-full rounded-lg border border-[#263142] bg-[#101720] px-4 py-3 text-white outline-none focus:border-blue-500";

export default function PublicApplyPage() {
  const params = useParams<{ code: string }>();
  const code = (params?.code as string) || "";

  const [details, setDetails] = useState<PublicApplyForm | null>(null);
  const [loadError, setLoadError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [reference, setReference] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;
    getPublicApplyForm(code)
      .then((data) => {
        setDetails(data);
        setForm((current) => ({ ...current, city: current.city || data.organization.city || "" }));
      })
      .catch((err) =>
        setLoadError(err instanceof ApiError ? err.message : "This ISP link is not available."),
      );
  }, [code]);

  function update(field: keyof typeof emptyForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      setSubmitting(true);
      const result = await submitPublicInquiry(code, {
        ...form,
        preferred_package: form.preferred_package || null,
      });
      setReference(result.reference ?? "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to submit your request.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loadError) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070A0F] px-4 text-white">
        <div className="max-w-md rounded-2xl border border-[#1C2431] bg-[#0D1117] p-8 text-center">
          <RadioTower className="mx-auto h-8 w-8 text-slate-500" />
          <h1 className="mt-4 text-lg font-semibold">Link not available</h1>
          <p className="mt-2 text-sm text-slate-400">{loadError}</p>
        </div>
      </main>
    );
  }

  if (!details) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070A0F] text-white">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </main>
    );
  }

  if (reference !== null) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070A0F] px-4 text-white">
        <div className="max-w-md rounded-2xl border border-[#1C2431] bg-[#0D1117] p-8 text-center">
          <CheckCircle2 className="mx-auto h-10 w-10 text-green-400" />
          <h1 className="mt-4 text-xl font-semibold">Request received</h1>
          <p className="mt-2 text-sm text-slate-400">
            Thank you. {details.organization.name} will contact you shortly
            {details.organization.phone ? ` from ${details.organization.phone}` : ""}.
          </p>
          {reference && (
            <p className="mt-4 rounded-lg border border-[#263142] bg-[#101720] px-4 py-2 font-mono text-sm text-slate-300">
              Reference: {reference}
            </p>
          )}
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#070A0F] px-4 py-10 text-white sm:px-6">
      <div className="mx-auto max-w-2xl rounded-2xl border border-[#1C2431] bg-[#0D1117] p-6 shadow-2xl sm:p-8">
        <div className="mb-8 flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-600">
            <Wifi className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold sm:text-2xl">{details.organization.name}</h1>
            <p className="text-sm text-slate-400">Apply for a new internet connection</p>
          </div>
        </div>

        {details.packages.length > 0 && (
          <div className="mb-8">
            <p className="mb-3 text-sm text-slate-300">Choose a package</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {details.packages.map((pkg) => {
                const selected = form.preferred_package === pkg.id;
                return (
                  <button
                    key={pkg.id}
                    type="button"
                    onClick={() => update("preferred_package", selected ? "" : pkg.id)}
                    className={`rounded-lg border p-4 text-left transition ${
                      selected
                        ? "border-blue-500 bg-blue-500/10"
                        : "border-[#263142] bg-[#101720] hover:border-slate-500"
                    }`}
                  >
                    <p className="font-semibold">{pkg.name}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {pkg.download_speed_mbps} Mbps down / {pkg.upload_speed_mbps} Mbps up
                    </p>
                    <p className="mt-2 font-mono text-sm text-green-400">
                      Rs. {Number(pkg.monthly_price).toLocaleString()} / month
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <form onSubmit={submit} className="grid gap-5 md:grid-cols-2">
          <label className="md:col-span-2">
            <span className="mb-2 block text-sm text-slate-300">Full Name *</span>
            <input required value={form.full_name} onChange={(e) => update("full_name", e.target.value)} className={inputClass} />
          </label>

          <label>
            <span className="mb-2 block text-sm text-slate-300">Mobile Number *</span>
            <input
              required
              type="tel"
              inputMode="tel"
              placeholder="03001234567"
              value={form.phone}
              onChange={(e) => update("phone", e.target.value)}
              className={inputClass}
            />
          </label>

          <label>
            <span className="mb-2 block text-sm text-slate-300">Email</span>
            <input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} className={inputClass} />
          </label>

          <label className="md:col-span-2">
            <span className="mb-2 block text-sm text-slate-300">Address *</span>
            <input
              required
              placeholder="House / street / block"
              value={form.address_line}
              onChange={(e) => update("address_line", e.target.value)}
              className={inputClass}
            />
          </label>

          <label>
            <span className="mb-2 block text-sm text-slate-300">Area</span>
            <input value={form.area} onChange={(e) => update("area", e.target.value)} className={inputClass} />
          </label>

          <label>
            <span className="mb-2 block text-sm text-slate-300">City *</span>
            <input required value={form.city} onChange={(e) => update("city", e.target.value)} className={inputClass} />
          </label>

          <label className="md:col-span-2">
            <span className="mb-2 block text-sm text-slate-300">Connection Type</span>
            <select value={form.connection_type} onChange={(e) => update("connection_type", e.target.value)} className={inputClass}>
              {details.connection_types.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </label>

          <label className="md:col-span-2">
            <span className="mb-2 block text-sm text-slate-300">Anything else we should know?</span>
            <textarea rows={3} value={form.notes} onChange={(e) => update("notes", e.target.value)} className={inputClass} />
          </label>

          {/* Honeypot for bots: hidden from people and screen readers. */}
          <input
            type="text"
            name="website"
            tabIndex={-1}
            autoComplete="off"
            aria-hidden="true"
            value={form.website}
            onChange={(e) => update("website", e.target.value)}
            className="hidden"
          />

          {error && (
            <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300 md:col-span-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 font-semibold hover:bg-blue-500 disabled:opacity-60 md:col-span-2"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Submit Request
          </button>
        </form>
      </div>
    </main>
  );
}
