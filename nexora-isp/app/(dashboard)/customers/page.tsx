"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Download,
  Filter,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Users,
  Wifi,
  X,
} from "lucide-react";

import CustomersTable from "@/components/customers/CustomersTable";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Skeleton from "@/components/ui/Skeleton";
import {
  customersService,
  type CustomerListItem,
  type CustomerServiceStatus,
  type InternetPackage,
} from "@/services/customers.service";
import { geoService, type City, type Area } from "@/services/geo.service";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<CustomerListItem[]>([]);
  const [packages, setPackages] = useState<InternetPackage[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);

  // Filter States
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<CustomerServiceStatus | "">("");
  const [activeFilter, setActiveFilter] = useState<string>("");
  const [cityFilter, setCityFilter] = useState("");
  const [areaFilter, setAreaFilter] = useState("");
  const [packageFilter, setPackageFilter] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load Packages and Cities for Filter Options
  useEffect(() => {
    async function loadFilterOptions() {
      try {
        const [pkgs, cityList] = await Promise.all([
          customersService.getInternetPackages({ status: "active" }),
          geoService.getCities({ status: "active" }),
        ]);
        setPackages(pkgs);
        setCities(cityList);
      } catch {
        // Silently fail secondary filter options
      }
    }
    void loadFilterOptions();
  }, []);

  // Cascade Area options when city changes
  useEffect(() => {
    if (!cityFilter) {
      setAreas([]);
      setAreaFilter("");
      return;
    }
    const matchedCity = cities.find((c) => c.name === cityFilter);
    if (matchedCity) {
      geoService.getAreas({ city: matchedCity.id, status: "active" })
        .then((res) => setAreas(res))
        .catch(() => setAreas([]));
    }
  }, [cityFilter, cities]);

  const loadCustomers = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await customersService.getCustomers({
        search,
        status: statusFilter,
        city: cityFilter,
        area: areaFilter,
        package_id: packageFilter,
        is_active: activeFilter || undefined,
      });

      setCustomers(data);
    } catch (requestError) {
      console.error("Failed to load customers:", requestError);
      setCustomers([]);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load customer records from server."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadCustomers();
    }, search ? 300 : 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [search, statusFilter, activeFilter, cityFilter, areaFilter, packageFilter]);

  const hasActiveFilters = Boolean(
    search || statusFilter || activeFilter || cityFilter || areaFilter || packageFilter
  );

  const resetFilters = () => {
    setSearch("");
    setStatusFilter("");
    setActiveFilter("");
    setCityFilter("");
    setAreaFilter("");
    setPackageFilter("");
  };

  const stats = useMemo(() => {
    const total = customers.length;
    const activeServices = customers.filter(
      (customer) => customer.service_status === "ACTIVE"
    ).length;
    const gracePeriod = customers.filter(
      (customer) => customer.service_status === "GRACE_PERIOD"
    ).length;
    const suspended = customers.filter(
      (customer) =>
        customer.service_status === "SUSPENDED_NON_PAYMENT" ||
        customer.service_status === "SUSPENSION_PENDING"
    ).length;

    return [
      { label: "Total Subscribers", value: total, icon: Users, color: "text-blue-400" },
      { label: "Active Services", value: activeServices, icon: Wifi, color: "text-green-400" },
      { label: "Grace Period", value: gracePeriod, icon: Wifi, color: "text-amber-400" },
      { label: "Suspended / Pending", value: suspended, icon: Wifi, color: "text-red-400" },
    ];
  }, [customers]);

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-blue-400">
            Operations & Subscribers
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Customer Management
          </h1>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            Manage subscriber profiles, service account connections, and network provisioning.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => void loadCustomers()}
            disabled={loading}
            className="flex h-9 items-center gap-2 border border-[var(--border)] bg-[var(--surface)] px-3 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:text-white disabled:opacity-50"
          >
            <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>

          <Link
            href="/customers/new"
            className="flex h-9 items-center gap-2 bg-blue-600 px-4 text-xs font-semibold text-white transition-colors hover:bg-blue-500"
          >
            <Plus className="size-4" />
            Add Customer
          </Link>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="mt-6 grid grid-cols-2 gap-px border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className="bg-[var(--surface)] p-4 transition-colors hover:bg-white/[0.02]"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  {stat.label}
                </span>
                <Icon className={`size-4 ${stat.color} opacity-80`} />
              </div>
              <p className="mt-2 text-2xl font-bold text-white">
                {stat.value.toLocaleString()}
              </p>
            </div>
          );
        })}
      </div>

      {/* Operational Toolbar */}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Search */}
        <div className="flex h-10 w-full max-w-md items-center gap-2.5 border border-[var(--border)] bg-[var(--surface)] px-3.5 focus-within:border-blue-500">
          <Search className="size-4 shrink-0 text-[var(--text-muted)]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by customer number, name, phone, email, address, or service ID..."
            className="h-full w-full bg-transparent text-xs text-white outline-none placeholder:text-[var(--text-muted)]"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              className="text-[var(--text-muted)] hover:text-white"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        {/* Filter Toggle & Clear */}
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              type="button"
              onClick={resetFilters}
              className="flex h-10 items-center gap-1.5 border border-red-500/20 bg-red-500/10 px-3 text-xs font-medium text-red-400 transition-colors hover:bg-red-500/20"
            >
              <RotateCcw className="size-3.5" />
              Reset Filters
            </button>
          )}

          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className={`flex h-10 items-center gap-2 border px-3.5 text-xs font-medium transition-colors ${
              showFilters || hasActiveFilters
                ? "border-blue-500/40 bg-blue-500/10 text-blue-400"
                : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] hover:text-white"
            }`}
          >
            <Filter className="size-3.5" />
            <span>Filters</span>
            {hasActiveFilters && (
              <span className="flex size-4 items-center justify-center rounded-full bg-blue-500 text-[9px] font-bold text-white">
                !
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Expandable Filter Drawer / Panel */}
      {showFilters && (
        <div className="mt-3 border border-[var(--border)] bg-[var(--surface)] p-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {/* Service Status */}
            <div>
              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Service Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as CustomerServiceStatus | "")}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-2.5 text-xs text-white outline-none focus:border-blue-500"
              >
                <option value="">All Service Statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="GRACE_PERIOD">Grace Period</option>
                <option value="SUSPENSION_PENDING">Suspension Pending</option>
                <option value="SUSPENDED_NON_PAYMENT">Suspended (Non-Payment)</option>
                <option value="RESTORE_PENDING">Restore Pending</option>
              </select>
            </div>

            {/* Customer Status */}
            <div>
              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Customer Status
              </label>
              <select
                value={activeFilter}
                onChange={(e) => setActiveFilter(e.target.value)}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-2.5 text-xs text-white outline-none focus:border-blue-500"
              >
                <option value="">All Customer States</option>
                <option value="true">Active Customer</option>
                <option value="false">Inactive Customer</option>
              </select>
            </div>

            {/* City Filter */}
            <div>
              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Operating City
              </label>
              <select
                value={cityFilter}
                onChange={(e) => setCityFilter(e.target.value)}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-2.5 text-xs text-white outline-none focus:border-blue-500"
              >
                <option value="">All Cities</option>
                {cities.map((city) => (
                  <option key={city.id} value={city.name}>
                    {city.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Area Filter */}
            <div>
              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Service Area
              </label>
              <select
                disabled={!cityFilter}
                value={areaFilter}
                onChange={(e) => setAreaFilter(e.target.value)}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-2.5 text-xs text-white outline-none focus:border-blue-500 disabled:opacity-40"
              >
                <option value="">
                  {!cityFilter ? "Select City First" : "All Areas in City"}
                </option>
                {areas.map((area) => (
                  <option key={area.id} value={area.name}>
                    {area.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Internet Package */}
            <div>
              <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Internet Package
              </label>
              <select
                value={packageFilter}
                onChange={(e) => setPackageFilter(e.target.value)}
                className="h-9 w-full border border-[var(--border)] bg-[var(--background)] px-2.5 text-xs text-white outline-none focus:border-blue-500"
              >
                <option value="">All Packages</option>
                {packages.map((pkg) => (
                  <option key={pkg.id} value={pkg.id}>
                    {pkg.name} ({pkg.download_speed_mbps}M)
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="mt-4">
        {loading ? (
          <div className="border border-[var(--border)] bg-[var(--surface)] p-6">
            <div className="space-y-4">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          </div>
        ) : error ? (
          <ErrorState
            title="Failed to Load Customers"
            message={error}
            onRetry={() => void loadCustomers()}
          />
        ) : customers.length === 0 ? (
          <EmptyState
            title={hasActiveFilters ? "No Matching Customers" : "No Subscribers Yet"}
            description={
              hasActiveFilters
                ? "No customer records matched your search query and filters. Try resetting the filters."
                : "No customer accounts exist in your organization yet. Activate your first subscriber."
            }
            actionLabel={hasActiveFilters ? "Reset Filters" : "Add Customer"}
            actionHref={hasActiveFilters ? undefined : "/customers/new"}
            onActionClick={hasActiveFilters ? resetFilters : undefined}
          />
        ) : (
          <CustomersTable customers={customers} />
        )}
      </div>
    </div>
  );
}