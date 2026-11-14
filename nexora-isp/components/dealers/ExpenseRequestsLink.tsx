"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Receipt } from "lucide-react";

import { dealerPortalService } from "@/services/dealer-portal.service";

// "Employee Expenses" button for the Dealers page, with the number waiting for a decision.
export default function ExpenseRequestsLink() {
  const [pending, setPending] = useState(0);

  useEffect(() => {
    let active = true;
    dealerPortalService
      .getOfficeExpenses("PENDING")
      .then((data) => active && setPending(data.counts.PENDING))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  return (
    <Link
      href="/dealers/expenses"
      className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
    >
      <Receipt className="h-4 w-4" />
      Employee Expenses
      {pending > 0 && (
        <span className="rounded-full bg-amber-500 px-1.5 text-xs font-bold text-black">{pending}</span>
      )}
    </Link>
  );
}
