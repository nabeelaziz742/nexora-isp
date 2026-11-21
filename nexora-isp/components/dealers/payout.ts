import type { CommissionType, DealerPayout, PayoutSlab } from "@/services/dealers.service";

const pkr = (value: string | number) => `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

// How a dealer is paid, in one short line.
export function payTermsText(dealer: {
  commission_type: CommissionType;
  commission_rate_percentage: string | number;
  parent_dealer?: string | null;
  parent_dealer_name?: string | null;
}) {
  if (dealer.parent_dealer) return `Paid by ${dealer.parent_dealer_name ?? "their dealer"}`;
  if (dealer.commission_type === "MONTHLY_SLAB") return "Monthly fixed by active users";
  if (dealer.commission_type === "PERCENTAGE") return `${Number(dealer.commission_rate_percentage)}% of collections`;
  return `${pkr(dealer.commission_rate_percentage)} per active user`;
}

export function slabText(slab: PayoutSlab) {
  return `${slab.min_active_users.toLocaleString()}+ users → ${pkr(slab.monthly_amount)}/month`;
}

// Why this month's payout is what it is, e.g. "640 active users · 500+ slab · 140 more for the next slab".
export function payoutHint(payout: DealerPayout) {
  if (payout.basis === "PAID_BY_PARENT") return "Sub dealer: paid by their dealer";
  if (payout.basis !== "MONTHLY_SLAB") return `${payout.active_users.toLocaleString()} active users`;
  const parts = [`${payout.active_users.toLocaleString()} active users`];
  parts.push(payout.slab ? `${payout.slab.min_active_users.toLocaleString()}+ slab` : "no slab reached yet");
  if (payout.next_slab) {
    const more = payout.next_slab.min_active_users - payout.active_users;
    parts.push(`${more.toLocaleString()} more for ${pkr(payout.next_slab.monthly_amount)}`);
  }
  return parts.join(" · ");
}
