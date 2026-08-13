import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import CustomerOnboarding from "@/components/customers/CustomerOnboarding";

export default function NewCustomerPage() {
  return (
    <div className="mx-auto w-full max-w-[1600px] px-8 py-7">
      <Link
        href="/customers"
        className="inline-flex items-center gap-2 text-[11px] text-[var(--text-muted)] transition-colors hover:text-white"
      >
        <ArrowLeft className="size-4" />
        Back to Customers
      </Link>

      <div className="mt-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-blue-400">
          Customer Provisioning
        </p>

        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">
          Add Customer
        </h2>

        <p className="mt-1.5 text-sm text-[var(--text-secondary)]">
          Provision a subscriber, assign network access and configure billing.
        </p>
      </div>

      <div className="mt-7">
        <CustomerOnboarding />
      </div>
    </div>
  );
}