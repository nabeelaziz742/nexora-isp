import Link from "next/link";
import { ArrowUpRight, MoreHorizontal } from "lucide-react";

import type {
  CustomerListItem,
  CustomerServiceStatus,
} from "@/services/customers.service";

interface CustomersTableProps {
  customers: CustomerListItem[];
}

const statusStyles: Record<CustomerServiceStatus, string> = {
  ACTIVE: "border-green-500/20 bg-green-500/10 text-green-400",
  GRACE_PERIOD: "border-amber-500/20 bg-amber-500/10 text-amber-400",
  SUSPENSION_PENDING:
    "border-orange-500/20 bg-orange-500/10 text-orange-400",
  SUSPENDED_NON_PAYMENT:
    "border-red-500/20 bg-red-500/10 text-red-400",
  RESTORE_PENDING:
    "border-blue-500/20 bg-blue-500/10 text-blue-400",
};

function formatStatus(status: CustomerServiceStatus) {
  return status.replaceAll("_", " ");
}

function formatMonthlyPrice(
  monthlyPrice: CustomerListItem["monthly_price"],
) {
  if (
    monthlyPrice === null ||
    monthlyPrice === undefined ||
    monthlyPrice === ""
  ) {
    return "—";
  }

  const numericPrice = Number(monthlyPrice);

  if (Number.isNaN(numericPrice)) {
    return String(monthlyPrice);
  }

  return `Rs. ${numericPrice.toLocaleString()}`;
}

export default function CustomersTable({
  customers,
}: CustomersTableProps) {
  return (
    <div className="overflow-hidden border border-[var(--border)] bg-[var(--surface)]">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1000px] border-collapse">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--surface-elevated)]">
              <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
                Customer
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
                Service Status
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
                Service
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
                Package
              </th>

              <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
                Monthly Bill
              </th>

              <th className="w-20 px-4 py-3" />
            </tr>
          </thead>

          <tbody className="divide-y divide-[var(--border)]">
            {customers.map((customer) => (
              <tr
                key={customer.id}
                className="transition-colors hover:bg-white/[0.02]"
              >
                <td className="px-5 py-4">
                  <p className="text-[12px] font-semibold text-white">
                    {customer.full_name}
                  </p>

                  <div className="mt-1 flex items-center gap-2">
                    <span className="text-[10px] text-blue-400">
                      {customer.customer_number}
                    </span>

                    <span className="text-[10px] text-[var(--text-muted)]">
                      {[customer.area, customer.city]
                        .filter(Boolean)
                        .join(", ") || "Location unavailable"}
                    </span>
                  </div>

                  <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                    {customer.phone}
                  </p>
                </td>

                <td className="px-4 py-4">
                  {customer.service_status ? (
                    <span
                      className={`inline-flex border px-2 py-1 text-[9px] font-semibold uppercase tracking-wide ${
                        statusStyles[customer.service_status]
                      }`}
                    >
                      {formatStatus(customer.service_status)}
                    </span>
                  ) : (
                    <span className="inline-flex border border-white/10 bg-white/[0.03] px-2 py-1 text-[9px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                      No Service
                    </span>
                  )}
                </td>

                <td className="px-4 py-4">
                  <p className="text-[11px] font-medium text-white">
                    {customer.service_number || "—"}
                  </p>

                  <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                    {customer.is_active
                      ? "Customer active"
                      : "Customer inactive"}
                  </p>
                </td>

                <td className="px-4 py-4">
                  <p className="text-[11px] font-medium text-white">
                    {customer.package_name || "No package"}
                  </p>

                  <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                    Internet service
                  </p>
                </td>

                <td className="px-4 py-4">
                  <p className="text-[12px] font-semibold text-white">
                    {formatMonthlyPrice(customer.monthly_price)}
                  </p>

                  <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                    Monthly
                  </p>
                </td>

                <td className="px-4 py-4">
                  <div className="flex items-center justify-end gap-1">
                    <Link
                      href={`/customers/${customer.id}`}
                      aria-label={`Open ${customer.full_name}`}
                      className="flex size-8 items-center justify-center text-[var(--text-muted)] transition-colors hover:text-blue-400"
                    >
                      <ArrowUpRight className="size-4" />
                    </Link>

                    <button
                      type="button"
                      aria-label={`More actions for ${customer.full_name}`}
                      className="flex size-8 items-center justify-center text-[var(--text-muted)] transition-colors hover:text-white"
                    >
                      <MoreHorizontal className="size-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}