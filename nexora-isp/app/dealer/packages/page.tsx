"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowDown, ArrowUp, Loader2, Package } from "lucide-react";

import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerPackage } from "@/services/dealer-portal.service";

const pkr = (value: string | number) => `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

export default function DealerPackagesPage() {
  const me = useDealerMe();
  const canView = me.is_dealer || me.rights.can_view_packages;

  const [packages, setPackages] = useState<DealerPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setPackages((await dealerPortalService.getPackages()).results);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load packages.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (canView) void load();
  }, [canView, load]);

  if (!canView) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
        You do not have permission to view packages.
      </div>
    );
  }

  return (
    <>
      <div className="mb-4">
        <h1 className="text-xl font-bold text-white">Packages</h1>
        <p className="text-sm text-slate-400">Active internet packages offered by your ISP (read-only).</p>
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-blue-500" /></div>
      ) : packages.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-500">
          <Package className="mx-auto mb-2 h-6 w-6 text-slate-600" />
          No active packages found.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {packages.map((pkg) => (
            <div key={pkg.id} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h2 className="truncate text-base font-bold text-white">{pkg.name}</h2>
                  <p className="font-mono text-xs text-slate-500">{pkg.code}</p>
                </div>
                <p className="shrink-0 text-base font-bold text-emerald-400">{pkr(pkg.monthly_price)}/mo</p>
              </div>
              <div className="mt-3 flex items-center gap-4 text-xs text-slate-300">
                <span className="inline-flex items-center gap-1">
                  <ArrowDown className="h-3.5 w-3.5 text-blue-400" />
                  {pkg.download_speed_mbps} Mbps
                </span>
                <span className="inline-flex items-center gap-1">
                  <ArrowUp className="h-3.5 w-3.5 text-sky-400" />
                  {pkg.upload_speed_mbps} Mbps
                </span>
              </div>
              {pkg.description && <p className="mt-2 text-xs text-slate-500">{pkg.description}</p>}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
