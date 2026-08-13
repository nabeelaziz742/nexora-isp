"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Download, Filter, Plus, Search } from "lucide-react";

import CustomersTable from "@/components/customers/CustomersTable";
import {
  customersService,
  type CustomerListItem,
} from "@/services/customers.service";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<CustomerListItem[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timeoutId = window.setTimeout(async () => {
      try {
        setLoading(true);
        setError(null);

        const data = await customersService.getCustomers({
          search,
        });

        setCustomers(data);
      } catch (requestError) {
        console.error(
          "Failed to load customers:",
          requestError,
        );

        setCustomers([]);
        setError("Unable to load customers.");
      } finally {
        setLoading(false);
      }
    }, search ? 350 : 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [search]);

  const stats = useMemo(() => {
    const activeServices = customers.filter(
      (customer) => customer.service_status === "ACTIVE",
    ).length;

    const gracePeriod = customers.filter(
      (customer) =>
        customer.service_status === "GRACE_PERIOD",
    ).length;

    const suspended = customers.filter(
      (customer) =>
        customer.service_status ===
          "SUSPENDED_NON_PAYMENT" ||
        customer.service_status === "SUSPENSION_PENDING",
    ).length;

    return [
      ["Total Customers", customers.length],
      ["Active Services", activeServices],
      ["Grace Period", gracePeriod],
      ["Suspended", suspended],
    ] as const;
  }, [customers]);

  return (
    <div className="mx-auto w-full max-w-[1600px] px-8 py-7">
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-blue-400">
            Operations
          </p>

          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">
            Customers
          </h2>

          <p className="mt-1.5 text-sm text-[var(--text-secondary)]">
            Manage subscribers, service lifecycle and network assignments.
          </p>
        </div>

        <Link
          href="/customers/new"
          className="flex items-center gap-2 bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500"
        >
          <Plus className="h-4 w-4" />
          Add Customer
        </Link>
      </div>

      <div className="mt-7 grid grid-cols-2 border-l border-t border-[var(--border)] lg:grid-cols-4">
        {stats.map(([label, value]) => (
          <div
            key={label}
            className="border-b border-r border-[var(--border)] bg-[var(--surface)] p-4"
          >
            <p className="text-[10px] text-[var(--text-muted)]">
              {label}
            </p>

            <p className="mt-2 text-xl font-semibold text-white">
              {value.toLocaleString()}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex h-9 w-full max-w-[380px] items-center gap-2 border border-[var(--border)] bg-[var(--surface)] px-3">
          <Search className="size-4 text-[var(--text-muted)]" />

          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search customer, phone or email..."
            className="h-full min-w-0 flex-1 bg-transparent text-[11px] text-white outline-none placeholder:text-[var(--text-muted)]"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="flex h-9 items-center gap-2 border border-[var(--border)] bg-[var(--surface)] px-3 text-[11px] text-[var(--text-secondary)] hover:text-white"
          >
            <Filter className="size-3.5" />
            Filters
          </button>

          <button
            type="button"
            className="flex h-9 items-center gap-2 border border-[var(--border)] bg-[var(--surface)] px-3 text-[11px] text-[var(--text-secondary)] hover:text-white"
          >
            <Download className="size-3.5" />
            Export
          </button>
        </div>
      </div>

      <div className="mt-4">
        {loading ? (
          <div className="flex min-h-56 items-center justify-center border border-[var(--border)] bg-[var(--surface)]">
            <p className="text-[11px] text-[var(--text-muted)]">
              Loading customers...
            </p>
          </div>
        ) : error ? (
          <div className="flex min-h-56 items-center justify-center border border-red-500/20 bg-red-500/[0.04]">
            <p className="text-[11px] text-red-400">
              {error}
            </p>
          </div>
        ) : customers.length === 0 ? (
          <div className="flex min-h-56 items-center justify-center border border-[var(--border)] bg-[var(--surface)]">
            <div className="text-center">
              <p className="text-[12px] font-medium text-white">
                No customers found
              </p>

              <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                {search
                  ? "No customers match the current search."
                  : "Customer records will appear here after activation."}
              </p>
            </div>
          </div>
        ) : (
          <CustomersTable customers={customers} />
        )}
      </div>
    </div>
  );
}