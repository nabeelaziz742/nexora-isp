"use client";

import { useCallback, useEffect, useState } from "react";

import DealerCustomersList from "@/components/dealers/DealerCustomersList";
import { useDealerMe } from "@/components/dealers/DealerMeContext";
import { handoverText } from "@/components/dealers/EmployeeCashList";
import { payoutHint } from "@/components/dealers/payout";
import { ApiError } from "@/services/api-error";
import { dealerPortalService, type DealerSummary } from "@/services/dealer-portal.service";

const pkr = (value: string | number) => `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

type Card = { label: string; value: string | number; hint: string; tone?: string };

// Money cards appear only when the summary includes them (employees may not see them).
function summaryCards(summary: DealerSummary): Card[] {
  const cards: Card[] = [];
  if (summary.me.cash_in_hand !== undefined) {
    const last = summary.me.last_cash_handover;
    cards.push({
      label: "Cash in hand",
      value: pkr(summary.me.cash_in_hand),
      hint: last ? `Last: ${handoverText(last)}` : "Hand this over to your dealer or the ISP office",
      tone: "text-amber-400",
    });
  }
  if (summary.total_customers !== undefined) {
    cards.push({
      label: "Customers",
      value: summary.total_customers,
      hint: `${summary.active_connections ?? 0} active`,
    });
  }
  if (summary.total_outstanding !== undefined) {
    cards.push({
      label: "Due from customers",
      value: pkr(summary.total_outstanding),
      hint: `${summary.expiring_in_3_days ?? 0} expiring in 3 days`,
      tone: "text-amber-400",
    });
  }
  if (summary.collected_this_month !== undefined) {
    cards.push({
      label: "Collected this month",
      value: pkr(summary.collected_this_month),
      hint: `${pkr(summary.collected_by_me_this_month ?? 0)} by you`,
      tone: "text-emerald-400",
    });
  } else if (summary.collected_by_me_this_month !== undefined) {
    cards.push({
      label: "Collected by you",
      value: pkr(summary.collected_by_me_this_month),
      hint: "This month",
      tone: "text-emerald-400",
    });
  }
  if (summary.commission_this_month !== undefined && !summary.parent_dealer_name) {
    const monthly = summary.payout?.basis === "MONTHLY_SLAB";
    cards.push({
      label: monthly ? "Monthly payout" : "My commission",
      value: pkr(summary.commission_this_month),
      hint: summary.payout ? payoutHint(summary.payout) : "This month, estimated",
      tone: "text-blue-400",
    });
  }
  return cards;
}

export default function DealerHomePage() {
  const me = useDealerMe();
  const [summary, setSummary] = useState<DealerSummary | null>(null);
  const [error, setError] = useState("");

  const loadSummary = useCallback(async () => {
    try {
      setSummary(await dealerPortalService.getSummary());
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load your summary.");
    }
  }, []);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  if (!me.rights.can_view_dashboard) {
    return (
      <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-6">
        <p className="text-sm text-slate-400">Assalam o Alaikum,</p>
        <h1 className="mt-1 text-xl font-bold text-white">{me.name}</h1>
        <p className="mt-2 text-sm text-slate-400">
          Welcome to the Dealer Portal{summary ? ` (${summary.organization_name})` : ""}. Use the menu on the left to
          access the sections assigned to you.
        </p>
      </div>
    );
  }

  return (
    <>
      {summary && (
        <div className="mb-5">
          <p className="text-sm text-slate-400">Assalam o Alaikum,</p>
          <h1 className="text-xl font-bold text-white">{me.is_dealer ? summary.dealer.name : me.name}</h1>
          <p className="text-xs text-slate-500">
            {summary.dealer.dealer_code}
            {!me.is_dealer
              ? ` · Working for ${summary.dealer.name}`
              : summary.parent_dealer_name
                ? ` · Sub dealer of ${summary.parent_dealer_name}`
                : summary.dealer.commission_type === "MONTHLY_SLAB"
                  ? " · Paid monthly by active users"
                  : ` · Commission ${
                      summary.dealer.commission_type === "PERCENTAGE"
                        ? `${Number(summary.dealer.commission_rate)}% of collections`
                        : `${pkr(summary.dealer.commission_rate ?? 0)} per active customer`
                    }`}
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            {summaryCards(summary).map((card) => (
              <div key={card.label} className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-3.5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{card.label}</p>
                <p className={`mt-1.5 text-lg font-bold ${card.tone ?? "text-white"}`}>{card.value}</p>
                <p className="mt-0.5 text-[11px] text-slate-500">{card.hint}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}

      <DealerCustomersList onChanged={() => void loadSummary()} />
    </>
  );
}
