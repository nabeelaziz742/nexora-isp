"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Eye, Loader2, LogOut, ShieldCheck, X } from "lucide-react";
import { useRouter } from "next/navigation";

import {
  approveRegistration,
  getAdminRegistrations,
  getReceiptObjectUrl,
  rejectRegistration,
  type Registration,
} from "@/services/onboarding.service";

const POLLING_INTERVAL_MS = 10000;

export default function SuperAdminPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [receiptUrl, setReceiptUrl] = useState("");

  const isPollingRef = useRef(false);
  const isMountedRef = useRef(true);
  const busyIdRef = useRef("");
  busyIdRef.current = busyId;

  const handleUnauthorized = useCallback(() => {
    localStorage.removeItem("nexora_superadmin_access");
    localStorage.removeItem("nexora_superadmin_refresh");
    if (isMountedRef.current) {
      router.replace("/superadmin/login");
    }
  }, [router]);

  const syncRegistrations = useCallback(
    async (currentToken: string) => {
      if (isPollingRef.current || busyIdRef.current) return;
      isPollingRef.current = true;
      try {
        const items = await getAdminRegistrations(
          currentToken,
          "PENDING_VERIFICATION",
        );
        if (isMountedRef.current) {
          setRegistrations(items);
        }
      } catch (err: unknown) {
        const status = (err as { status?: number })?.status;
        if (status === 401) {
          handleUnauthorized();
          return;
        }
        // Silently ignore transient background polling errors to maintain smooth UX
      } finally {
        isPollingRef.current = false;
      }
    },
    [handleUnauthorized],
  );

  const load = useCallback(
    async (currentToken: string) => {
      setLoading(true);
      setError("");
      try {
        const items = await getAdminRegistrations(
          currentToken,
          "PENDING_VERIFICATION",
        );
        if (isMountedRef.current) {
          setRegistrations(items);
        }
      } catch (err: unknown) {
        const status = (err as { status?: number })?.status;
        if (status === 401) {
          handleUnauthorized();
          return;
        }
        if (isMountedRef.current) {
          setError(
            err instanceof Error ? err.message : "Unable to load admin data.",
          );
        }
      } finally {
        if (isMountedRef.current) {
          setLoading(false);
        }
      }
    },
    [handleUnauthorized],
  );

  useEffect(() => {
    isMountedRef.current = true;
    const currentToken = localStorage.getItem("nexora_superadmin_access");
    if (!currentToken) {
      router.replace("/superadmin/login");
      return;
    }
    setToken(currentToken);
    void load(currentToken);

    const timer = setInterval(() => {
      void syncRegistrations(currentToken);
    }, POLLING_INTERVAL_MS);

    return () => {
      isMountedRef.current = false;
      clearInterval(timer);
    };
  }, [router, load, syncRegistrations]);

  async function approve(id: string) {
    if (!token) return;
    setBusyId(id);
    setError("");
    try {
      await approveRegistration(token, id);
      setRegistrations((items) => items.filter((item) => item.id !== id));
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 401) {
        handleUnauthorized();
        return;
      }
      setError(
        err instanceof Error ? err.message : "Unable to approve payment.",
      );
    } finally {
      setBusyId("");
    }
  }

  async function reject(id: string) {
    if (!token) return;
    const reason = window.prompt(
      "Reason for rejecting this payment:",
      "Payment could not be verified.",
    );
    if (reason === null) return;
    setBusyId(id);
    setError("");
    try {
      await rejectRegistration(token, id, reason);
      setRegistrations((items) => items.filter((item) => item.id !== id));
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 401) {
        handleUnauthorized();
        return;
      }
      setError(
        err instanceof Error ? err.message : "Unable to reject payment.",
      );
    } finally {
      setBusyId("");
    }
  }

  async function viewReceipt(id: string) {
    if (!token) return;
    try {
      if (receiptUrl) URL.revokeObjectURL(receiptUrl);
      setReceiptUrl(await getReceiptObjectUrl(token, id));
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 401) {
        handleUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Unable to load receipt.");
    }
  }

  function logout() {
    localStorage.removeItem("nexora_superadmin_access");
    localStorage.removeItem("nexora_superadmin_refresh");
    router.replace("/superadmin/login");
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070A0F] text-white">
        <Loader2 className="h-7 w-7 animate-spin text-blue-500" />
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#070A0F] text-white">
      <header className="border-b border-[#1C2431] bg-[#0D1117] px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-6 w-6 text-blue-400" />
            <div>
              <p className="font-semibold">Nexora Super Admin</p>
              <p className="text-xs text-slate-500">Platform administration</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-8 px-6 py-8">
        {error && (
          <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <section>
          <div className="mb-4">
            <h1 className="text-2xl font-bold">Payment Verification</h1>
            <p className="text-sm text-slate-400">
              Review submitted receipts before activating ISP accounts.
            </p>
          </div>
          {registrations.length === 0 ? (
            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-slate-500">
              No pending payment verifications.
            </div>
          ) : (
            <div className="space-y-4">
              {registrations.map((item) => (
                <div
                  key={item.id}
                  className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-5"
                >
                  <div className="grid gap-5 lg:grid-cols-[1fr_auto]">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div>
                        <p className="text-xs text-slate-500">ISP</p>
                        <p className="font-semibold">{item.company_name}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500">Owner</p>
                        <p>{item.owner_name}</p>
                        <p className="text-xs text-slate-500">
                          {item.owner_email}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500">
                          Organization Code
                        </p>
                        <p>{item.organization_code}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500">Amount</p>
                        <p>Rs. {item.amount_due}</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                      <button
                        onClick={() => void viewReceipt(item.id)}
                        disabled={!item.receipt_url}
                        className="flex h-10 items-center gap-2 rounded-lg border border-[#263142] px-4 text-sm hover:bg-[#151D27] disabled:opacity-40"
                      >
                        <Eye className="h-4 w-4" /> Receipt
                      </button>
                      <button
                        onClick={() => void approve(item.id)}
                        disabled={busyId === item.id}
                        className="flex h-10 items-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
                      >
                        <Check className="h-4 w-4" /> Approve
                      </button>
                      <button
                        onClick={() => void reject(item.id)}
                        disabled={busyId === item.id}
                        className="flex h-10 items-center gap-2 rounded-lg bg-red-600 px-4 text-sm font-medium hover:bg-red-700 disabled:opacity-50"
                      >
                        <X className="h-4 w-4" /> Reject
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {receiptUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-6"
          onClick={() => {
            URL.revokeObjectURL(receiptUrl);
            setReceiptUrl("");
          }}
        >
          <div
            className="max-h-[90vh] max-w-4xl overflow-auto rounded-xl bg-[#0D1117] p-4"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-3 flex justify-end">
              <button
                onClick={() => {
                  URL.revokeObjectURL(receiptUrl);
                  setReceiptUrl("");
                }}
              >
                <X />
              </button>
            </div>
            <img
              src={receiptUrl}
              alt="Payment receipt"
              className="max-h-[78vh] max-w-full object-contain"
            />
          </div>
        </div>
      )}
    </main>
  );
}
