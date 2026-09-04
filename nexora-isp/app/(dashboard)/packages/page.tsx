"use client";

import { useEffect, useState, useTransition } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownUp,
  CheckCircle2,
  Edit2,
  Filter,
  Layers,
  Package,
  Plus,
  Power,
  Search,
  Trash2,
  Wifi,
  X,
} from "lucide-react";

import {
  customersService,
  InternetPackage,
  InternetPackagePayload,
} from "@/services/customers.service";
import { useToast } from "@/hooks/useToast";
import { SkeletonMetricCard, SkeletonTable } from "@/components/ui/Skeleton";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { ApiError } from "@/services/api-error";

interface FormState {
  name: string;
  code: string;
  description: string;
  download_speed_mbps: string;
  upload_speed_mbps: string;
  monthly_price: string;
  is_active: boolean;
}

const initialFormState: FormState = {
  name: "",
  code: "",
  description: "",
  download_speed_mbps: "",
  upload_speed_mbps: "",
  monthly_price: "",
  is_active: true,
};

export default function PackagesPage() {
  const { success, error: toastError } = useToast();

  const [packages, setPackages] = useState<InternetPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"active" | "inactive" | "">("");

  // Modal states
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPackage, setEditingPackage] = useState<InternetPackage | null>(null);
  const [form, setForm] = useState<FormState>(initialFormState);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [submitting, setSubmitting] = useState(false);

  // Delete modal
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [packageToDelete, setPackageToDelete] = useState<InternetPackage | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Load packages from real backend
  async function loadPackages() {
    try {
      setLoading(true);
      setError(null);
      const data = await customersService.getInternetPackages({
        search,
        status: statusFilter,
      });
      setPackages(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to connect to the package management service.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPackages();
  }, [search, statusFilter]);

  // Metric computations from real data
  const totalPackages = packages.length;
  const activePackages = packages.filter((p) => p.is_active).length;
  const avgPrice =
    totalPackages > 0
      ? Math.round(
          packages.reduce((acc, p) => acc + Number(p.monthly_price), 0) /
            totalPackages
        )
      : 0;
  const maxSpeed =
    totalPackages > 0
      ? Math.max(...packages.map((p) => p.download_speed_mbps))
      : 0;

  function openCreateModal() {
    setEditingPackage(null);
    setForm(initialFormState);
    setFormErrors({});
    setModalOpen(true);
  }

  function openEditModal(pkg: InternetPackage) {
    setEditingPackage(pkg);
    setForm({
      name: pkg.name,
      code: pkg.code,
      description: pkg.description || "",
      download_speed_mbps: String(pkg.download_speed_mbps),
      upload_speed_mbps: String(pkg.upload_speed_mbps),
      monthly_price: String(pkg.monthly_price),
      is_active: pkg.is_active,
    });
    setFormErrors({});
    setModalOpen(true);
  }

  function validateForm(): boolean {
    const errs: Partial<Record<keyof FormState, string>> = {};

    if (!form.name.trim()) errs.name = "Package name is required";
    if (!form.code.trim()) errs.code = "Package code is required";

    const down = Number(form.download_speed_mbps);
    if (!form.download_speed_mbps || isNaN(down) || down <= 0) {
      errs.download_speed_mbps = "Enter a valid download speed (> 0)";
    }

    const up = Number(form.upload_speed_mbps);
    if (!form.upload_speed_mbps || isNaN(up) || up <= 0) {
      errs.upload_speed_mbps = "Enter a valid upload speed (> 0)";
    }

    const price = Number(form.monthly_price);
    if (!form.monthly_price || isNaN(price) || price < 0) {
      errs.monthly_price = "Enter a valid monthly price (≥ 0)";
    }

    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSavePackage(e: React.FormEvent) {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    const payload: InternetPackagePayload = {
      name: form.name.trim(),
      code: form.code.trim().toUpperCase(),
      description: form.description.trim(),
      download_speed_mbps: Number(form.download_speed_mbps),
      upload_speed_mbps: Number(form.upload_speed_mbps),
      monthly_price: Number(form.monthly_price),
      is_active: form.is_active,
    };

    try {
      if (editingPackage) {
        await customersService.updateInternetPackage(editingPackage.id, payload);
        success(`Package "${payload.name}" updated successfully.`);
      } else {
        await customersService.createInternetPackage(payload);
        success(`Package "${payload.name}" created successfully.`);
      }
      setModalOpen(false);
      loadPackages();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Failed to save internet package.";
      toastError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleStatus(pkg: InternetPackage) {
    try {
      const updated = await customersService.toggleInternetPackageStatus(pkg.id);
      success(
        `Package "${pkg.name}" is now ${updated.is_active ? "Active" : "Inactive"}.`
      );
      setPackages((prev) =>
        prev.map((p) => (p.id === pkg.id ? { ...p, is_active: updated.is_active } : p))
      );
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "Failed to toggle package status.";
      toastError(msg);
    }
  }

  async function handleDeletePackage() {
    if (!packageToDelete) return;

    setDeleting(true);
    try {
      await customersService.deleteInternetPackage(packageToDelete.id);
      success(`Package "${packageToDelete.name}" was deleted successfully.`);
      setDeleteModalOpen(false);
      setPackageToDelete(null);
      loadPackages();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Failed to delete package. It may be assigned to existing subscribers.";
      toastError(msg);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-blue-400">
              Broadband Configuration
            </span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white">
            Packages & Bandwidth Plans
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Configure speed tiers, rate limits, monthly recurring prices, and subscriber service profiles.
          </p>
        </div>

        <button
          type="button"
          onClick={openCreateModal}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-md shadow-blue-600/20 transition hover:bg-blue-500"
        >
          <Plus className="h-4 w-4" />
          Create New Package
        </button>
      </div>

      {/* KPI Metrics Summary (Backed by Real API Data) */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:gap-4">
        {loading && packages.length === 0 ? (
          <>
            <SkeletonMetricCard />
            <SkeletonMetricCard />
            <SkeletonMetricCard />
            <SkeletonMetricCard />
          </>
        ) : (
          <>
            <div className="border border-[#202938] bg-[#0D1117] p-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Total Plans
                </span>
                <Package className="h-4 w-4 text-blue-400" />
              </div>
              <p className="mt-2 text-2xl font-bold text-white">{totalPackages}</p>
              <p className="mt-1 text-[11px] text-slate-500">Configured in system</p>
            </div>

            <div className="border border-[#202938] bg-[#0D1117] p-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Active Plans
                </span>
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              </div>
              <p className="mt-2 text-2xl font-bold text-white">{activePackages}</p>
              <p className="mt-1 text-[11px] text-emerald-400">
                {totalPackages > 0
                  ? `${Math.round((activePackages / totalPackages) * 100)}% available`
                  : "0 available"}
              </p>
            </div>

            <div className="border border-[#202938] bg-[#0D1117] p-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Average Price
                </span>
                <Activity className="h-4 w-4 text-amber-400" />
              </div>
              <p className="mt-2 text-2xl font-bold text-white">
                Rs. {avgPrice.toLocaleString()}
              </p>
              <p className="mt-1 text-[11px] text-slate-500">Per monthly cycle</p>
            </div>

            <div className="border border-[#202938] bg-[#0D1117] p-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Top Speed
                </span>
                <Wifi className="h-4 w-4 text-purple-400" />
              </div>
              <p className="mt-2 text-2xl font-bold text-white">{maxSpeed} Mbps</p>
              <p className="mt-1 text-[11px] text-purple-400">Max downstream tier</p>
            </div>
          </>
        )}
      </div>

      {/* Filters & Search Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border border-[#202938] bg-[#0D1117] p-3">
        <div className="relative flex-1 max-w-md">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search packages by name or code..."
            className="w-full rounded-md border border-[#202938] bg-[#070A0F] py-1.5 pl-9 pr-3 text-xs text-white placeholder:text-slate-600 outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-slate-500" />
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as "active" | "inactive" | "")
            }
            className="rounded-md border border-[#202938] bg-[#070A0F] px-3 py-1.5 text-xs text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive Only</option>
          </select>
        </div>
      </div>

      {/* Error state */}
      {error && <ErrorState message={error} onRetry={loadPackages} />}

      {/* Loading state table */}
      {loading && !error && <SkeletonTable columns={6} rows={5} />}

      {/* Packages Data Grid */}
      {!loading && !error && packages.length === 0 && (
        <EmptyState
          title="No Internet Packages Found"
          description={
            search || statusFilter
              ? "No packages matched your search filters. Try adjusting your search query."
              : "No internet packages have been created yet. Create your first broadband plan to get started."
          }
          icon={Package}
          actionLabel="Create Package"
          onActionClick={openCreateModal}
        />
      )}

      {!loading && !error && packages.length > 0 && (
        <div className="overflow-x-auto border border-[#202938] bg-[#0D1117]">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#202938] bg-[#0A0E14] text-[10px] uppercase tracking-wider text-slate-400">
                <th className="px-4 py-3">Package / Plan</th>
                <th className="px-4 py-3">Code</th>
                <th className="px-4 py-3">Bandwidth Speeds</th>
                <th className="px-4 py-3">Monthly Price</th>
                <th className="px-4 py-3">Subscribers</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#182131]">
              {packages.map((pkg) => (
                <tr
                  key={pkg.id}
                  className="transition hover:bg-[#121821]/50"
                >
                  <td className="px-4 py-3.5">
                    <div>
                      <p className="font-semibold text-slate-100">{pkg.name}</p>
                      {pkg.description && (
                        <p className="text-[11px] text-slate-500 line-clamp-1 max-w-xs">
                          {pkg.description}
                        </p>
                      )}
                    </div>
                  </td>

                  <td className="px-4 py-3.5">
                    <span className="font-mono text-[11px] text-slate-400">
                      {pkg.code}
                    </span>
                  </td>

                  <td className="px-4 py-3.5">
                    <div className="inline-flex items-center gap-1.5 rounded-sm border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 font-mono text-[11px] text-blue-400">
                      <ArrowDownUp className="h-3 w-3" />
                      <span>{pkg.download_speed_mbps} Mbps ↓</span>
                      <span className="text-slate-600">/</span>
                      <span>{pkg.upload_speed_mbps} Mbps ↑</span>
                    </div>
                  </td>

                  <td className="px-4 py-3.5">
                    <span className="font-semibold text-slate-100">
                      Rs. {Number(pkg.monthly_price).toLocaleString()}
                    </span>
                    <span className="text-[10px] text-slate-500"> / mo</span>
                  </td>

                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-1.5 text-slate-300">
                      <Layers className="h-3.5 w-3.5 text-slate-500" />
                      <span>{pkg.subscribers_count ?? 0}</span>
                    </div>
                  </td>

                  <td className="px-4 py-3.5">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        pkg.is_active
                          ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                          : "border border-slate-700 bg-slate-800 text-slate-400"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          pkg.is_active ? "bg-emerald-400" : "bg-slate-500"
                        }`}
                      />
                      {pkg.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>

                  <td className="px-4 py-3.5 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => openEditModal(pkg)}
                        aria-label={`Edit ${pkg.name}`}
                        className="rounded-md border border-[#202938] bg-[#070A0F] p-1.5 text-slate-400 transition hover:border-blue-500 hover:text-blue-400"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>

                      <button
                        type="button"
                        onClick={() => handleToggleStatus(pkg)}
                        aria-label={`Toggle status for ${pkg.name}`}
                        title={pkg.is_active ? "Deactivate" : "Activate"}
                        className={`rounded-md border border-[#202938] bg-[#070A0F] p-1.5 transition ${
                          pkg.is_active
                            ? "text-slate-400 hover:text-amber-400"
                            : "text-slate-500 hover:text-emerald-400"
                        }`}
                      >
                        <Power className="h-3.5 w-3.5" />
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setPackageToDelete(pkg);
                          setDeleteModalOpen(true);
                        }}
                        aria-label={`Delete ${pkg.name}`}
                        className="rounded-md border border-[#202938] bg-[#070A0F] p-1.5 text-slate-400 transition hover:border-red-500/40 hover:text-red-400"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit Package Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-lg border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-4">
              <h2 className="text-base font-bold text-white">
                {editingPackage ? "Edit Internet Package" : "Create Internet Package"}
              </h2>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSavePackage} className="mt-4 space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  Package Name *
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Fiber Ultra 50 Mbps"
                  className={`w-full rounded-md border bg-[#070A0F] px-3 py-2 text-xs text-white outline-none placeholder:text-slate-600 focus:ring-1 ${
                    formErrors.name
                      ? "border-red-500 focus:border-red-500"
                      : "border-[#202938] focus:border-blue-500 focus:ring-blue-500/20"
                  }`}
                />
                {formErrors.name && (
                  <p className="mt-1 text-[11px] text-red-400">{formErrors.name}</p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  Package Code / SKU *
                </label>
                <input
                  type="text"
                  value={form.code}
                  onChange={(e) =>
                    setForm({ ...form, code: e.target.value.toUpperCase() })
                  }
                  placeholder="e.g. FIBER-50M"
                  className={`w-full rounded-md border bg-[#070A0F] px-3 py-2 text-xs uppercase font-mono text-white outline-none placeholder:text-slate-600 focus:ring-1 ${
                    formErrors.code
                      ? "border-red-500 focus:border-red-500"
                      : "border-[#202938] focus:border-blue-500 focus:ring-blue-500/20"
                  }`}
                />
                {formErrors.code && (
                  <p className="mt-1 text-[11px] text-red-400">{formErrors.code}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-300">
                    Download Speed (Mbps) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={form.download_speed_mbps}
                    onChange={(e) =>
                      setForm({ ...form, download_speed_mbps: e.target.value })
                    }
                    placeholder="50"
                    className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                  />
                  {formErrors.download_speed_mbps && (
                    <p className="mt-1 text-[11px] text-red-400">
                      {formErrors.download_speed_mbps}
                    </p>
                  )}
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-300">
                    Upload Speed (Mbps) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={form.upload_speed_mbps}
                    onChange={(e) =>
                      setForm({ ...form, upload_speed_mbps: e.target.value })
                    }
                    placeholder="25"
                    className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                  />
                  {formErrors.upload_speed_mbps && (
                    <p className="mt-1 text-[11px] text-red-400">
                      {formErrors.upload_speed_mbps}
                    </p>
                  )}
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  Monthly Recurring Price (PKR) *
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.monthly_price}
                  onChange={(e) =>
                    setForm({ ...form, monthly_price: e.target.value })
                  }
                  placeholder="3500.00"
                  className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                />
                {formErrors.monthly_price && (
                  <p className="mt-1 text-[11px] text-red-400">
                    {formErrors.monthly_price}
                  </p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  Description / Service Details
                </label>
                <textarea
                  rows={2}
                  value={form.description}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                  placeholder="Unlimited fiber internet, includes optical ONT support..."
                  className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs text-white outline-none placeholder:text-slate-600 focus:border-blue-500"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  id="package_is_active"
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) =>
                    setForm({ ...form, is_active: e.target.checked })
                  }
                  className="h-4 w-4 rounded border-[#202938] bg-[#070A0F] text-blue-600 accent-blue-600"
                />
                <label
                  htmlFor="package_is_active"
                  className="text-xs text-slate-300 cursor-pointer select-none"
                >
                  Active and available for subscriber provisioning
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  disabled={submitting}
                  className="rounded-md border border-[#202938] px-4 py-2 text-xs font-medium text-slate-300 transition hover:bg-[#121821]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-md transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {submitting && <LoadingSpinner size="xs" tone="white" />}
                  {editingPackage ? "Update Package" : "Create Package"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && packageToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-lg border border-red-500/30 bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-red-400">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-base font-bold text-white">
                Confirm Package Deletion
              </h3>
            </div>

            <p className="mt-3 text-xs leading-relaxed text-slate-300">
              Are you sure you want to delete the package{" "}
              <strong className="text-white">"{packageToDelete.name}"</strong>?
            </p>

            {packageToDelete.subscribers_count &&
            packageToDelete.subscribers_count > 0 ? (
              <div className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
                ⚠️ This package is currently assigned to{" "}
                <strong>{packageToDelete.subscribers_count}</strong> subscriber(s).
                The system will prevent deletion to preserve billing integrity.
                Deactivate it instead.
              </div>
            ) : null}

            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setDeleteModalOpen(false);
                  setPackageToDelete(null);
                }}
                disabled={deleting}
                className="rounded-md border border-[#202938] px-4 py-2 text-xs font-medium text-slate-300 transition hover:bg-[#121821]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeletePackage}
                disabled={deleting}
                className="inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-xs font-semibold text-white shadow-md transition hover:bg-red-500 disabled:opacity-50"
              >
                {deleting && <LoadingSpinner size="xs" tone="white" />}
                Delete Package
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
