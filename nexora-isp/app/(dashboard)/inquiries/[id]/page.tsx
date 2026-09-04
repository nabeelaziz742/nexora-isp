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
  ClipboardCheck,
  ClipboardList,
  Edit3,
  MapPin,
  Phone,
  RefreshCw,
  User,
  UserCheck,
  UserPlus,
  Wifi,
  X,
  XCircle,
} from "lucide-react";

import Skeleton from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";
import {
  inquiriesService,
  type FeasibilityAssessmentItem,
  type InquiryItem,
  type InquiryStatus,
} from "@/services/inquiries.service";

const STATUS_CONFIG: Record<
  InquiryStatus,
  { label: string; badgeClass: string }
> = {
  NEW: { label: "New Lead", badgeClass: "bg-blue-500/10 text-blue-400 border-blue-500/30" },
  CONTACTED: { label: "Contacted", badgeClass: "bg-sky-500/10 text-sky-400 border-sky-500/30" },
  FEASIBILITY_PENDING: { label: "Feasibility Pending", badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/30" },
  FEASIBLE: { label: "Feasible", badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" },
  NOT_FEASIBLE: { label: "Not Feasible", badgeClass: "bg-rose-500/10 text-rose-400 border-rose-500/30" },
  FOLLOW_UP: { label: "Follow Up", badgeClass: "bg-purple-500/10 text-purple-400 border-purple-500/30" },
  CONVERTED: { label: "Converted", badgeClass: "bg-emerald-600/20 text-emerald-300 border-emerald-500/40" },
  LOST: { label: "Lost", badgeClass: "bg-slate-500/10 text-slate-400 border-slate-500/30" },
  CANCELLED: { label: "Cancelled", badgeClass: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30" },
};

export default function InquiryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const inquiryId = params.id as string;

  const [inquiry, setInquiry] = useState<InquiryItem | null>(null);
  const [feasibilities, setFeasibilities] = useState<FeasibilityAssessmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [inqData, fsbData] = await Promise.all([
        inquiriesService.getInquiry(inquiryId),
        inquiriesService.getFeasibilities({ inquiry_id: inquiryId }),
      ]);
      setInquiry(inqData);
      setFeasibilities(fsbData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load inquiry details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (inquiryId) {
      loadData();
    }
  }, [inquiryId]);

  if (loading) {
    return (
      <div className="space-y-6 pb-12">
        <Skeleton className="h-10 w-48 rounded-lg" />
        <Skeleton className="h-64 w-full rounded-2xl" />
        <Skeleton className="h-48 w-full rounded-2xl" />
      </div>
    );
  }

  if (error || !inquiry) {
    return (
      <div className="py-8">
        <ErrorState message={error || "Inquiry not found"} onRetry={loadData} />
      </div>
    );
  }

  const statusConf = STATUS_CONFIG[inquiry.status] || {
    label: inquiry.status,
    badgeClass: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Breadcrumb & Action Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/inquiries")}
            className="rounded-lg border border-slate-800 bg-slate-900/80 p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl font-mono">
                {inquiry.inquiry_number}
              </h1>
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusConf.badgeClass}`}>
                {statusConf.label}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Created on {new Date(inquiry.created_at).toLocaleDateString()} • Lead Source: {inquiry.source}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {inquiry.converted_customer && (
            <Link
              href={`/customers/${inquiry.converted_customer}`}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600/20 border border-emerald-500/40 px-3.5 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-600 hover:text-white transition"
            >
              <UserCheck className="h-4 w-4" />
              View Customer {inquiry.converted_customer_number}
            </Link>
          )}
          <button
            onClick={loadData}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Prospect & Service Overview Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left 2 Cols: Prospect Details */}
        <div className="space-y-6 lg:col-span-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 backdrop-blur-sm shadow-xl space-y-5">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <User className="h-4 w-4 text-emerald-400" />
              Prospect Details
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
              <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3">
                <span className="text-xs text-slate-500 block mb-1">Full Name</span>
                <span className="font-semibold text-white">{inquiry.full_name}</span>
              </div>
              <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3">
                <span className="text-xs text-slate-500 block mb-1">Primary Phone</span>
                <span className="font-mono text-emerald-400">{inquiry.phone}</span>
              </div>
              <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3">
                <span className="text-xs text-slate-500 block mb-1">Alternate Phone</span>
                <span className="font-mono text-slate-300">{inquiry.alternate_phone || "—"}</span>
              </div>
              <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3">
                <span className="text-xs text-slate-500 block mb-1">Email</span>
                <span className="text-slate-300">{inquiry.email || "—"}</span>
              </div>
              <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3">
                <span className="text-xs text-slate-500 block mb-1">CNIC / ID</span>
                <span className="font-mono text-slate-300">{inquiry.cnic || "—"}</span>
              </div>
              <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3">
                <span className="text-xs text-slate-500 block mb-1">Assigned Dealer</span>
                <span className="text-amber-400 font-medium">{inquiry.dealer_name || "Direct ISP"}</span>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 space-y-1">
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-slate-400" />
                Physical Installation Address
              </span>
              <p className="text-sm font-medium text-white">{inquiry.address_line}</p>
              <p className="text-xs text-slate-400">
                {inquiry.area}, {inquiry.city} {inquiry.country ? `, ${inquiry.country}` : ""}
              </p>
            </div>

            {inquiry.notes && (
              <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4">
                <span className="text-xs text-slate-500 block mb-1">Internal Notes</span>
                <p className="text-xs text-slate-300 whitespace-pre-wrap">{inquiry.notes}</p>
              </div>
            )}
          </div>

          {/* Feasibility Assessment History */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 backdrop-blur-sm shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <ClipboardCheck className="h-4 w-4 text-amber-400" />
                Feasibility Assessment Records ({feasibilities.length})
              </h2>
            </div>

            {feasibilities.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-800 p-6 text-center text-xs text-slate-500">
                No formal feasibility assessment records logged yet.
              </div>
            ) : (
              <div className="space-y-3">
                {feasibilities.map((fsb) => (
                  <div
                    key={fsb.id}
                    className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-amber-400">
                          {fsb.feasibility_number}
                        </span>
                        <span
                          className={`rounded-full px-2 py-0.5 font-medium ${
                            fsb.status === "FEASIBLE"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                              : fsb.status === "NOT_FEASIBLE"
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                              : "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                          }`}
                        >
                          {fsb.status}
                        </span>
                      </div>
                      <span className="text-slate-500">
                        {new Date(fsb.created_at).toLocaleString()}
                      </span>
                    </div>

                    {fsb.status === "NOT_FEASIBLE" && (
                      <div className="rounded-lg bg-rose-950/30 border border-rose-500/30 p-2.5 text-rose-300">
                        <strong className="block font-semibold">Reason: {fsb.not_feasible_reason}</strong>
                        {fsb.not_feasible_details && <p className="mt-0.5">{fsb.not_feasible_details}</p>}
                      </div>
                    )}

                    {fsb.remarks && (
                      <div className="text-slate-300 bg-slate-900/60 p-2.5 rounded-lg">
                        <strong>Survey Notes:</strong> {fsb.remarks}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Service Request & Conversion Summary */}
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 backdrop-blur-sm shadow-xl space-y-4">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Wifi className="h-4 w-4 text-sky-400" />
              Requested Service
            </h2>

            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Connection Medium:</span>
                <span className="font-mono font-semibold text-white">{inquiry.connection_type}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Package:</span>
                <span className="font-semibold text-emerald-400">{inquiry.preferred_package_name || "Custom"}</span>
              </div>
              {inquiry.preferred_package_speed && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Bandwidth:</span>
                  <span className="font-mono text-white">{inquiry.preferred_package_speed} Mbps</span>
                </div>
              )}
              {inquiry.preferred_package_price && (
                <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-800">
                  <span className="text-slate-400">Monthly Plan Rate:</span>
                  <span className="font-bold text-white">PKR {inquiry.preferred_package_price}</span>
                </div>
              )}
            </div>

            {inquiry.converted_customer ? (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-xs text-emerald-300 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" />
                  Successfully Converted
                </div>
                <p>Converted on {inquiry.converted_at ? new Date(inquiry.converted_at).toLocaleString() : "—"}</p>
                <p className="font-mono">Customer ID: {inquiry.converted_customer}</p>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-xs text-slate-400">
                Lead is currently open. Once physical feasibility is confirmed, you can convert this lead to a subscriber account from the inquiries list.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
