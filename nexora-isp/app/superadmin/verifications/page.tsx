"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Eye, Loader2, X } from "lucide-react";

import { ErrorBanner, PageHeader, formatPKR, useSuperAdminErrorHandler } from "@/components/superadmin/ui";
import {
  approveRegistration,
  getAdminRegistrations,
  getReceiptObjectUrl,
  rejectRegistration,
  type Registration,
} from "@/services/onboarding.service";

const POLLING_INTERVAL_MS = 10000;

function readToken() {
  return localStorage.getItem("nexora_superadmin_access") ?? "";
}

export default function PaymentVerificationPage() {
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [receiptUrl, setReceiptUrl] = useState("");
  const handleError = useSuperAdminErrorHandler(setError);
  const busyIdRef = useRef("");

  useEffect(() => {
    busyIdRef.current = busyId;
  }, [busyId]);

  const load = useCallback(
    async (background = false) => {
      if (background && busyIdRef.current) return;
      try {
        setRegistrations(await getAdminRegistrations(readToken(), "PENDING_VERIFICATION"));
        if (!background) setError("");
      } catch (err) {
        // Background polling stays quiet unless the session expired.
        if (!background || (err as { status?: number })?.status === 401) {
          handleError(err, "Unable to load pending verifications.");
        }
      } finally {
        setLoading(false);
      }
    },
    [handleError],
  );

  useEffect(() => {
    // Initial fetch, then poll so new receipts show up without a refresh.
    void load();
    const timer = setInterval(() => void load(true), POLLING_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [load]);

  async function approve(id: string) {
    setBusyId(id);
    setError("");
    try {
      await approveRegistration(readToken(), id);
      setRegistrations((items) => items.filter((item) => item.id !== id));
    } catch (err) {
      handleError(err, "Unable to approve payment.");
    } finally {
      setBusyId("");
    }
  }

  async function reject(id: string) {
    const reason = window.prompt("Reason for rejecting this payment:", "Payment could not be verified.");
    if (reason === null) return;
    setBusyId(id);
    setError("");
    try {
      await rejectRegistration(readToken(), id, reason);
      setRegistrations((items) => items.filter((item) => item.id !== id));
    } catch (err) {
      handleError(err, "Unable to reject payment.");
    } finally {
      setBusyId("");
    }
  }

  async function viewReceipt(id: string) {
    try {
      if (receiptUrl) URL.revokeObjectURL(receiptUrl);
      setReceiptUrl(await getReceiptObjectUrl(readToken(), id));
    } catch (err) {
      handleError(err, "Unable to load receipt.");
    }
  }

  function closeReceipt() {
    URL.revokeObjectURL(receiptUrl);
    setReceiptUrl("");
  }

  return (
    <>
      <PageHeader
        title="Payment Verification"
        subtitle="Review submitted receipts before activating ISP accounts. Approval also starts the ISP's first paid month."
      />
      <ErrorBanner message={error} />

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
        </div>
      ) : registrations.length === 0 ? (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-slate-500">
          No pending payment verifications.
        </div>
      ) : (
        <div className="space-y-4">
          {registrations.map((item) => (
            <div key={item.id} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5">
              <div className="grid gap-5 lg:grid-cols-[1fr_auto]">
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="text-xs text-slate-500">ISP</p>
                    <p className="font-semibold text-white">{item.company_name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Owner</p>
                    <p className="text-slate-200">{item.owner_name}</p>
                    <p className="text-xs text-slate-500">{item.owner_email}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Organization Code</p>
                    <p className="text-slate-200">{item.organization_code}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Amount</p>
                    <p className="text-slate-200">{formatPKR(item.amount_due)}</p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                  <button
                    onClick={() => void viewReceipt(item.id)}
                    disabled={!item.receipt_url}
                    className="flex h-10 items-center gap-2 rounded-lg border border-[#263142] px-4 text-sm text-slate-200 hover:bg-[#151D27] disabled:opacity-40"
                  >
                    <Eye className="h-4 w-4" /> Receipt
                  </button>
                  <button
                    onClick={() => void approve(item.id)}
                    disabled={busyId === item.id}
                    className="flex h-10 items-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    <Check className="h-4 w-4" /> Approve
                  </button>
                  <button
                    onClick={() => void reject(item.id)}
                    disabled={busyId === item.id}
                    className="flex h-10 items-center gap-2 rounded-lg bg-red-600 px-4 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    <X className="h-4 w-4" /> Reject
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {receiptUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-6" onClick={closeReceipt}>
          <div
            className="max-h-[90vh] max-w-4xl overflow-auto rounded-xl bg-[#0D1117] p-4"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-3 flex justify-end">
              <button onClick={closeReceipt} aria-label="Close receipt">
                <X className="text-slate-300" />
              </button>
            </div>
            {/* A blob: object URL from an authenticated download; next/image cannot optimise it. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={receiptUrl} alt="Payment receipt" className="max-h-[78vh] max-w-full object-contain" />
          </div>
        </div>
      )}
    </>
  );
}
