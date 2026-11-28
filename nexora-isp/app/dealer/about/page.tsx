"use client";

import { useEffect, useState } from "react";
import { Info, Loader2, Mail, MapPin, Phone } from "lucide-react";

import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerAboutInfo } from "@/services/dealer-portal.service";

export default function DealerAboutPage() {
  const [data, setData] = useState<DealerAboutInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    dealerPortalService
      .getAbout()
      .then((res) => {
        setData(res);
        setError("");
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Unable to load ISP details."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="mb-4 flex items-center gap-2.5">
        <Info className="h-5 w-5 text-blue-400" />
        <div>
          <h1 className="text-xl font-bold text-white">About</h1>
          <p className="text-sm text-slate-400">Your ISP head office contact details.</p>
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
      ) : data ? (
        <div className="space-y-4">
          <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5">
            <h2 className="text-lg font-bold text-white">{data.organization.name}</h2>
            <p className="mt-0.5 text-xs text-slate-500">Dealer Code: {data.dealer_code}</p>
            <div className="mt-4 space-y-2.5 text-sm text-slate-300">
              {data.organization.phone && (
                <div className="flex items-center gap-2">
                  <Phone className="h-4 w-4 text-slate-500" />
                  <span>{data.organization.phone}</span>
                </div>
              )}
              {data.organization.email && (
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-slate-500" />
                  <span>{data.organization.email}</span>
                </div>
              )}
              {(data.organization.address || data.organization.city) && (
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-slate-500" />
                  <span>
                    {[data.organization.address, data.organization.city].filter(Boolean).join(", ")}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] px-5 py-4 text-center text-xs text-slate-400">
            {data.powered_by}
          </div>
        </div>
      ) : null}
    </>
  );
}
