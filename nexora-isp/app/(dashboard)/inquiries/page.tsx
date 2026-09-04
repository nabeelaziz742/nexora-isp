"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  Building2,
  Calendar,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Filter,
  Layers,
  MapPin,
  Phone,
  Plus,
  RefreshCw,
  Search,
  UserCheck,
  UserPlus,
  X,
  XCircle,
} from "lucide-react";

import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Skeleton from "@/components/ui/Skeleton";
import {
  inquiriesService,
  type FeasibilityAssessmentItem,
  type FeasibilityStatus,
  type InquiryCreatePayload,
  type InquiryItem,
  type InquiryStatus,
  type NotFeasibleReason,
} from "@/services/inquiries.service";
import { customersService, type InternetPackage } from "@/services/customers.service";
import { geoService, type City, type Area } from "@/services/geo.service";
import { dealersService, type DealerItem } from "@/services/dealers.service";

const STATUS_CONFIG: Record<
  InquiryStatus,
  { label: string; badgeClass: string }
> = {
  NEW: {
    label: "New Lead",
    badgeClass: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  },
  CONTACTED: {
    label: "Contacted",
    badgeClass: "bg-sky-500/10 text-sky-400 border-sky-500/30",
  },
  FEASIBILITY_PENDING: {
    label: "Feasibility Pending",
    badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  },
  FEASIBLE: {
    label: "Feasible",
    badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  },
  NOT_FEASIBLE: {
    label: "Not Feasible",
    badgeClass: "bg-rose-500/10 text-rose-400 border-rose-500/30",
  },
  FOLLOW_UP: {
    label: "Follow Up",
    badgeClass: "bg-purple-500/10 text-purple-400 border-purple-500/30",
  },
  CONVERTED: {
    label: "Converted",
    badgeClass: "bg-emerald-600/20 text-emerald-300 border-emerald-500/40",
  },
  LOST: {
    label: "Lost",
    badgeClass: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  },
  CANCELLED: {
    label: "Cancelled",
    badgeClass: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
  },
};

export default function InquiriesPage() {
  const [inquiries, setInquiries] = useState<InquiryItem[]>([]);
  const [packages, setPackages] = useState<InternetPackage[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [dealers, setDealers] = useState<DealerItem[]>([]);

  // Filter States
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<InquiryStatus | "">("");
  const [cityFilter, setCityFilter] = useState("");
  const [areaFilter, setAreaFilter] = useState("");
  const [packageFilter, setPackageFilter] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showFeasibilityModal, setShowFeasibilityModal] = useState(false);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [showConvertModal, setShowConvertModal] = useState(false);
  const [selectedInquiry, setSelectedInquiry] = useState<InquiryItem | null>(null);

  // Form Submissions
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  // New Inquiry Form State
  const [newInquiry, setNewInquiry] = useState<InquiryCreatePayload>({
    full_name: "",
    phone: "",
    alternate_phone: "",
    email: "",
    cnic: "",
    address_line: "",
    city: "",
    area: "",
    preferred_package: "",
    connection_type: "FIBER",
    source: "WALK_IN",
    dealer: "",
    notes: "",
    follow_up_date: "",
  });

  // Feasibility Form State
  const [feasibilityForm, setFeasibilityForm] = useState<{
    status: FeasibilityStatus;
    not_feasible_reason: NotFeasibleReason | "";
    not_feasible_details: string;
    remarks: string;
  }>({
    status: "FEASIBLE",
    not_feasible_reason: "",
    not_feasible_details: "",
    remarks: "",
  });

  // Status Transition Form State
  const [statusForm, setStatusForm] = useState<{
    status: InquiryStatus;
    notes: string;
    follow_up_date: string;
  }>({
    status: "CONTACTED",
    notes: "",
    follow_up_date: "",
  });

  // Convert Form State
  const [convertForm, setConvertForm] = useState<{
    internet_package_id: string;
    billing_day: number;
    due_day: number;
  }>({
    internet_package_id: "",
    billing_day: 1,
    due_day: 10,
  });

  // Load Filter Options
  useEffect(() => {
    async function loadOptions() {
      try {
        const [pkgs, cityList, dealerList] = await Promise.all([
          customersService.getInternetPackages({ status: "active" }),
          geoService.getCities({ status: "active" }),
          dealersService.getDealers({ status: "ACTIVE" }),
        ]);
        setPackages(pkgs);
        setCities(cityList);
        setDealers(dealerList);
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

  // Load Inquiries
  const fetchInquiries = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await inquiriesService.getInquiries({
        status: statusFilter || undefined,
        city: cityFilter || undefined,
        area: areaFilter || undefined,
        package_id: packageFilter || undefined,
        search: search.trim() || undefined,
      });
      setInquiries(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load inquiries.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInquiries();
  }, [statusFilter, cityFilter, areaFilter, packageFilter]);

  // Handle Search Debounced / Submit
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchInquiries();
  };

  const handleResetFilters = () => {
    setSearch("");
    setStatusFilter("");
    setCityFilter("");
    setAreaFilter("");
    setPackageFilter("");
  };

  // Stats Calculations
  const stats = useMemo(() => {
    const total = inquiries.length;
    const pending = inquiries.filter((i) => i.status === "FEASIBILITY_PENDING" || i.status === "NEW").length;
    const feasible = inquiries.filter((i) => i.status === "FEASIBLE").length;
    const converted = inquiries.filter((i) => i.status === "CONVERTED").length;
    const notFeasibleOrLost = inquiries.filter((i) => i.status === "NOT_FEASIBLE" || i.status === "LOST").length;
    return { total, pending, feasible, converted, notFeasibleOrLost };
  }, [inquiries]);

  // Submit Create Inquiry
  const handleCreateInquiry = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);
    try {
      await inquiriesService.createInquiry({
        ...newInquiry,
        preferred_package: newInquiry.preferred_package || undefined,
        dealer: newInquiry.dealer || undefined,
        follow_up_date: newInquiry.follow_up_date || null,
      });
      setShowCreateModal(false);
      setNewInquiry({
        full_name: "",
        phone: "",
        alternate_phone: "",
        email: "",
        cnic: "",
        address_line: "",
        city: "",
        area: "",
        preferred_package: "",
        connection_type: "FIBER",
        source: "WALK_IN",
        dealer: "",
        notes: "",
        follow_up_date: "",
      });
      fetchInquiries();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to create inquiry.");
    } finally {
      setFormSubmitting(false);
    }
  };

  // Submit Feasibility Assessment
  const handleRecordFeasibility = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInquiry) return;
    setFormSubmitting(true);
    setFormError(null);
    try {
      await inquiriesService.createFeasibility({
        inquiry: selectedInquiry.id,
        address_line: selectedInquiry.address_line,
        city: selectedInquiry.city,
        area: selectedInquiry.area,
        package: selectedInquiry.preferred_package || undefined,
        connection_type: selectedInquiry.connection_type,
        status: feasibilityForm.status,
        remarks: feasibilityForm.remarks,
      });
      setShowFeasibilityModal(false);
      fetchInquiries();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to record feasibility assessment.");
    } finally {
      setFormSubmitting(false);
    }
  };

  // Submit Status Transition
  const handleStatusTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInquiry) return;
    setFormSubmitting(true);
    setFormError(null);
    try {
      await inquiriesService.transitionStatus(selectedInquiry.id, {
        status: statusForm.status,
        notes: statusForm.notes,
        follow_up_date: statusForm.follow_up_date || null,
      });
      setShowStatusModal(false);
      fetchInquiries();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to update status.");
    } finally {
      setFormSubmitting(false);
    }
  };

  // Submit Convert to Customer
  const handleConvertInquiry = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInquiry) return;
    setFormSubmitting(true);
    setFormError(null);
    try {
      const res = await inquiriesService.convertInquiry(selectedInquiry.id, {
        internet_package_id: convertForm.internet_package_id,
        billing_day: convertForm.billing_day,
        due_day: convertForm.due_day,
      });
      setFormSuccess(`Successfully converted inquiry! Customer ID: ${res.customer_id}`);
      setTimeout(() => {
        setShowConvertModal(false);
        setFormSuccess(null);
        fetchInquiries();
      }, 1500);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to convert inquiry.");
    } finally {
      setFormSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Inquiries & Leads
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Track prospective subscribers, conduct network feasibility assessments, and convert leads to active customer accounts.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchInquiries()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => {
              setFormError(null);
              setShowCreateModal(true);
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 transition shadow-emerald-950/20"
          >
            <Plus className="h-4 w-4" />
            New Inquiry
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <ClipboardList className="h-4 w-4 text-blue-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Total Leads</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-white">{stats.total}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <Layers className="h-4 w-4 text-amber-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Pending / New</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-400">{stats.pending}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <ClipboardCheck className="h-4 w-4 text-emerald-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Feasible</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-400">{stats.feasible}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <UserCheck className="h-4 w-4 text-sky-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Converted</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-sky-400">{stats.converted}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-slate-400">
            <XCircle className="h-4 w-4 text-rose-400" />
            <span className="text-xs font-medium uppercase tracking-wider">Not Feasible / Lost</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-rose-400">{stats.notFeasibleOrLost}</p>
        </div>
      </div>

      {/* Search and Filters Bar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-sm space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <form onSubmit={handleSearchSubmit} className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by inquiry #, customer name, phone..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950/80 pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </form>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition ${
                showFilters || statusFilter || cityFilter || areaFilter || packageFilter
                  ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400"
                  : "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              <Filter className="h-4 w-4" />
              Filters
              {(statusFilter || cityFilter || areaFilter || packageFilter) && (
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
              )}
            </button>
            {(search || statusFilter || cityFilter || areaFilter || packageFilter) && (
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

        {/* Expandable Filter Row */}
        {showFilters && (
          <div className="grid grid-cols-1 gap-3 pt-3 border-t border-slate-800 sm:grid-cols-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as InquiryStatus | "")}
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
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Package</label>
              <select
                value={packageFilter}
                onChange={(e) => setPackageFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
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
        )}
      </div>

      {/* Table Section */}
      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={fetchInquiries} />
      ) : inquiries.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No inquiries found"
          description="No customer inquiries or prospective leads match your current search and filter criteria."
          actionLabel="Create First Inquiry"
          onActionClick={() => setShowCreateModal(true)}
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-slate-800 bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 pl-4 pr-3 font-semibold">Inquiry #</th>
                  <th className="px-3 py-3.5 font-semibold">Prospect</th>
                  <th className="px-3 py-3.5 font-semibold">Location</th>
                  <th className="px-3 py-3.5 font-semibold">Package & Type</th>
                  <th className="px-3 py-3.5 font-semibold">Dealer / Source</th>
                  <th className="px-3 py-3.5 font-semibold">Status</th>
                  <th className="px-3 py-3.5 font-semibold">Follow-Up</th>
                  <th className="py-3.5 pl-3 pr-4 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {inquiries.map((item) => {
                  const statusConf = STATUS_CONFIG[item.status] || {
                    label: item.status,
                    badgeClass: "bg-slate-500/10 text-slate-400 border-slate-500/30",
                  };
                  return (
                    <tr key={item.id} className="hover:bg-slate-800/30 transition">
                      <td className="whitespace-nowrap py-4 pl-4 pr-3 font-mono text-xs font-semibold text-emerald-400">
                        <Link href={`/inquiries/${item.id}`} className="hover:underline">
                          {item.inquiry_number}
                        </Link>
                      </td>
                      <td className="px-3 py-4">
                        <div className="font-medium text-white">{item.full_name}</div>
                        <div className="flex items-center gap-1.5 text-xs text-slate-400">
                          <Phone className="h-3 w-3" />
                          {item.phone}
                        </div>
                      </td>
                      <td className="px-3 py-4 text-xs">
                        <div className="flex items-center gap-1 text-slate-200">
                          <MapPin className="h-3 w-3 text-slate-500" />
                          {item.area}, {item.city}
                        </div>
                        <div className="text-slate-500 truncate max-w-[180px]">
                          {item.address_line}
                        </div>
                      </td>
                      <td className="px-3 py-4 text-xs">
                        <div className="font-medium text-slate-200">
                          {item.preferred_package_name || "Custom"}
                        </div>
                        <div className="text-slate-400 font-mono text-[11px]">
                          {item.connection_type}
                        </div>
                      </td>
                      <td className="px-3 py-4 text-xs">
                        {item.dealer_name ? (
                          <div className="flex items-center gap-1 text-amber-400 font-medium">
                            <Building2 className="h-3 w-3" />
                            {item.dealer_name}
                          </div>
                        ) : (
                          <span className="text-slate-400 capitalize">{item.source.toLowerCase()}</span>
                        )}
                      </td>
                      <td className="px-3 py-4">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusConf.badgeClass}`}
                        >
                          {statusConf.label}
                        </span>
                      </td>
                      <td className="px-3 py-4 text-xs text-slate-400 whitespace-nowrap">
                        {item.follow_up_date ? (
                          <div className="flex items-center gap-1 text-purple-400">
                            <Calendar className="h-3 w-3" />
                            {item.follow_up_date}
                          </div>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="py-4 pl-3 pr-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Feasibility Check Action */}
                          {item.status !== "CONVERTED" && item.status !== "CANCELLED" && (
                            <button
                              onClick={() => {
                                setSelectedInquiry(item);
                                setFeasibilityForm({
                                  status: "FEASIBLE",
                                  not_feasible_reason: "",
                                  not_feasible_details: "",
                                  remarks: "",
                                });
                                setFormError(null);
                                setShowFeasibilityModal(true);
                              }}
                              title="Record Feasibility"
                              className="rounded-lg border border-slate-700 bg-slate-800 p-1.5 text-slate-300 hover:bg-slate-700 hover:text-white transition"
                            >
                              <ClipboardCheck className="h-3.5 w-3.5 text-amber-400" />
                            </button>
                          )}

                          {/* Convert to Customer Action */}
                          {item.status === "FEASIBLE" && !item.converted_customer && (
                            <button
                              onClick={() => {
                                setSelectedInquiry(item);
                                setConvertForm({
                                  internet_package_id: item.preferred_package || packages[0]?.id || "",
                                  billing_day: 1,
                                  due_day: 10,
                                });
                                setFormError(null);
                                setShowConvertModal(true);
                              }}
                              title="Convert to Active Customer"
                              className="rounded-lg bg-emerald-600/20 border border-emerald-500/40 p-1.5 text-emerald-300 hover:bg-emerald-600 hover:text-white transition"
                            >
                              <UserPlus className="h-3.5 w-3.5" />
                            </button>
                          )}

                          {/* Status Transition Action */}
                          {item.status !== "CONVERTED" && (
                            <button
                              onClick={() => {
                                setSelectedInquiry(item);
                                setStatusForm({
                                  status: item.status,
                                  notes: "",
                                  follow_up_date: item.follow_up_date || "",
                                });
                                setFormError(null);
                                setShowStatusModal(true);
                              }}
                              title="Update Status"
                              className="rounded-lg border border-slate-700 bg-slate-800 p-1.5 text-slate-300 hover:bg-slate-700 hover:text-white transition"
                            >
                              <RefreshCw className="h-3.5 w-3.5" />
                            </button>
                          )}

                          {/* Detail View */}
                          <Link
                            href={`/inquiries/${item.id}`}
                            className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                          >
                            Details
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

      {/* CREATE INQUIRY MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-white">Create New Inquiry / Lead</h3>
                <p className="text-xs text-slate-400">Capture customer lead details for network feasibility assessment</p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateInquiry} className="mt-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Full Name <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={newInquiry.full_name}
                    onChange={(e) => setNewInquiry({ ...newInquiry, full_name: e.target.value })}
                    placeholder="e.g. Tariq Mehmood"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Primary Phone <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={newInquiry.phone}
                    onChange={(e) => setNewInquiry({ ...newInquiry, phone: e.target.value })}
                    placeholder="e.g. 03001234567"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Alternate Phone</label>
                  <input
                    type="text"
                    value={newInquiry.alternate_phone || ""}
                    onChange={(e) => setNewInquiry({ ...newInquiry, alternate_phone: e.target.value })}
                    placeholder="e.g. 03219876543"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Email</label>
                  <input
                    type="email"
                    value={newInquiry.email || ""}
                    onChange={(e) => setNewInquiry({ ...newInquiry, email: e.target.value })}
                    placeholder="prospect@example.com"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">CNIC / ID</label>
                  <input
                    type="text"
                    value={newInquiry.cnic || ""}
                    onChange={(e) => setNewInquiry({ ...newInquiry, cnic: e.target.value })}
                    placeholder="37405-XXXXXXX-X"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    City <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={newInquiry.city}
                    onChange={(e) => setNewInquiry({ ...newInquiry, city: e.target.value })}
                    placeholder="e.g. Islamabad"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Area / Sector <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={newInquiry.area}
                    onChange={(e) => setNewInquiry({ ...newInquiry, area: e.target.value })}
                    placeholder="e.g. Sector G-11"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Full Street Address <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={newInquiry.address_line}
                  onChange={(e) => setNewInquiry({ ...newInquiry, address_line: e.target.value })}
                  placeholder="House/Flat #, Street #, Sector/Block"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Preferred Package</label>
                  <select
                    value={newInquiry.preferred_package || ""}
                    onChange={(e) => setNewInquiry({ ...newInquiry, preferred_package: e.target.value })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="">Select Package</option>
                    {packages.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.download_speed_mbps} Mbps - PKR {p.monthly_price})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Connection Type</label>
                  <select
                    value={newInquiry.connection_type}
                    onChange={(e) => setNewInquiry({ ...newInquiry, connection_type: e.target.value })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="FIBER">Fiber (GPON / FTTH)</option>
                    <option value="WIRELESS">Wireless (P2P / AirMax)</option>
                    <option value="COPPER">Copper / Ethernet</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Dealer / Sub-ISP</label>
                  <select
                    value={newInquiry.dealer || ""}
                    onChange={(e) => setNewInquiry({ ...newInquiry, dealer: e.target.value })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="">Direct ISP (No Dealer)</option>
                    {dealers.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.dealer_code} - {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Lead Source</label>
                  <select
                    value={newInquiry.source}
                    onChange={(e) => setNewInquiry({ ...newInquiry, source: e.target.value })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="WALK_IN">Walk In</option>
                    <option value="PHONE">Phone Call</option>
                    <option value="WEBSITE">Website</option>
                    <option value="SOCIAL_MEDIA">Social Media</option>
                    <option value="FIELD_AGENT">Field Agent</option>
                    <option value="DEALER">Dealer / Sub-ISP</option>
                    <option value="REFERRAL">Referral</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Follow-up Date</label>
                  <input
                    type="date"
                    value={newInquiry.follow_up_date || ""}
                    onChange={(e) => setNewInquiry({ ...newInquiry, follow_up_date: e.target.value })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Internal Notes</label>
                <textarea
                  rows={2}
                  value={newInquiry.notes || ""}
                  onChange={(e) => setNewInquiry({ ...newInquiry, notes: e.target.value })}
                  placeholder="Special instructions or lead requirements..."
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition"
                >
                  {formSubmitting ? "Creating..." : "Save Inquiry"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* FEASIBILITY MODAL */}
      {showFeasibilityModal && selectedInquiry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-white">Record Feasibility Assessment</h3>
                <p className="text-xs text-slate-400">
                  {selectedInquiry.inquiry_number} — {selectedInquiry.full_name}
                </p>
              </div>
              <button
                onClick={() => setShowFeasibilityModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleRecordFeasibility} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Assessment Status</label>
                <select
                  value={feasibilityForm.status}
                  onChange={(e) => setFeasibilityForm({ ...feasibilityForm, status: e.target.value as FeasibilityStatus })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  <option value="FEASIBLE">FEASIBLE (Ready for installation)</option>
                  <option value="NOT_FEASIBLE">NOT FEASIBLE (Cannot service area)</option>
                  <option value="IN_PROGRESS">IN PROGRESS (Survey ongoing)</option>
                </select>
              </div>

              {feasibilityForm.status === "NOT_FEASIBLE" && (
                <div className="space-y-3 rounded-lg border border-rose-500/30 bg-rose-950/20 p-3">
                  <div>
                    <label className="block text-xs font-medium text-rose-300 mb-1">
                      Reason for Infeasibility <span className="text-rose-400">*</span>
                    </label>
                    <select
                      required
                      value={feasibilityForm.not_feasible_reason}
                      onChange={(e) =>
                        setFeasibilityForm({ ...feasibilityForm, not_feasible_reason: e.target.value as NotFeasibleReason })
                      }
                      className="w-full rounded-lg border border-rose-700/50 bg-slate-950 px-3 py-2 text-xs text-white focus:border-rose-500 focus:outline-none"
                    >
                      <option value="">Select mandatory reason</option>
                      <option value="NO_COVERAGE">No Coverage / Outside service perimeter</option>
                      <option value="NO_PORT">No Available Port on DP / FAT</option>
                      <option value="NO_NODE">No Suitable Network Node</option>
                      <option value="CAPACITY_UNAVAILABLE">Capacity / Bandwidth Unavailable</option>
                      <option value="INFRASTRUCTURE_UNAVAILABLE">Infrastructure / Pole Access Unavailable</option>
                      <option value="DISTANCE_LIMITATION">Distance Limitation / Optical loss too high</option>
                      <option value="OTHER">Other Reason</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-rose-300 mb-1">Reason Details</label>
                    <textarea
                      rows={2}
                      value={feasibilityForm.not_feasible_details}
                      onChange={(e) =>
                        setFeasibilityForm({ ...feasibilityForm, not_feasible_details: e.target.value })
                      }
                      placeholder="e.g. Nearest DP is 650m away with no direct line of sight..."
                      className="w-full rounded-lg border border-rose-700/50 bg-slate-950 px-3 py-1.5 text-xs text-white focus:border-rose-500 focus:outline-none"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Remarks / Survey Findings</label>
                <textarea
                  rows={2}
                  value={feasibilityForm.remarks}
                  onChange={(e) => setFeasibilityForm({ ...feasibilityForm, remarks: e.target.value })}
                  placeholder="e.g. DP-04 has 2 free ports, optical signal -18 dBm..."
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowFeasibilityModal(false)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition"
                >
                  {formSubmitting ? "Saving..." : "Save Assessment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CONVERT INQUIRY MODAL */}
      {showConvertModal && selectedInquiry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-white">Convert Inquiry to Active Subscriber</h3>
                <p className="text-xs text-slate-400">
                  {selectedInquiry.inquiry_number} — {selectedInquiry.full_name}
                </p>
              </div>
              <button
                onClick={() => setShowConvertModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            {formSuccess && (
              <div className="mt-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 p-3 text-xs text-emerald-400 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>{formSuccess}</span>
              </div>
            )}

            <form onSubmit={handleConvertInquiry} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Internet Package <span className="text-rose-400">*</span>
                </label>
                <select
                  required
                  value={convertForm.internet_package_id}
                  onChange={(e) => setConvertForm({ ...convertForm, internet_package_id: e.target.value })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  {packages.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.download_speed_mbps} Mbps - PKR {p.monthly_price})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Billing Day of Month</label>
                  <input
                    type="number"
                    min={1}
                    max={28}
                    required
                    value={convertForm.billing_day}
                    onChange={(e) => setConvertForm({ ...convertForm, billing_day: parseInt(e.target.value) || 1 })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Due Day of Month</label>
                  <input
                    type="number"
                    min={1}
                    max={28}
                    required
                    value={convertForm.due_day}
                    onChange={(e) => setConvertForm({ ...convertForm, due_day: parseInt(e.target.value) || 10 })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-400 space-y-1">
                <p className="font-semibold text-slate-200">What happens upon conversion:</p>
                <p>• A permanent Customer and Service Account record is created.</p>
                <p>• An initial prorated service invoice is generated.</p>
                <p>• The inquiry status is transitioned to <strong className="text-emerald-400">CONVERTED</strong> and retained in history.</p>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowConvertModal(false)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting || !!formSuccess}
                  className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition"
                >
                  {formSubmitting ? "Converting..." : "Confirm & Activate"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* STATUS TRANSITION MODAL */}
      {showStatusModal && selectedInquiry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-white">Update Inquiry Status</h3>
                <p className="text-xs text-slate-400">{selectedInquiry.inquiry_number}</p>
              </div>
              <button
                onClick={() => setShowStatusModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleStatusTransition} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">New Status</label>
                <select
                  value={statusForm.status}
                  onChange={(e) => setStatusForm({ ...statusForm, status: e.target.value as InquiryStatus })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  {Object.entries(STATUS_CONFIG)
                    .filter(([key]) => key !== "CONVERTED")
                    .map(([key, { label }]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Follow-up Date</label>
                <input
                  type="date"
                  value={statusForm.follow_up_date}
                  onChange={(e) => setStatusForm({ ...statusForm, follow_up_date: e.target.value })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Transition Remarks / Notes</label>
                <textarea
                  rows={2}
                  value={statusForm.notes}
                  onChange={(e) => setStatusForm({ ...statusForm, notes: e.target.value })}
                  placeholder="e.g. Customer requested call next Tuesday after office hours..."
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowStatusModal(false)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition"
                >
                  {formSubmitting ? "Updating..." : "Update Status"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
