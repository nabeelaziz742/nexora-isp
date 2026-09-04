"use client";

import { useState } from "react";
import {
  Building2,
  CheckCircle2,
  Edit2,
  HardDrive,
  MapPin,
  Plus,
  Radio,
  Search,
  Server,
  ShieldAlert,
  Users,
  X,
  Zap,
} from "lucide-react";

import { networkService } from "@/services/network.service";
import type { PointOfPresence, PopStatus, PopType } from "@/types/network";

interface PopsTableProps {
  pops: PointOfPresence[];
  onRefresh: () => void;
}

const POP_TYPE_LABELS: Record<PopType, string> = {
  CORE: "Core POP",
  AGGREGATION: "Aggregation Node",
  DISTRIBUTION: "Distribution Point",
  TOWER: "Wireless Tower",
  CABINET: "Street Cabinet / ODF",
  CENTRAL_OFFICE: "Central Office",
  OTHER: "Other Facility",
};

const POP_STATUS_COLORS: Record<PopStatus, { bg: string; text: string; border: string }> = {
  ACTIVE: { bg: "bg-[#22C55E]/10", text: "text-[#22C55E]", border: "border-[#22C55E]/30" },
  MAINTENANCE: { bg: "bg-[#F59E0B]/10", text: "text-[#F59E0B]", border: "border-[#F59E0B]/30" },
  DEGRADED: { bg: "bg-[#EC4899]/10", text: "text-[#EC4899]", border: "border-[#EC4899]/30" },
  OFFLINE: { bg: "bg-[#EF4444]/10", text: "text-[#EF4444]", border: "border-[#EF4444]/30" },
};

export default function PopsTable({ pops, onRefresh }: PopsTableProps) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPop, setEditingPop] = useState<PointOfPresence | null>(null);
  const [formData, setFormData] = useState({
    code: "",
    name: "",
    pop_type: "DISTRIBUTION" as PopType,
    address: "",
    rack_capacity_units: 42,
    power_backup_type: "UPS_GENERATOR",
    status: "ACTIVE" as PopStatus,
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const filteredPops = pops.filter((pop) => {
    const matchesSearch =
      search === "" ||
      pop.code.toLowerCase().includes(search.toLowerCase()) ||
      pop.name.toLowerCase().includes(search.toLowerCase()) ||
      pop.address.toLowerCase().includes(search.toLowerCase());

    const matchesType = typeFilter === "" || pop.pop_type === typeFilter;
    const matchesStatus = statusFilter === "" || pop.status === statusFilter;

    return matchesSearch && matchesType && matchesStatus;
  });

  const handleOpenCreate = () => {
    setEditingPop(null);
    setFormData({
      code: "",
      name: "",
      pop_type: "DISTRIBUTION",
      address: "",
      rack_capacity_units: 42,
      power_backup_type: "UPS_GENERATOR",
      status: "ACTIVE",
      notes: "",
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (pop: PointOfPresence) => {
    setEditingPop(pop);
    setFormData({
      code: pop.code,
      name: pop.name,
      pop_type: pop.pop_type,
      address: pop.address || "",
      rack_capacity_units: pop.rack_capacity_units || 42,
      power_backup_type: pop.power_backup_type || "UPS_GENERATOR",
      status: pop.status,
      notes: pop.notes || "",
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);

    try {
      if (editingPop) {
        await networkService.updatePop(editingPop.id, formData);
      } else {
        await networkService.createPop(formData);
      }
      setIsModalOpen(false);
      onRefresh();
    } catch (err: any) {
      setFormError(err?.message || "Failed to save POP site.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Search and Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[240px]">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#64748B]" />
            <input
              type="text"
              placeholder="Search POP sites..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full border border-[#202938] bg-[#0D1117] py-2 pl-9 pr-3 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:border-[#38BDF8] focus:outline-none"
            />
          </div>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border border-[#202938] bg-[#0D1117] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
          >
            <option value="">All POP Types</option>
            <option value="CORE">Core POP</option>
            <option value="AGGREGATION">Aggregation Node</option>
            <option value="DISTRIBUTION">Distribution Point</option>
            <option value="TOWER">Wireless Tower</option>
            <option value="CABINET">Street Cabinet</option>
            <option value="CENTRAL_OFFICE">Central Office</option>
            <option value="OTHER">Other Facility</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-[#202938] bg-[#0D1117] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="MAINTENANCE">Maintenance</option>
            <option value="DEGRADED">Degraded</option>
            <option value="OFFLINE">Offline</option>
          </select>
        </div>

        <button
          type="button"
          onClick={handleOpenCreate}
          className="flex items-center gap-2 border border-[#38BDF8] bg-[#38BDF8]/10 px-4 py-2 text-xs font-semibold text-[#38BDF8] transition-colors hover:bg-[#38BDF8]/20"
        >
          <Plus className="h-3.5 w-3.5" />
          Add POP Site
        </button>
      </div>

      {/* POP Table */}
      <div className="overflow-x-auto border border-[#202938] bg-[#0D1117]">
        <table className="w-full text-left text-xs text-[#F8FAFC]">
          <thead className="border-b border-[#202938] bg-[#161B22] text-[11px] uppercase tracking-wider text-[#64748B]">
            <tr>
              <th className="px-4 py-3">POP Site</th>
              <th className="px-4 py-3">Facility Type</th>
              <th className="px-4 py-3">Area / Location</th>
              <th className="px-4 py-3">Capacity & Power</th>
              <th className="px-4 py-3 text-center">Nodes Attached</th>
              <th className="px-4 py-3 text-center">Subscribers</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#202938]">
            {filteredPops.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-xs text-[#64748B]">
                  No Point of Presence (POP) sites match the current filters.
                </td>
              </tr>
            ) : (
              filteredPops.map((pop) => {
                const statusStyle = POP_STATUS_COLORS[pop.status] || POP_STATUS_COLORS.ACTIVE;

                return (
                  <tr key={pop.id} className="transition-colors hover:bg-[#161B22]/50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-[#F8FAFC]">{pop.name}</div>
                      <div className="font-mono text-[10px] text-[#38BDF8]">{pop.code}</div>
                    </td>

                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 border border-[#38BDF8]/20 bg-[#38BDF8]/5 px-2 py-0.5 text-[11px] text-[#38BDF8]">
                        <Building2 className="h-3 w-3" />
                        {POP_TYPE_LABELS[pop.pop_type] || pop.pop_type}
                      </span>
                    </td>

                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 text-[#94A3B8]">
                        <MapPin className="h-3 w-3 text-[#64748B]" />
                        <span>{pop.area_name || pop.address || "Unspecified"}</span>
                      </div>
                      {pop.area_city && <div className="text-[10px] text-[#64748B] pl-4">{pop.area_city}</div>}
                    </td>

                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 text-[#94A3B8]">
                        <Server className="h-3 w-3 text-[#64748B]" />
                        <span className="font-medium">{pop.rack_capacity_units}U Rack</span>
                      </div>

                      {/* Visual Capacity Meter */}
                      {(() => {
                        const estimatedUsed = Math.min(pop.rack_capacity_units, Math.max(1, pop.nodes_count * 2));
                        const capacityPct = pop.rack_capacity_units > 0
                          ? Math.min(100, Math.round((estimatedUsed / pop.rack_capacity_units) * 100))
                          : 0;
                        const meterColor =
                          capacityPct > 80
                            ? "bg-rose-500"
                            : capacityPct > 60
                            ? "bg-amber-500"
                            : "bg-emerald-500";
                        const textColor =
                          capacityPct > 80
                            ? "text-rose-400"
                            : capacityPct > 60
                            ? "text-amber-400"
                            : "text-emerald-400";

                        return (
                          <div className="mt-1.5 w-28">
                            <div className="flex items-center justify-between text-[9px] font-mono mb-0.5">
                              <span className="text-slate-400">{estimatedUsed}/{pop.rack_capacity_units}U</span>
                              <span className={`font-semibold ${textColor}`}>{capacityPct}%</span>
                            </div>
                            <div className="h-1.5 w-full bg-[#161B22] rounded-full overflow-hidden border border-[#202938]">
                              <div
                                className={`h-full rounded-full transition-all ${meterColor}`}
                                style={{ width: `${Math.max(6, capacityPct)}%` }}
                                role="progressbar"
                                aria-valuenow={capacityPct}
                                aria-valuemin={0}
                                aria-valuemax={100}
                                aria-label={`POP Rack Capacity: ${capacityPct}% utilized`}
                              />
                            </div>
                          </div>
                        );
                      })()}

                      <div className="mt-1 flex items-center gap-1.5 text-[10px] text-[#64748B]">
                        <Zap className="h-2.5 w-2.5 text-[#F59E0B]" />
                        <span>{pop.power_backup_type || "Standard"}</span>
                      </div>
                    </td>

                    <td className="px-4 py-3 text-center">
                      <span className="font-mono text-xs font-semibold text-[#F8FAFC]">{pop.nodes_count}</span>
                    </td>

                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center gap-1 font-mono text-xs font-semibold text-[#22C55E]">
                        <Users className="h-3 w-3" />
                        {pop.active_subscribers_count}
                      </span>
                    </td>

                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border}`}
                      >
                        {pop.status}
                      </span>
                    </td>

                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => handleOpenEdit(pop)}
                        className="inline-flex items-center gap-1 border border-[#202938] bg-[#161B22] px-2.5 py-1 text-[11px] text-[#94A3B8] transition-colors hover:border-[#38BDF8] hover:text-[#38BDF8]"
                      >
                        <Edit2 className="h-3 w-3" />
                        Edit
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Create / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-3">
              <h3 className="text-sm font-semibold text-[#F8FAFC]">
                {editingPop ? `Edit POP Site: ${editingPop.code}` : "Add New Point of Presence (POP)"}
              </h3>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-[#64748B] hover:text-[#F8FAFC]"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {formError && (
              <div className="mt-3 border border-[#EF4444]/30 bg-[#EF4444]/10 p-2.5 text-xs text-[#EF4444]">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">POP Code *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. POP-LHR-01"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 font-mono text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">POP Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Gulberg Main Core Site"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Facility Type</label>
                  <select
                    value={formData.pop_type}
                    onChange={(e) => setFormData({ ...formData, pop_type: e.target.value as PopType })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  >
                    <option value="CORE">Core POP</option>
                    <option value="AGGREGATION">Aggregation Node</option>
                    <option value="DISTRIBUTION">Distribution Point</option>
                    <option value="TOWER">Wireless Tower</option>
                    <option value="CABINET">Street Cabinet / ODF</option>
                    <option value="CENTRAL_OFFICE">Central Office</option>
                    <option value="OTHER">Other Facility</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Operational Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as PopStatus })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  >
                    <option value="ACTIVE">Active</option>
                    <option value="MAINTENANCE">Under Maintenance</option>
                    <option value="DEGRADED">Degraded Performance</option>
                    <option value="OFFLINE">Offline</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Rack Units (Capacity)</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={formData.rack_capacity_units}
                    onChange={(e) => setFormData({ ...formData, rack_capacity_units: parseInt(e.target.value) || 42 })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Power Backup</label>
                  <input
                    type="text"
                    placeholder="e.g. SOLAR_UPS_GENERATOR"
                    value={formData.power_backup_type}
                    onChange={(e) => setFormData({ ...formData, power_backup_type: e.target.value })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Address / Location</label>
                <input
                  type="text"
                  placeholder="Street address or physical landmarks"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Notes</label>
                <textarea
                  rows={2}
                  placeholder="Facility access notes, keys, generator schedule..."
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="border border-[#202938] bg-[#161B22] px-4 py-2 text-xs text-[#94A3B8] hover:text-[#F8FAFC]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="border border-[#38BDF8] bg-[#38BDF8] px-4 py-2 text-xs font-semibold text-[#0D1117] hover:bg-[#38BDF8]/90 disabled:opacity-50"
                >
                  {submitting ? "Saving..." : editingPop ? "Update POP" : "Create POP Site"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
