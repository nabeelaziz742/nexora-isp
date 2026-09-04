"use client";

import { useEffect, useState } from "react";
import {
  Building,
  CheckCircle2,
  Edit2,
  Filter,
  Globe,
  MapPin,
  Plus,
  Power,
  Search,
  Trash2,
  X,
  AlertTriangle,
} from "lucide-react";

import {
  Area,
  AreaPayload,
  City,
  CityPayload,
  Country,
  CountryPayload,
  geoService,
} from "@/services/geo.service";
import { useToast } from "@/hooks/useToast";
import { SkeletonTable } from "@/components/ui/Skeleton";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { ApiError } from "@/services/api-error";

type TabType = "areas" | "cities" | "countries";

export default function AreasPage() {
  const { success, error: toastError } = useToast();

  const [activeTab, setActiveTab] = useState<TabType>("areas");

  // Data
  const [areas, setAreas] = useState<Area[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [selectedCityFilter, setSelectedCityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"active" | "inactive" | "">("");

  // Area Modal State
  const [areaModalOpen, setAreaModalOpen] = useState(false);
  const [editingArea, setEditingArea] = useState<Area | null>(null);
  const [areaForm, setAreaForm] = useState<AreaPayload>({
    name: "",
    code: "",
    postal_code: "",
    city: "",
    is_active: true,
  });

  // City Modal State
  const [cityModalOpen, setCityModalOpen] = useState(false);
  const [editingCity, setEditingCity] = useState<City | null>(null);
  const [cityForm, setCityForm] = useState<CityPayload>({
    name: "",
    code: "",
    country: "",
    is_active: true,
  });

  // Country Modal State
  const [countryModalOpen, setCountryModalOpen] = useState(false);
  const [editingCountry, setEditingCountry] = useState<Country | null>(null);
  const [countryForm, setCountryForm] = useState<CountryPayload>({
    name: "",
    code: "",
    is_active: true,
  });

  // Delete State
  const [deleteItem, setDeleteItem] = useState<{
    type: TabType;
    id: string;
    name: string;
    warning?: string;
  } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Load all reference data
  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [areasData, citiesData, countriesData] = await Promise.all([
        geoService.getAreas({
          search,
          city: selectedCityFilter,
          status: statusFilter,
        }),
        geoService.getCities(),
        geoService.getCountries(),
      ]);
      setAreas(areasData);
      setCities(citiesData);
      setCountries(countriesData);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to load geographic area hierarchy.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [search, selectedCityFilter, statusFilter, activeTab]);

  // ==================== AREA HANDLERS ====================
  function openCreateArea() {
    setEditingArea(null);
    setAreaForm({
      name: "",
      code: "",
      postal_code: "",
      city: cities[0]?.id ?? "",
      is_active: true,
    });
    setAreaModalOpen(true);
  }

  function openEditArea(area: Area) {
    setEditingArea(area);
    setAreaForm({
      name: area.name,
      code: area.code || "",
      postal_code: area.postal_code || "",
      city: area.city || "",
      is_active: area.is_active,
    });
    setAreaModalOpen(true);
  }

  async function handleSaveArea(e: React.FormEvent) {
    e.preventDefault();
    if (!areaForm.name.trim()) {
      toastError("Area name is required.");
      return;
    }

    setSubmitting(true);
    try {
      if (editingArea) {
        await geoService.updateArea(editingArea.id, areaForm);
        success(`Area "${areaForm.name}" updated successfully.`);
      } else {
        await geoService.createArea(areaForm);
        success(`Area "${areaForm.name}" created successfully.`);
      }
      setAreaModalOpen(false);
      loadData();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to save area.";
      toastError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleAreaStatus(area: Area) {
    try {
      const res = await geoService.toggleAreaStatus(area.id);
      success(`Area "${area.name}" is now ${res.is_active ? "Active" : "Inactive"}.`);
      setAreas((prev) =>
        prev.map((a) => (a.id === area.id ? { ...a, is_active: res.is_active } : a))
      );
    } catch (err) {
      toastError("Failed to update status.");
    }
  }

  // ==================== CITY HANDLERS ====================
  function openCreateCity() {
    setEditingCity(null);
    setCityForm({
      name: "",
      code: "",
      country: countries[0]?.id ?? "",
      is_active: true,
    });
    setCityModalOpen(true);
  }

  function openEditCity(city: City) {
    setEditingCity(city);
    setCityForm({
      name: city.name,
      code: city.code || "",
      country: city.country || "",
      is_active: city.is_active,
    });
    setCityModalOpen(true);
  }

  async function handleSaveCity(e: React.FormEvent) {
    e.preventDefault();
    if (!cityForm.name.trim()) {
      toastError("City name is required.");
      return;
    }

    setSubmitting(true);
    try {
      if (editingCity) {
        await geoService.updateCity(editingCity.id, cityForm);
        success(`City "${cityForm.name}" updated successfully.`);
      } else {
        await geoService.createCity(cityForm);
        success(`City "${cityForm.name}" created successfully.`);
      }
      setCityModalOpen(false);
      loadData();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to save city.";
      toastError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleCityStatus(city: City) {
    try {
      const res = await geoService.toggleCityStatus(city.id);
      success(`City "${city.name}" is now ${res.is_active ? "Active" : "Inactive"}.`);
      setCities((prev) =>
        prev.map((c) => (c.id === city.id ? { ...c, is_active: res.is_active } : c))
      );
    } catch (err) {
      toastError("Failed to update city status.");
    }
  }

  // ==================== COUNTRY HANDLERS ====================
  function openCreateCountry() {
    setEditingCountry(null);
    setCountryForm({
      name: "",
      code: "",
      is_active: true,
    });
    setCountryModalOpen(true);
  }

  function openEditCountry(country: Country) {
    setEditingCountry(country);
    setCountryForm({
      name: country.name,
      code: country.code,
      is_active: country.is_active,
    });
    setCountryModalOpen(true);
  }

  async function handleSaveCountry(e: React.FormEvent) {
    e.preventDefault();
    if (!countryForm.name.trim() || !countryForm.code.trim()) {
      toastError("Country name and code are required.");
      return;
    }

    setSubmitting(true);
    try {
      if (editingCountry) {
        await geoService.updateCountry(editingCountry.id, countryForm);
        success(`Country "${countryForm.name}" updated successfully.`);
      } else {
        await geoService.createCountry(countryForm);
        success(`Country "${countryForm.name}" created successfully.`);
      }
      setCountryModalOpen(false);
      loadData();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to save country.";
      toastError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleCountryStatus(country: Country) {
    try {
      const res = await geoService.toggleCountryStatus(country.id);
      success(
        `Country "${country.name}" is now ${res.is_active ? "Active" : "Inactive"}.`
      );
      setCountries((prev) =>
        prev.map((c) => (c.id === country.id ? { ...c, is_active: res.is_active } : c))
      );
    } catch (err) {
      toastError("Failed to update country status.");
    }
  }

  // ==================== DELETE HANDLER ====================
  async function handleConfirmDelete() {
    if (!deleteItem) return;

    setDeleting(true);
    try {
      if (deleteItem.type === "areas") {
        await geoService.deleteArea(deleteItem.id);
        success(`Area "${deleteItem.name}" deleted.`);
      } else if (deleteItem.type === "cities") {
        await geoService.deleteCity(deleteItem.id);
        success(`City "${deleteItem.name}" deleted.`);
      } else if (deleteItem.type === "countries") {
        await geoService.deleteCountry(deleteItem.id);
        success(`Country "${deleteItem.name}" deleted.`);
      }
      setDeleteItem(null);
      loadData();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Failed to delete item. It may have child relationships attached.";
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
              Operational Coverage
            </span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white">
            Areas & Geographic Hierarchy
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Define countries, operational cities, and sublocalities/areas for subscriber mapping and field recovery.
          </p>
        </div>

        <div>
          {activeTab === "areas" && (
            <button
              type="button"
              onClick={openCreateArea}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-md shadow-blue-600/20 transition hover:bg-blue-500"
            >
              <Plus className="h-4 w-4" />
              Add Area / Sublocality
            </button>
          )}

          {activeTab === "cities" && (
            <button
              type="button"
              onClick={openCreateCity}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-md shadow-blue-600/20 transition hover:bg-blue-500"
            >
              <Plus className="h-4 w-4" />
              Add City
            </button>
          )}

          {activeTab === "countries" && (
            <button
              type="button"
              onClick={openCreateCountry}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-md shadow-blue-600/20 transition hover:bg-blue-500"
            >
              <Plus className="h-4 w-4" />
              Add Country
            </button>
          )}
        </div>
      </div>

      {/* Tabs Header */}
      <div className="flex border-b border-[#202938]">
        <button
          type="button"
          onClick={() => setActiveTab("areas")}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition ${
            activeTab === "areas"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <MapPin className="h-4 w-4" />
          Sublocalities & Areas ({areas.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("cities")}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition ${
            activeTab === "cities"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Building className="h-4 w-4" />
          Cities ({cities.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("countries")}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition ${
            activeTab === "countries"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Globe className="h-4 w-4" />
          Countries ({countries.length})
        </button>
      </div>

      {/* Filter toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border border-[#202938] bg-[#0D1117] p-3">
        <div className="relative flex-1 max-w-md">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search ${activeTab}...`}
            className="w-full rounded-md border border-[#202938] bg-[#070A0F] py-1.5 pl-9 pr-3 text-xs text-white placeholder:text-slate-600 outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-2">
          {activeTab === "areas" && cities.length > 0 && (
            <select
              value={selectedCityFilter}
              onChange={(e) => setSelectedCityFilter(e.target.value)}
              className="rounded-md border border-[#202938] bg-[#070A0F] px-3 py-1.5 text-xs text-slate-300 outline-none focus:border-blue-500"
            >
              <option value="">All Cities</option>
              {cities.map((city) => (
                <option key={city.id} value={city.id}>
                  {city.name}
                </option>
              ))}
            </select>
          )}

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

      {/* Error State */}
      {error && <ErrorState message={error} onRetry={loadData} />}

      {/* Loading Skeleton */}
      {loading && !error && <SkeletonTable columns={5} rows={5} />}

      {/* ==================== AREAS TAB ==================== */}
      {!loading && !error && activeTab === "areas" && (
        <>
          {areas.length === 0 ? (
            <EmptyState
              title="No Areas Found"
              description="No sublocalities or areas have been added yet. Add an area to begin mapping subscribers."
              icon={MapPin}
              actionLabel="Add Area"
              onActionClick={openCreateArea}
            />
          ) : (
            <div className="overflow-x-auto border border-[#202938] bg-[#0D1117]">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#202938] bg-[#0A0E14] text-[10px] uppercase tracking-wider text-slate-400">
                    <th className="px-4 py-3">Area / Sublocality</th>
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">City & Country</th>
                    <th className="px-4 py-3">Postal Code</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#182131]">
                  {areas.map((area) => (
                    <tr key={area.id} className="transition hover:bg-[#121821]/50">
                      <td className="px-4 py-3.5 font-semibold text-slate-100">
                        {area.name}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-[11px] text-slate-400">
                        {area.code || "—"}
                      </td>
                      <td className="px-4 py-3.5 text-slate-300">
                        <span>{area.city_name || "Unassigned"}</span>
                        {area.country_name && (
                          <span className="text-[10px] text-slate-500">
                            {" "}
                            ({area.country_name})
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-[11px] text-slate-400">
                        {area.postal_code || "—"}
                      </td>
                      <td className="px-4 py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            area.is_active
                              ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                              : "border border-slate-700 bg-slate-800 text-slate-400"
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              area.is_active ? "bg-emerald-400" : "bg-slate-500"
                            }`}
                          />
                          {area.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => openEditArea(area)}
                            className="rounded-md border border-[#202938] bg-[#070A0F] p-1.5 text-slate-400 transition hover:border-blue-500 hover:text-blue-400"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleToggleAreaStatus(area)}
                            title={area.is_active ? "Deactivate" : "Activate"}
                            className="rounded-md border border-[#202938] bg-[#070A0F] p-1.5 text-slate-400 transition hover:text-amber-400"
                          >
                            <Power className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setDeleteItem({
                                type: "areas",
                                id: area.id,
                                name: area.name,
                              })
                            }
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
        </>
      )}

      {/* ==================== CITIES TAB ==================== */}
      {!loading && !error && activeTab === "cities" && (
        <>
          {cities.length === 0 ? (
            <EmptyState
              title="No Cities Configured"
              description="Add operational cities under which sublocalities and areas can be created."
              icon={Building}
              actionLabel="Add City"
              onActionClick={openCreateCity}
            />
          ) : (
            <div className="overflow-x-auto border border-[#202938] bg-[#0D1117]">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#202938] bg-[#0A0E14] text-[10px] uppercase tracking-wider text-slate-400">
                    <th className="px-4 py-3">City Name</th>
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">Country</th>
                    <th className="px-4 py-3">Attached Areas</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#182131]">
                  {cities.map((city) => (
                    <tr key={city.id} className="transition hover:bg-[#121821]/50">
                      <td className="px-4 py-3.5 font-semibold text-slate-100">
                        {city.name}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-[11px] text-slate-400">
                        {city.code || "—"}
                      </td>
                      <td className="px-4 py-3.5 text-slate-300">
                        {city.country_name || "—"}
                      </td>
                      <td className="px-4 py-3.5 text-slate-300">
                        {city.areas_count ?? 0} area(s)
                      </td>
                      <td className="px-4 py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            city.is_active
                              ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                              : "border border-slate-700 bg-slate-800 text-slate-400"
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              city.is_active ? "bg-emerald-400" : "bg-slate-500"
                            }`}
                          />
                          {city.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => openEditCity(city)}
                            className="rounded-md border border-[#202938] bg-[#070A0F] p-1.5 text-slate-400 transition hover:border-blue-500 hover:text-blue-400"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleToggleCityStatus(city)}
                            title={city.is_active ? "Deactivate" : "Activate"}
                            className="rounded-md border border-[#202938] bg-[#070A0F] p-1.5 text-slate-400 transition hover:text-amber-400"
                          >
                            <Power className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setDeleteItem({
                                type: "cities",
                                id: city.id,
                                name: city.name,
                                warning:
                                  city.areas_count && city.areas_count > 0
                                    ? `This city has ${city.areas_count} attached area(s). The system will prevent deletion unless areas are removed first.`
                                    : undefined,
                              })
                            }
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
        </>
      )}

      {/* ==================== COUNTRIES TAB ==================== */}
      {!loading && !error && activeTab === "countries" && (
        <>
          {countries.length === 0 ? (
            <EmptyState
              title="No Countries Configured"
              description="Add country records for multi-region operational grouping."
              icon={Globe}
              actionLabel="Add Country"
              onActionClick={openCreateCountry}
            />
          ) : (
            <div className="overflow-x-auto border border-[#202938] bg-[#0D1117]">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#202938] bg-[#0A0E14] text-[10px] uppercase tracking-wider text-slate-400">
                    <th className="px-4 py-3">Country Name</th>
                    <th className="px-4 py-3">Country Code</th>
                    <th className="px-4 py-3">Cities Attached</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#182131]">
                  {countries.map((c) => (
                    <tr key={c.id} className="transition hover:bg-[#121821]/50">
                      <td className="px-4 py-3.5 font-semibold text-slate-100">
                        {c.name}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-[11px] text-blue-400">
                        {c.code}
                      </td>
                      <td className="px-4 py-3.5 text-slate-300">
                        {c.cities_count ?? 0} city/cities
                      </td>
                      <td className="px-4 py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            c.is_active
                              ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                              : "border border-slate-700 bg-slate-800 text-slate-400"
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              c.is_active ? "bg-emerald-400" : "bg-slate-500"
                            }`}
                          />
                          {c.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => openEditCountry(c)}
                            className="rounded-md border border-[#202938] bg-[#070A0F] p-1.5 text-slate-400 transition hover:border-blue-500 hover:text-blue-400"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleToggleCountryStatus(c)}
                            title={c.is_active ? "Deactivate" : "Activate"}
                            className="rounded-md border border-[#202938] bg-[#070A0F] p-1.5 text-slate-400 transition hover:text-amber-400"
                          >
                            <Power className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setDeleteItem({
                                type: "countries",
                                id: c.id,
                                name: c.name,
                                warning:
                                  c.cities_count && c.cities_count > 0
                                    ? `This country has ${c.cities_count} attached city/cities. Remove attached cities first.`
                                    : undefined,
                              })
                            }
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
        </>
      )}

      {/* ==================== MODALS ==================== */}

      {/* Area Modal */}
      {areaModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-lg border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-4">
              <h2 className="text-base font-bold text-white">
                {editingArea ? "Edit Area / Sublocality" : "Add Area / Sublocality"}
              </h2>
              <button
                type="button"
                onClick={() => setAreaModalOpen(false)}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveArea} className="mt-4 space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  Area Name *
                </label>
                <input
                  type="text"
                  value={areaForm.name}
                  onChange={(e) =>
                    setAreaForm({ ...areaForm, name: e.target.value })
                  }
                  placeholder="e.g. Sector F-10/2, Johar Town Block A"
                  className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  Parent City
                </label>
                <select
                  value={areaForm.city || ""}
                  onChange={(e) =>
                    setAreaForm({ ...areaForm, city: e.target.value })
                  }
                  className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                >
                  <option value="">No parent city</option>
                  {cities.map((city) => (
                    <option key={city.id} value={city.id}>
                      {city.name} {city.country_name ? `(${city.country_name})` : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-300">
                    Area Code
                  </label>
                  <input
                    type="text"
                    value={areaForm.code}
                    onChange={(e) =>
                      setAreaForm({ ...areaForm, code: e.target.value.toUpperCase() })
                    }
                    placeholder="e.g. F10"
                    className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs uppercase font-mono text-white outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-300">
                    Postal Code
                  </label>
                  <input
                    type="text"
                    value={areaForm.postal_code}
                    onChange={(e) =>
                      setAreaForm({ ...areaForm, postal_code: e.target.value })
                    }
                    placeholder="e.g. 44000"
                    className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setAreaModalOpen(false)}
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
                  {editingArea ? "Update Area" : "Create Area"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* City Modal */}
      {cityModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-lg border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-4">
              <h2 className="text-base font-bold text-white">
                {editingCity ? "Edit City" : "Add Operational City"}
              </h2>
              <button
                type="button"
                onClick={() => setCityModalOpen(false)}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveCity} className="mt-4 space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  City Name *
                </label>
                <input
                  type="text"
                  value={cityForm.name}
                  onChange={(e) =>
                    setCityForm({ ...cityForm, name: e.target.value })
                  }
                  placeholder="e.g. Islamabad, Lahore, Karachi"
                  className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  Parent Country
                </label>
                <select
                  value={cityForm.country || ""}
                  onChange={(e) =>
                    setCityForm({ ...cityForm, country: e.target.value })
                  }
                  className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                >
                  <option value="">No parent country</option>
                  {countries.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  City Code
                </label>
                <input
                  type="text"
                  value={cityForm.code}
                  onChange={(e) =>
                    setCityForm({ ...cityForm, code: e.target.value.toUpperCase() })
                  }
                  placeholder="e.g. ISB, LHE, KHI"
                  className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs uppercase font-mono text-white outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setCityModalOpen(false)}
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
                  {editingCity ? "Update City" : "Create City"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Country Modal */}
      {countryModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-lg border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-4">
              <h2 className="text-base font-bold text-white">
                {editingCountry ? "Edit Country" : "Add Country"}
              </h2>
              <button
                type="button"
                onClick={() => setCountryModalOpen(false)}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveCountry} className="mt-4 space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  Country Name *
                </label>
                <input
                  type="text"
                  value={countryForm.name}
                  onChange={(e) =>
                    setCountryForm({ ...countryForm, name: e.target.value })
                  }
                  placeholder="e.g. Pakistan"
                  className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs text-white outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  Country Code (ISO 2-letter) *
                </label>
                <input
                  type="text"
                  maxLength={5}
                  value={countryForm.code}
                  onChange={(e) =>
                    setCountryForm({
                      ...countryForm,
                      code: e.target.value.toUpperCase(),
                    })
                  }
                  placeholder="e.g. PK"
                  className="w-full rounded-md border border-[#202938] bg-[#070A0F] px-3 py-2 text-xs uppercase font-mono text-white outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setCountryModalOpen(false)}
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
                  {editingCountry ? "Update Country" : "Create Country"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-lg border border-red-500/30 bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-red-400">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-base font-bold text-white">
                Confirm Deletion
              </h3>
            </div>

            <p className="mt-3 text-xs leading-relaxed text-slate-300">
              Are you sure you want to delete{" "}
              <strong className="text-white">"{deleteItem.name}"</strong>?
            </p>

            {deleteItem.warning && (
              <div className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
                ⚠️ {deleteItem.warning}
              </div>
            )}

            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteItem(null)}
                disabled={deleting}
                className="rounded-md border border-[#202938] px-4 py-2 text-xs font-medium text-slate-300 transition hover:bg-[#121821]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={deleting}
                className="inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-xs font-semibold text-white shadow-md transition hover:bg-red-500 disabled:opacity-50"
              >
                {deleting && <LoadingSpinner size="xs" tone="white" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
