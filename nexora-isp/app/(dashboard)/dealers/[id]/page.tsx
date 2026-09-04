"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  Calendar,
  CheckCircle2,
  CircleDollarSign,
  CreditCard,
  DollarSign,
  MapPin,
  Percent,
  Phone,
  Power,
  Receipt,
  RefreshCw,
  Users,
  Wifi,
} from "lucide-react";

import Skeleton from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";
import { dealersService, type Dealer360Data } from "@/services/dealers.service";

export default function Dealer360Page() {
  const params = useParams();
  const router = useRouter();
  const dealerId = params.id as string;

  const [data, setData] = useState<Dealer360Data | null>(null);
  const [activeTab, setActiveTab] = useState<"customers" | "collections" | "overview">("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await dealersService.getDealer360(dealerId);
      setData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load dealer 360 overview.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (dealerId) {
      loadData();
    }
  }, [dealerId]);

  const handleToggleStatus = async () => {
    if (!data) return;
    setToggling(true);
    try {
      await dealersService.toggleStatus(dealerId);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to toggle status.");
    } finally {
      setToggling(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 pb-12">
        <Skeleton className="h-10 w-48 rounded-lg" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
        </div>
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="py-8">
        <ErrorState message={error || "Dealer not found."} onRetry={loadData} />
      </div>
    );
  }

  const { dealer, metrics, customers, recent_collections } = data;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/dealers")}
            className="rounded-lg border border-slate-800 bg-slate-900/80 p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                {dealer.name}
              </h1>
              <span className="font-mono text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                {dealer.dealer_code}
              </span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium border ${
                  dealer.status === "ACTIVE"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                    : "bg-slate-500/10 text-slate-400 border-slate-500/30"
                }`}
              >
                {dealer.status}
              </span>
            </div>
            {dealer.company_name && (
              <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
                <Building2 className="h-3 w-3" />
                {dealer.company_name} • Partner since {dealer.joining_date}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleToggleStatus}
            disabled={toggling}
            className={`inline-flex items-center gap-2 rounded-lg border px-3.5 py-2 text-xs font-semibold transition ${
              dealer.status === "ACTIVE"
                ? "border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
            }`}
          >
            <Power className="h-3.5 w-3.5" />
            {dealer.status === "ACTIVE" ? "Deactivate Partner" : "Activate Partner"}
          </button>
          <button
            onClick={loadData}
            className="rounded-lg border border-slate-700 bg-slate-800 p-2 text-slate-300 hover:bg-slate-700 hover:text-white transition"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* KPI Metrics Strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <span className="text-xs text-slate-500 block uppercase font-medium">Subscribers</span>
          <p className="mt-1 text-2xl font-bold text-white">{metrics.total_customers}</p>
          <span className="text-[11px] text-emerald-400">{metrics.active_customers} active</span>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <span className="text-xs text-slate-500 block uppercase font-medium">Total Invoiced</span>
          <p className="mt-1 text-xl font-bold text-white">PKR {Number(metrics.total_invoiced).toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <span className="text-xs text-slate-500 block uppercase font-medium">Collections</span>
          <p className="mt-1 text-xl font-bold text-emerald-400">PKR {Number(metrics.total_collected).toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <span className="text-xs text-slate-500 block uppercase font-medium">Outstanding</span>
          <p className="mt-1 text-xl font-bold text-rose-400">PKR {Number(metrics.total_outstanding).toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm sm:col-span-2">
          <span className="text-xs text-slate-500 block uppercase font-medium flex items-center gap-1">
            <Percent className="h-3 w-3 text-amber-400" />
            Accrued Commission ({dealer.commission_type === "PERCENTAGE" ? `${dealer.commission_rate_percentage}%` : `PKR ${dealer.commission_rate_percentage}/sub`})
          </span>
          <p className="mt-1 text-2xl font-bold text-amber-400">PKR {Number(metrics.calculated_commission).toLocaleString()}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 text-sm font-medium">
        <button
          onClick={() => setActiveTab("overview")}
          className={`pb-3 px-4 border-b-2 transition ${
            activeTab === "overview"
              ? "border-emerald-500 text-emerald-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Partner Overview & Agreement
        </button>
        <button
          onClick={() => setActiveTab("customers")}
          className={`pb-3 px-4 border-b-2 transition ${
            activeTab === "customers"
              ? "border-emerald-500 text-emerald-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Assigned Subscribers ({customers.length})
        </button>
        <button
          onClick={() => setActiveTab("collections")}
          className={`pb-3 px-4 border-b-2 transition ${
            activeTab === "collections"
              ? "border-emerald-500 text-emerald-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Recent Collections ({recent_collections.length})
        </button>
      </div>

      {/* TAB CONTENT: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 backdrop-blur-sm shadow-xl space-y-4">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">Partner Information</h2>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-slate-500 block mb-1">Contact Person</span>
                <span className="font-semibold text-white text-sm">{dealer.name}</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-slate-500 block mb-1">Primary Phone</span>
                <span className="font-mono text-emerald-400 text-sm">{dealer.phone}</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-slate-500 block mb-1">Alternate Phone</span>
                <span className="font-mono text-slate-300">{dealer.alternate_phone || "—"}</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-slate-500 block mb-1">Email</span>
                <span className="text-slate-300">{dealer.email || "—"}</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-slate-500 block mb-1">CNIC / Tax ID</span>
                <span className="font-mono text-slate-300">{dealer.cnic || "—"}</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-slate-500 block mb-1">Territory / Area</span>
                <span className="text-white">{dealer.assigned_area_name || dealer.area || "—"}, {dealer.city}</span>
              </div>
            </div>

            {dealer.address_line && (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs">
                <span className="text-slate-500 block mb-1">Office Address</span>
                <span className="text-white">{dealer.address_line}</span>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 backdrop-blur-sm shadow-xl space-y-4">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">Commission & Agreement Terms</h2>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Revenue Split Model:</span>
                <span className="font-semibold text-white">{dealer.commission_type}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Contracted Rate:</span>
                <span className="font-bold text-amber-400 text-sm">
                  {dealer.commission_type === "PERCENTAGE"
                    ? `${dealer.commission_rate_percentage}% of collected revenue`
                    : `PKR ${dealer.commission_rate_percentage} per active customer`}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Partnership Inception:</span>
                <span className="text-slate-300">{dealer.joining_date}</span>
              </div>
            </div>

            {dealer.notes && (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-xs">
                <span className="text-slate-500 block mb-1">Contract Notes</span>
                <p className="text-slate-300 whitespace-pre-wrap">{dealer.notes}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT: CUSTOMERS */}
      {activeTab === "customers" && (
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-xl">
          {customers.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No subscriber accounts currently linked to this franchise partner.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="border-b border-slate-800 bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="py-3.5 pl-4 pr-3">Customer #</th>
                    <th className="px-3 py-3.5">Subscriber Name</th>
                    <th className="px-3 py-3.5">Contact</th>
                    <th className="px-3 py-3.5">Service #</th>
                    <th className="px-3 py-3.5">Package</th>
                    <th className="px-3 py-3.5">Monthly Rate</th>
                    <th className="px-3 py-3.5">Status</th>
                    <th className="py-3.5 pl-3 pr-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs">
                  {customers.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-800/30 transition">
                      <td className="whitespace-nowrap py-3.5 pl-4 pr-3 font-mono font-semibold text-emerald-400">
                        <Link href={`/customers/${c.id}`} className="hover:underline">
                          {c.customer_number}
                        </Link>
                      </td>
                      <td className="px-3 py-3.5 font-semibold text-white">{c.full_name}</td>
                      <td className="px-3 py-3.5 font-mono text-slate-300">{c.phone}</td>
                      <td className="px-3 py-3.5 font-mono text-slate-400">{c.service_number || "—"}</td>
                      <td className="px-3 py-3.5 font-medium text-slate-200">{c.package_name || "Custom"}</td>
                      <td className="px-3 py-3.5 font-semibold text-white">PKR {c.monthly_price || "0"}</td>
                      <td className="px-3 py-3.5">
                        <span
                          className={`rounded-full px-2 py-0.5 font-medium ${
                            c.is_active
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                              : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                          }`}
                        >
                          {c.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="py-3.5 pl-3 pr-4 text-right">
                        <Link
                          href={`/customers/${c.id}`}
                          className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white"
                        >
                          Customer 360
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: COLLECTIONS */}
      {activeTab === "collections" && (
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-xl">
          {recent_collections.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No payment transactions recorded for this dealer&apos;s customer accounts yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="border-b border-slate-800 bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="py-3.5 pl-4 pr-3">Payment #</th>
                    <th className="px-3 py-3.5">Subscriber</th>
                    <th className="px-3 py-3.5">Customer #</th>
                    <th className="px-3 py-3.5">Amount</th>
                    <th className="px-3 py-3.5">Method</th>
                    <th className="py-3.5 pl-3 pr-4 text-right">Paid Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs">
                  {recent_collections.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-800/30 transition">
                      <td className="whitespace-nowrap py-3.5 pl-4 pr-3 font-mono font-semibold text-emerald-400">
                        {p.payment_number}
                      </td>
                      <td className="px-3 py-3.5 font-semibold text-white">{p.customer_name}</td>
                      <td className="px-3 py-3.5 font-mono text-slate-400">{p.customer_number}</td>
                      <td className="px-3 py-3.5 font-bold text-emerald-400">
                        PKR {Number(p.amount).toLocaleString()}
                      </td>
                      <td className="px-3 py-3.5 uppercase font-mono text-slate-400">{p.payment_method}</td>
                      <td className="py-3.5 pl-3 pr-4 text-right text-slate-400">
                        {new Date(p.paid_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
