import type { ExpenseStatus } from "@/services/dealer-portal.service";

const STYLE: Record<ExpenseStatus, { label: string; cls: string }> = {
  PENDING: { label: "Pending", cls: "border-amber-500/30 bg-amber-500/10 text-amber-400" },
  APPROVED: { label: "Approved", cls: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" },
  REJECTED: { label: "Rejected", cls: "border-red-500/30 bg-red-500/10 text-red-400" },
};

export const pkr = (value: string | number) =>
  `PKR ${Number(value).toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;

export const shortDate = (value: string) =>
  new Date(value.length === 10 ? `${value}T00:00:00` : value).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

export default function ExpenseStatusBadge({ status }: { status: ExpenseStatus }) {
  const style = STYLE[status];
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${style.cls}`}>{style.label}</span>
  );
}
