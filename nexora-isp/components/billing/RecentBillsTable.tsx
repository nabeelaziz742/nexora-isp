import {
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  RefreshCw,
  ShieldAlert,
  ShieldOff,
} from "lucide-react";

import { CustomerBill } from "@/types/billing";

interface RecentBillsTableProps {
  bills: CustomerBill[];
}

const billStatusStyles = {
  PAID:
    "border-[#22C55E]/20 bg-[#22C55E]/10 text-[#22C55E]",
  UNPAID:
    "border-[#64748B]/20 bg-[#64748B]/10 text-[#94A3B8]",
  GRACE_PERIOD:
    "border-[#F59E0B]/20 bg-[#F59E0B]/10 text-[#F59E0B]",
  SUSPENSION_PENDING:
    "border-[#F59E0B]/20 bg-[#F59E0B]/10 text-[#F59E0B]",
  OVERDUE:
    "border-[#EF4444]/20 bg-[#EF4444]/10 text-[#EF4444]",
};

const serviceStatusStyles = {
  ACTIVE: {
    icon: CheckCircle2,
    color: "text-[#22C55E]",
  },
  GRACE_PERIOD: {
    icon: Clock3,
    color: "text-[#F59E0B]",
  },
  SUSPENSION_PENDING: {
    icon: ShieldAlert,
    color: "text-[#F59E0B]",
  },
  SUSPENDED_NON_PAYMENT: {
    icon: ShieldOff,
    color: "text-[#EF4444]",
  },
  RESTORE_PENDING: {
    icon: RefreshCw,
    color: "text-[#3B82F6]",
  },
};

export default function RecentBillsTable({
  bills,
}: RecentBillsTableProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-[#F8FAFC]">
          Billing Operations
        </h2>

        <p className="mt-1 text-xs text-[#64748B]">
          Customer bills, payment state and service lifecycle actions
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1180px] text-left">
          <thead>
            <tr className="border-b border-[#202938] bg-[#121821]/50">
              <th className="px-5 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Customer
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Bill
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Amount
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Due Date
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Bill Status
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Service State
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Network
              </th>

              <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                Last Automation Action
              </th>

              <th className="px-4 py-3" />
            </tr>
          </thead>

          <tbody>
            {bills.map((bill) => {
              const serviceStyle =
                serviceStatusStyles[bill.serviceStatus];

              const ServiceIcon = serviceStyle.icon;

              return (
                <tr
                  key={bill.id}
                  className="border-b border-[#202938] last:border-b-0 hover:bg-[#121821]/60"
                >
                  <td className="px-5 py-4">
                    <p className="text-sm font-medium text-[#F8FAFC]">
                      {bill.customerName}
                    </p>

                    <p className="mt-1 font-mono text-[10px] text-[#64748B]">
                      {bill.customerCode}
                    </p>
                  </td>

                  <td className="px-4 py-4">
                    <p className="font-mono text-xs text-[#3B82F6]">
                      {bill.billCode}
                    </p>

                    <p className="mt-1 text-[11px] text-[#64748B]">
                      {bill.billingMonth}
                    </p>
                  </td>

                  <td className="px-4 py-4">
                    <p className="text-sm font-medium text-[#F8FAFC]">
                      PKR {bill.amount.toLocaleString()}
                    </p>

                    <p className="mt-1 text-[10px] text-[#64748B]">
                      {bill.packageName}
                    </p>
                  </td>

                  <td className="px-4 py-4 text-xs text-[#CBD5E1]">
                    {bill.dueDate}
                  </td>

                  <td className="px-4 py-4">
                    <span
                      className={`border px-2 py-1 text-[10px] font-medium ${billStatusStyles[bill.billStatus]}`}
                    >
                      {bill.billStatus.replaceAll("_", " ")}
                    </span>
                  </td>

                  <td className="px-4 py-4">
                    <div
                      className={`flex items-center gap-2 ${serviceStyle.color}`}
                    >
                      <ServiceIcon className="h-3.5 w-3.5" />

                      <span className="text-[10px] font-medium">
                        {bill.serviceStatus.replaceAll("_", " ")}
                      </span>
                    </div>
                  </td>

                  <td className="px-4 py-4 font-mono text-xs text-[#94A3B8]">
                    {bill.connectedNode}
                  </td>

                  <td className="px-4 py-4">
                    <p className="max-w-[210px] text-xs leading-5 text-[#94A3B8]">
                      {bill.lastAction}
                    </p>
                  </td>

                  <td className="px-4 py-4">
                    <button className="flex h-8 w-8 items-center justify-center text-[#64748B] transition-colors hover:bg-[#202938] hover:text-[#F8FAFC]">
                      <ArrowUpRight className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}