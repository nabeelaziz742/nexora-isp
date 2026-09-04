import Link from "next/link";
import { ArrowUpRight, Phone, MapPin, Wifi, ShieldCheck, ShieldAlert } from "lucide-react";

import type {
  CustomerListItem,
  CustomerServiceStatus,
} from "@/services/customers.service";

interface CustomersTableProps {
  customers: CustomerListItem[];
}

const statusStyles: Record<CustomerServiceStatus, { badge: string; dot: string; label: string }> = {
  ACTIVE: {
    badge: "border-green-500/20 bg-green-500/10 text-green-400",
    dot: "bg-green-400",
    label: "Active",
  },
  GRACE_PERIOD: {
    badge: "border-amber-500/20 bg-amber-500/10 text-amber-400",
    dot: "bg-amber-400",
    label: "Grace Period",
  },
  SUSPENSION_PENDING: {
    badge: "border-orange-500/20 bg-orange-500/10 text-orange-400",
    dot: "bg-orange-400",
    label: "Suspension Pending",
  },
  SUSPENDED_NON_PAYMENT: {
    badge: "border-red-500/20 bg-red-500/10 text-red-400",
    dot: "bg-red-400",
    label: "Suspended (Non-Payment)",
  },
  RESTORE_PENDING: {
    badge: "border-blue-500/20 bg-blue-500/10 text-blue-400",
    dot: "bg-blue-400",
    label: "Restore Pending",
  },
};

function formatMonthlyPrice(monthlyPrice: CustomerListItem["monthly_price"]) {
  if (monthlyPrice === null || monthlyPrice === undefined || monthlyPrice === "") {
    return "—";
  }
  const numericPrice = Number(monthlyPrice);
  if (Number.isNaN(numericPrice)) {
    return String(monthlyPrice);
  }
  return `Rs. ${numericPrice.toLocaleString()}`;
}

export default function CustomersTable({ customers }: CustomersTableProps) {
  return (
    <div className="border border-[var(--border)] bg-[var(--surface)]">
      {/* Desktop View Table */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[900px] border-collapse text-left">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--surface-elevated)] text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
              <th className="px-5 py-3.5">Customer & Contact</th>
              <th className="px-4 py-3.5">Service Status</th>
              <th className="px-4 py-3.5">Service ID</th>
              <th className="px-4 py-3.5">Internet Plan</th>
              <th className="px-4 py-3.5">Monthly Fee</th>
              <th className="px-4 py-3.5 text-right">Actions</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-[var(--border)]">
            {customers.map((customer) => {
              const statusCfg = customer.service_status ? statusStyles[customer.service_status] : null;

              return (
                <tr
                  key={customer.id}
                  className="group transition-colors hover:bg-white/[0.02]"
                >
                  {/* Customer Info */}
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <div>
                        <Link
                          href={`/customers/${customer.id}`}
                          className="text-xs font-semibold text-white transition-colors hover:text-blue-400"
                        >
                          {customer.full_name}
                        </Link>
                        <div className="mt-0.5 flex items-center gap-2 text-[10px] text-[var(--text-muted)]">
                          <span className="font-mono text-blue-400">{customer.customer_number}</span>
                          <span>•</span>
                          <span>{customer.phone}</span>
                        </div>
                        <p className="mt-0.5 text-[10px] text-slate-400">
                          {[customer.area, customer.city].filter(Boolean).join(", ") || "No location recorded"}
                        </p>
                      </div>
                    </div>
                  </td>

                  {/* Service Status */}
                  <td className="px-4 py-3.5">
                    {statusCfg ? (
                      <span className={`inline-flex items-center gap-1.5 border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ${statusCfg.badge}`}>
                        <span className={`size-1.5 rounded-full ${statusCfg.dot}`} />
                        {statusCfg.label}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 border border-slate-700 bg-slate-800/40 px-2 py-0.5 text-[10px] font-medium text-slate-400">
                        No Active Service
                      </span>
                    )}
                  </td>

                  {/* Service Account ID */}
                  <td className="px-4 py-3.5">
                    <p className="font-mono text-xs font-medium text-slate-200">
                      {customer.service_number || "—"}
                    </p>
                    <div className="mt-0.5 flex items-center gap-1">
                      {customer.is_active ? (
                        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400">
                          <ShieldCheck className="size-3" /> Account Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] text-red-400">
                          <ShieldAlert className="size-3" /> Account Inactive
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Package */}
                  <td className="px-4 py-3.5">
                    <p className="text-xs font-medium text-white">
                      {customer.package_name || "No Package"}
                    </p>
                    <p className="mt-0.5 text-[10px] text-[var(--text-muted)]">
                      Broadband Connection
                    </p>
                  </td>

                  {/* Monthly Bill */}
                  <td className="px-4 py-3.5">
                    <p className="font-mono text-xs font-semibold text-white">
                      {formatMonthlyPrice(customer.monthly_price)}
                    </p>
                    <p className="mt-0.5 text-[10px] text-[var(--text-muted)]">Recurring</p>
                  </td>

                  {/* Action Link */}
                  <td className="px-4 py-3.5 text-right">
                    <Link
                      href={`/customers/${customer.id}`}
                      className="inline-flex items-center gap-1.5 border border-[var(--border)] bg-[var(--surface-elevated)] px-3 py-1.5 text-[11px] font-medium text-slate-300 transition-colors hover:border-blue-500/40 hover:bg-blue-500/10 hover:text-blue-400"
                    >
                      <span>Subscriber 360</span>
                      <ArrowUpRight className="size-3.5" />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Card Layout */}
      <div className="divide-y divide-[var(--border)] md:hidden">
        {customers.map((customer) => {
          const statusCfg = customer.service_status ? statusStyles[customer.service_status] : null;

          return (
            <div key={customer.id} className="p-4 transition-colors hover:bg-white/[0.02]">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <Link
                    href={`/customers/${customer.id}`}
                    className="text-sm font-semibold text-white transition-colors hover:text-blue-400"
                  >
                    {customer.full_name}
                  </Link>
                  <p className="font-mono text-xs text-blue-400">{customer.customer_number}</p>
                </div>

                {statusCfg ? (
                  <span className={`inline-flex items-center gap-1 border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${statusCfg.badge}`}>
                    <span className={`size-1.5 rounded-full ${statusCfg.dot}`} />
                    {statusCfg.label}
                  </span>
                ) : (
                  <span className="border border-slate-700 bg-slate-800/40 px-2 py-0.5 text-[9px] text-slate-400">
                    No Service
                  </span>
                )}
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Phone className="size-3.5 text-slate-500" />
                  <span>{customer.phone}</span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  <MapPin className="size-3.5 text-slate-500" />
                  <span className="truncate">{[customer.area, customer.city].filter(Boolean).join(", ") || "—"}</span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Wifi className="size-3.5 text-slate-500" />
                  <span className="truncate">{customer.package_name || "No Plan"}</span>
                </div>
                <div className="text-right font-mono font-semibold text-white">
                  {formatMonthlyPrice(customer.monthly_price)}
                </div>
              </div>

              <div className="mt-3 flex items-center justify-between border-t border-[var(--border)] pt-3">
                <span className="text-[10px] text-[var(--text-muted)]">
                  Service: {customer.service_number || "—"}
                </span>

                <Link
                  href={`/customers/${customer.id}`}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-blue-400 hover:text-blue-300"
                >
                  <span>View 360</span>
                  <ArrowUpRight className="size-3.5" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}