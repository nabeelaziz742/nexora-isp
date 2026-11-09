"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, X } from "lucide-react";

import { getOwnerSubscription, type OwnerSubscriptionStatus } from "@/services/auth.service";

const DISMISS_KEY = "nexora_subscription_notice_dismissed";

function formatDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

// Shown to the ISP owner when their Nexora subscription is due within 7 days or overdue.
export default function SubscriptionNotice() {
  const [status, setStatus] = useState<OwnerSubscriptionStatus | null>(null);
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    let active = true;
    try {
      if (window.localStorage.getItem("nexora_role") !== "OWNER") return;
    } catch {
      return;
    }
    getOwnerSubscription()
      .then((data) => {
        if (!active || !data.show_notice || !data.paid_until) return;
        let hidden = false;
        try {
          // Dismissal lasts for the day; the notice returns tomorrow until paid.
          hidden = window.sessionStorage.getItem(DISMISS_KEY) === `${data.paid_until}:${new Date().toDateString()}`;
        } catch {
          hidden = false;
        }
        setStatus(data);
        setDismissed(hidden);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  if (!status || dismissed || !status.paid_until || status.days_left === null) return null;

  const overdue = status.days_left < 0;
  const fee = `PKR ${Number(status.monthly_fee).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;
  const headline = overdue
    ? `Your Nexora subscription is overdue since ${formatDate(status.paid_until)}.`
    : status.days_left === 0
      ? "Your Nexora subscription is due today."
      : `Your Nexora subscription is due on ${formatDate(status.paid_until)} (${status.days_left} day${status.days_left === 1 ? "" : "s"} left).`;

  return (
    <div className={`border-b px-4 py-2.5 text-xs ${overdue ? "border-red-500/30 bg-red-500/10 text-red-300" : "border-amber-500/30 bg-amber-500/10 text-amber-300"}`}>
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{headline}</p>
          <p className="mt-0.5 opacity-90">
            Pay {fee} to {status.payment.bank_name}, {status.payment.account_title}, account {status.payment.account_number}
            {status.lock_date ? `. Without payment, this workspace locks on ${formatDate(status.lock_date)}.` : "."}
          </p>
        </div>
        <button
          onClick={() => {
            try {
              window.sessionStorage.setItem(DISMISS_KEY, `${status.paid_until}:${new Date().toDateString()}`);
            } catch {
              // ignore storage errors
            }
            setDismissed(true);
          }}
          aria-label="Dismiss"
          className="shrink-0 opacity-70 hover:opacity-100"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
