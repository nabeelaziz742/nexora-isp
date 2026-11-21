"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Building2,
  CalendarDays,
  CheckCircle2,
  DollarSign,
  Filter,
  MapPin,
  Percent,
  Pencil,
  Phone,
  Plus,
  Power,
  RefreshCw,
  Search,
  Users,
  X,
} from "lucide-react";

import DealerFormModal from "@/components/dealers/DealerFormModal";
import ExpenseRequestsLink from "@/components/dealers/ExpenseRequestsLink";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Skeleton from "@/components/ui/Skeleton";
import {
  dealersService,
  type DealerItem,
  type DealerStatus,
} from "@/services/dealers.service";
import { geoService, type City, type Area } from "@/services/geo.service";

const STATUS_CONFIG: Record<
  DealerStatus,
  { label: string; badgeClass: string }
> = {
  ACTIVE: {
    label: "Active",
    badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  },
  INACTIVE: {
    label: "Inactive",
    badgeClass: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  },
  SUSPENDED: {
    label: "Suspended",
    badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  },
  TERMINATED: {
    label: "Terminated",
    badgeClass: "bg-rose-500/10 text-rose-400 border-rose-500/30",
  },
};

export default function DealersPage() {
  const [dealers, setDealers] = useState<DealerItem[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);

  // Filter States
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<DealerStatus | "">("");
  const [cityFilter, setCityFilter] = useState("");
  const [areaFilter, setAreaFilter] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals & Action States: null = closed, "new" = register, a dealer = edit
  const [formDealer, setFormDealer] = useState<DealerItem | "new" | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  // Load Geographic Options
  useEffect(() => {
    async function loadOptions() {
      try {
        const cityList = await geoService.getCities({ status: "active" });
        setCities(cityList);
      } catch {
        // Silently handle
      }
    }
    loadOptions();
  }, []);

  // Update areas when city filter changes
  useEffect(() => {
    if (!cityFilter) {
      setAreas([]);
      setAreaFilter("");
      return;
    }
    const selectedCity = cities.find((c) => c.name === cityFilter);
    if (selectedCity) {
      geoService
        .getAreas({ city: selectedCity.name, status: "active" })
        .then(setAreas)
        .catch(() => setAreas([]));
    }
  }, [cityFilter, cities]);

  // Fetch Dealers
  const fetchDealers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await dealersService.getDealers({
        status: statusFilter || undefined,
        city: cityFilter || undefined,
        area: areaFilter || undefined,
        search: search.trim() || undefined,
      });
      setDealers(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load dealers.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDealers();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- search text is applied on submit/Enter, not on every keystroke
  }, [statusFilter, cityFilter, areaFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchDealers();
  };

  const handleResetFilters = () => {
    setSearch("");
    setStatusFilter("");
    setCityFilter("");
    setAreaFilter("");
  };

  // Stats
  const stats = useMemo(() => {
    const total = dealers.length;
    const active = dealers.filter((d) => d.status === "ACTIVE").length;
    const totalSubscribers = dealers.reduce((acc, d) => acc + (d.customers_count || 0), 0);
    return { total, active, totalSubscribers };
  }, [dealers]);

  // Status Toggle
  const handleToggleStatus = async (dealerId: string) => {
    setTogglingId(dealerId);
    try {
      await dealersService.toggleStatus(dealerId);
      fetchDealers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update dealer status.");
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Dealers & Sub-ISPs
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Manage authorized franchise partners, sub-operators, assigned territory boundaries, and revenue commission structures.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <ExpenseRequestsLink />
          <button
            onClick={() => fetchDealers()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => setFormDealer("new")}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 transition shadow-emerald-950/20"
          >
            <Plus className="h-4 w-4" />
            Add Dealer / Sub-ISP
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <Building2 className="h-4 w-4 text-emerald-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Total Franchisees</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-white">{stats.total}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Active Partners</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-400">{stats.active}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <Users className="h-4 w-4 text-sky-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Managed Subscribers</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-sky-400">{stats.totalSubscribers}</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-sm space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <form onSubmit={handleSearchSubmit} className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by dealer code, partner name, company or phone..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950/80 pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </form>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition ${
                showFilters || statusFilter || cityFilter || areaFilter
                  ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400"
                  : "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              <Filter className="h-4 w-4" />
              Filters
              {(statusFilter || cityFilter || areaFilter) && (
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
              )}
            </button>
            {(search || statusFilter || cityFilter || areaFilter) && (
              <button
                onClick={handleResetFilters}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-2 text-xs font-medium text-slate-400 hover:text-white transition"
              >
                <X className="h-3.5 w-3.5" />
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Expandable Filters */}
        {showFilters && (
          <div className="grid grid-cols-1 gap-3 pt-3 border-t border-slate-800 sm:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as DealerStatus | "")}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="">All Statuses</option>
                {Object.entries(STATUS_CONFIG).map(([key, { label }]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">City</label>
              <select
                value={cityFilter}
                onChange={(e) => setCityFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="">All Cities</option>
                {cities.map((city) => (
                  <option key={city.id} value={city.name}>
                    {city.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Area</label>
              <select
                value={areaFilter}
                onChange={(e) => setAreaFilter(e.target.value)}
                disabled={!cityFilter}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none disabled:opacity-50"
              >
                <option value="">All Areas</option>
                {areas.map((area) => (
                  <option key={area.id} value={area.name}>
                    {area.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Dealers Table */}
      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={fetchDealers} />
      ) : dealers.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No dealers found"
          description="You haven't added any franchise partners or sub-ISPs yet."
          actionLabel="Add First Dealer"
          onActionClick={() => setFormDealer("new")}
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-slate-800 bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 pl-4 pr-3 font-semibold">Dealer Code</th>
                  <th className="px-3 py-3.5 font-semibold">Dealer & Company</th>
                  <th className="px-3 py-3.5 font-semibold">Contact</th>
                  <th className="px-3 py-3.5 font-semibold">Territory</th>
                  <th className="px-3 py-3.5 font-semibold">Commission</th>
                  <th className="px-3 py-3.5 font-semibold">Subscribers</th>
                  <th className="px-3 py-3.5 font-semibold">Status</th>
                  <th className="py-3.5 pl-3 pr-4 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {dealers.map((item) => {
                  const statusConf = STATUS_CONFIG[item.status] || {
                    label: item.status,
                    badgeClass: "bg-slate-500/10 text-slate-400 border-slate-500/30",
                  };
                  return (
                    <tr key={item.id} className="hover:bg-slate-800/30 transition">
                      <td className="whitespace-nowrap py-4 pl-4 pr-3 font-mono text-xs font-semibold text-emerald-400">
                        <Link href={`/dealers/${item.id}`} className="hover:underline">
                          {item.dealer_code}
                        </Link>
                      </td>
                      <td className="px-3 py-4">
                        <div className="font-semibold text-white">{item.name}</div>
                        {item.parent_dealer && (
                          <div className="text-[11px] text-sky-400">Sub dealer of {item.parent_dealer_name}</div>
                        )}
                        {item.sub_dealers_count > 0 && (
                          <div className="text-[11px] text-sky-400">{item.sub_dealers_count} sub dealer{item.sub_dealers_count === 1 ? "" : "s"}</div>
                        )}
                        {item.company_name && (
                          <div className="text-xs text-slate-400 flex items-center gap-1">
                            <Building2 className="h-3 w-3" />
                            {item.company_name}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-4 text-xs">
                        <div className="flex items-center gap-1 text-slate-200 font-mono">
                          <Phone className="h-3 w-3 text-slate-500" />
                          {item.phone}
                        </div>
                        {item.email && <div className="text-slate-400">{item.email}</div>}
                      </td>
                      <td className="px-3 py-4 text-xs">
                        <div className="flex items-center gap-1 text-slate-200">
                          <MapPin className="h-3 w-3 text-slate-500" />
                          {item.assigned_area_name || item.area || "—"}, {item.city}
                        </div>
                      </td>
                      <td className="px-3 py-4 text-xs">
                        <div className="flex items-center gap-1 font-semibold text-amber-400">
                          {item.parent_dealer ? (
                            <span className="text-slate-400">Paid by {item.parent_dealer_name}</span>
                          ) : item.commission_type === "MONTHLY_SLAB" ? (
                            <>
                              <CalendarDays className="h-3 w-3" />
                              Monthly · {item.payout_slabs.length} slab{item.payout_slabs.length === 1 ? "" : "s"}
                            </>
                          ) : item.commission_type === "PERCENTAGE" ? (
                            <>
                              <Percent className="h-3 w-3" />
                              {item.commission_rate_percentage}% of billing
                            </>
                          ) : (
                            <>
                              <DollarSign className="h-3 w-3" />
                              PKR {item.commission_rate_percentage} / user
                            </>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-4 text-xs">
                        <span className="font-mono font-semibold text-sky-400">
                          {item.customers_count ?? 0}
                        </span>{" "}
                        subscribers
                      </td>
                      <td className="px-3 py-4">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusConf.badgeClass}`}
                        >
                          {statusConf.label}
                        </span>
                      </td>
                      <td className="py-4 pl-3 pr-4 text-right">
                        <div className="flex flex-wrap items-center justify-end gap-2">
                          <button
                            onClick={() => handleToggleStatus(item.id)}
                            disabled={togglingId === item.id}
                            title={item.status === "ACTIVE" ? "Deactivate Partner" : "Activate Partner"}
                            className={`rounded-lg border p-1.5 transition ${
                              item.status === "ACTIVE"
                                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                                : "border-slate-700 bg-slate-800 text-slate-400 hover:text-white"
                            }`}
                          >
                            <Power className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => setFormDealer(item)}
                            title="Edit dealer"
                            className="rounded-lg border border-slate-700 bg-slate-800 p-1.5 text-slate-300 hover:bg-slate-700 hover:text-white transition"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <Link
                            href={`/dealers/${item.id}`}
                            className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                          >
                            Dealer 360
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {formDealer && (
        <DealerFormModal
          dealer={formDealer === "new" ? null : formDealer}
          onClose={() => setFormDealer(null)}
          onSaved={() => {
            setFormDealer(null);
            fetchDealers();
          }}
        />
      )}
    </div>
  );
}
