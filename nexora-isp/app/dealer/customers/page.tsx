"use client";

import Link from "next/link";
import { Upload, UserPlus } from "lucide-react";

import DealerCustomersList from "@/components/dealers/DealerCustomersList";
import { canSeeCustomers, useDealerMe } from "@/components/dealers/DealerMeContext";

export default function DealerCustomersPage() {
  const me = useDealerMe();

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Customers</h1>
          <p className="text-sm text-slate-400">Your customers, balances, fee collection, import, and export.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {me.rights.can_import_customers && (
            <Link
              href="/dealer/customers/import"
              className="flex h-10 items-center gap-2 rounded-lg border border-[#263142] bg-[#0D1117] px-3.5 text-sm font-medium text-slate-200 hover:bg-[#121821]"
            >
              <Upload className="h-4 w-4" /> Import
            </Link>
          )}
          {me.rights.can_request_customers && (
            <Link
              href="/dealer/requests"
              className="flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500"
            >
              <UserPlus className="h-4 w-4" /> Add Customer
            </Link>
          )}
        </div>
      </div>

      {canSeeCustomers(me.rights) ||
      me.rights.can_edit_customers ||
      me.rights.can_deactivate_customers ||
      me.rights.can_view_ledger ||
      me.rights.can_export_customers ? (
        <DealerCustomersList showExport={true} />
      ) : (
        <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
          Use the Add Customer or Import buttons above to add customers.
        </div>
      )}
    </>
  );
}
