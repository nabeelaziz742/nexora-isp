"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  CircleAlert,
  Edit2,
  Filter,
  LoaderCircle,
  Plus,
  RefreshCw,
  Search,
  Shield,
  UserCheck,
  UserCog,
  Users,
  Wrench,
  X,
} from "lucide-react";

import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Skeleton from "@/components/ui/Skeleton";
import { toast } from "sonner";
import { ApiError } from "@/services/api-error";
import { Area, geoService } from "@/services/geo.service";
import {
  OperationalRole,
  OrganizationStaff,
  StaffStatus,
  staffService,
  UpdateStaffPayload,
} from "@/services/staff-service";

export default function StaffManagementPage() {
  const [staff, setStaff] = useState<OrganizationStaff[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [areaFilter, setAreaFilter] = useState("");

  // Edit Modal State
  const [editingStaff, setEditingStaff] = useState<OrganizationStaff | null>(null);
  const [editForm, setEditForm] = useState<UpdateStaffPayload>({});
  const [isSaving, setIsSaving] = useState(false);
  const [modalError, setModalError] = useState("");

  const loadStaff = async () => {
    try {
      setIsLoading(true);
      setError("");

      const response = await staffService.getStaff({
        search: searchQuery || undefined,
        role: roleFilter || undefined,
        status: statusFilter || undefined,
        area_id: areaFilter || undefined,
      });

      setStaff(response);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load organization staff.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    geoService
      .getAreas({ status: "active" })
      .then(setAreas)
      .catch(() => setAreas([]));
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadStaff();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, roleFilter, statusFilter, areaFilter]);

  const handleStatusChange = async (
    membership: OrganizationStaff,
    newStatus: StaffStatus,
  ) => {
    if (membership.role === "OWNER") return;

    try {
      setError("");
      const updated = await staffService.setStatus(membership.id, newStatus);
      setStaff((current) =>
        current.map((s) => (s.id === updated.id ? updated : s)),
      );
      toast.success(`Staff status updated to ${newStatus}`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Unable to update staff status.";
      setError(msg);
      toast.error(msg);
    }
  };

  const openEditModal = (member: OrganizationStaff) => {
    setEditingStaff(member);
    setEditForm({
      first_name: member.first_name,
      last_name: member.last_name,
      role: member.operational_role,
      phone: member.phone,
      alternate_phone: member.alternate_phone,
      cnic: member.cnic,
      department: member.department,
      designation: member.designation,
      assigned_area_id: member.assigned_area_id,
      joining_date: member.joining_date,
      notes: member.notes,
    });
    setModalError("");
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStaff) return;

    try {
      setIsSaving(true);
      setModalError("");

      const updated = await staffService.updateStaff(editingStaff.id, editForm);
      setStaff((current) =>
        current.map((s) => (s.id === updated.id ? updated : s)),
      );
      toast.success("Staff profile and role updated successfully");
      setEditingStaff(null);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to update staff member.";
      setModalError(msg);
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  };

  // KPIs
  const totalCount = staff.length;
  const activeCount = staff.filter((s) => s.is_active).length;
  const operatorsCount = staff.filter(
    (s) =>
      s.operational_role === "OPERATOR" ||
      s.operational_role === "RECOVERY_OFFICER",
  ).length;
  const techniciansCount = staff.filter(
    (s) => s.operational_role === "TECHNICIAN",
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
            Workforce & Access Control
          </p>

          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
            Staff & Operators Management
          </h1>

          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            Manage employee identities, operational roles, assigned territories, and operational statuses.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadStaff}
            className="flex h-10 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/60 px-4 text-sm font-medium text-slate-300 transition hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>

          <Link
            href="/staff/add"
            className="flex h-10 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-500 shadow-lg shadow-blue-500/20"
          >
            <Plus className="h-4 w-4" />
            Add Staff
          </Link>
        </div>
      </section>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Staff</span>
            <Users className="h-4 w-4 text-blue-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-100">{totalCount}</p>
          <p className="mt-1 text-xs text-slate-500">Registered members</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Active Members</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-400">{activeCount}</p>
          <p className="mt-1 text-xs text-slate-500">Authenticated & Active</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Operators & Recovery</span>
            <UserCheck className="h-4 w-4 text-amber-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-400">{operatorsCount}</p>
          <p className="mt-1 text-xs text-slate-500">Field & Desk Collectors</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Technicians</span>
            <Wrench className="h-4 w-4 text-purple-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-purple-400">{techniciansCount}</p>
          <p className="mt-1 text-xs text-slate-500">Field & Network Team</p>
        </div>
      </div>

      {/* Filters Toolbar */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search by name, email, phone, staff ID, department..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-10 w-full rounded-lg border border-slate-700 bg-slate-950/80 pl-9 pr-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Roles</option>
            <option value="OWNER">Owner</option>
            <option value="ADMIN">Admin</option>
            <option value="MANAGER">Manager</option>
            <option value="OPERATOR">Operator</option>
            <option value="RECOVERY_OFFICER">Recovery Officer</option>
            <option value="TECHNICIAN">Technician</option>
            <option value="SUPPORT_OFFICER">Support Officer</option>
            <option value="FIELD_OFFICER">Field Officer</option>
            <option value="ACCOUNTANT">Accountant</option>
            <option value="STAFF">Standard Staff</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
            <option value="SUSPENDED">Suspended</option>
            <option value="TERMINATED">Terminated</option>
          </select>

          <select
            value={areaFilter}
            onChange={(e) => setAreaFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-300 outline-none focus:border-blue-500"
          >
            <option value="">All Areas</option>
            {areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={loadStaff} />}

      {/* Staff Table */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-14 w-full rounded-xl" />
          <Skeleton className="h-14 w-full rounded-xl" />
          <Skeleton className="h-14 w-full rounded-xl" />
          <Skeleton className="h-14 w-full rounded-xl" />
        </div>
      ) : staff.length === 0 ? (
        <EmptyState
          icon={UserCog}
          title="No staff members found"
          description="No staff profiles match your search and filter criteria."
          actionLabel="Add Staff Member"
          actionHref="/staff/add"
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow-xl backdrop-blur-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-slate-800 bg-slate-950/60 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-5 py-3.5">Staff Member</th>
                  <th className="px-4 py-3.5">Role</th>
                  <th className="px-4 py-3.5">Department / Position</th>
                  <th className="px-4 py-3.5">Territory</th>
                  <th className="px-4 py-3.5">Contact</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {staff.map((member) => (
                  <tr
                    key={member.id}
                    className="transition hover:bg-slate-800/40"
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 font-bold text-blue-400">
                          {member.first_name[0] || member.email[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-100">
                            {member.full_name}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="font-mono text-xs text-blue-400">
                              {member.staff_code || "STF-GEN"}
                            </span>
                            <span className="text-xs text-slate-500">
                              {member.email}
                            </span>
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium ${
                          member.role === "OWNER"
                            ? "bg-amber-500/10 text-amber-300 border border-amber-500/30"
                            : member.operational_role === "RECOVERY_OFFICER"
                            ? "bg-red-500/10 text-red-300 border border-red-500/30"
                            : member.operational_role === "OPERATOR"
                            ? "bg-blue-500/10 text-blue-300 border border-blue-500/30"
                            : member.operational_role === "TECHNICIAN"
                            ? "bg-purple-500/10 text-purple-300 border border-purple-500/30"
                            : "bg-slate-800 text-slate-300 border border-slate-700"
                        }`}
                      >
                        {member.role === "OWNER" ? (
                          <Shield className="h-3 w-3" />
                        ) : null}
                        {member.operational_role.replace("_", " ")}
                      </span>
                    </td>

                    <td className="px-4 py-4">
                      <p className="text-xs font-medium text-slate-200">
                        {member.designation || "Staff Member"}
                      </p>
                      <p className="text-xs text-slate-500">
                        {member.department || "General Operations"}
                      </p>
                    </td>

                    <td className="px-4 py-4">
                      <span className="text-xs text-slate-300">
                        {member.assigned_area_name || "-- All Areas --"}
                      </span>
                    </td>

                    <td className="px-4 py-4 text-xs">
                      <p className="text-slate-300">{member.phone || "--"}</p>
                      {member.cnic && (
                        <p className="text-slate-500 font-mono text-[11px]">
                          {member.cnic}
                        </p>
                      )}
                    </td>

                    <td className="px-4 py-4">
                      {member.role === "OWNER" ? (
                        <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
                          Active (Owner)
                        </span>
                      ) : (
                        <select
                          value={member.status || (member.is_active ? "ACTIVE" : "INACTIVE")}
                          onChange={(e) =>
                            handleStatusChange(
                              member,
                              e.target.value as StaffStatus,
                            )
                          }
                          className={`rounded-lg border px-2.5 py-1 text-xs font-medium outline-none transition ${
                            member.status === "ACTIVE"
                              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                              : member.status === "SUSPENDED"
                              ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
                              : member.status === "TERMINATED"
                              ? "border-red-500/40 bg-red-500/10 text-red-300"
                              : "border-slate-700 bg-slate-900 text-slate-400"
                          }`}
                        >
                          <option value="ACTIVE">Active</option>
                          <option value="INACTIVE">Inactive</option>
                          <option value="SUSPENDED">Suspended</option>
                          <option value="TERMINATED">Terminated</option>
                        </select>
                      )}
                    </td>

                    <td className="px-5 py-4 text-right">
                      {member.role !== "OWNER" && (
                        <button
                          onClick={() => openEditModal(member)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-slate-700 hover:text-white"
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                          Edit Profile
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit Staff Modal */}
      {editingStaff && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-slate-950/60">
              <div>
                <h3 className="text-base font-semibold text-slate-100">
                  Edit Staff Profile
                </h3>
                <p className="text-xs text-slate-400">
                  {editingStaff.full_name} ({editingStaff.staff_code})
                </p>
              </div>
              <button
                onClick={() => setEditingStaff(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {modalError && (
              <div className="m-5 mb-0 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleSaveEdit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-slate-300">
                    First Name
                  </label>
                  <input
                    type="text"
                    value={editForm.first_name || ""}
                    onChange={(e) =>
                      setEditForm({ ...editForm, first_name: e.target.value })
                    }
                    className="mt-1 h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300">
                    Last Name
                  </label>
                  <input
                    type="text"
                    value={editForm.last_name || ""}
                    onChange={(e) =>
                      setEditForm({ ...editForm, last_name: e.target.value })
                    }
                    className="mt-1 h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300">
                    Operational Role
                  </label>
                  <select
                    value={editForm.role || "STAFF"}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        role: e.target.value as OperationalRole,
                      })
                    }
                    className="mt-1 h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  >
                    <option value="STAFF">Staff</option>
                    <option value="OPERATOR">Operator</option>
                    <option value="RECOVERY_OFFICER">Recovery Officer</option>
                    <option value="TECHNICIAN">Technician</option>
                    <option value="SUPPORT_OFFICER">Support Officer</option>
                    <option value="FIELD_OFFICER">Field Officer</option>
                    <option value="MANAGER">Manager</option>
                    <option value="ACCOUNTANT">Accountant</option>
                    <option value="ADMIN">Admin</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300">
                    Assigned Territory
                  </label>
                  <select
                    value={editForm.assigned_area_id || ""}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        assigned_area_id: e.target.value || null,
                      })
                    }
                    className="mt-1 h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  >
                    <option value="">-- No specific area --</option>
                    {areas.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name} ({a.city_name || "City"})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300">
                    Department
                  </label>
                  <input
                    type="text"
                    value={editForm.department || ""}
                    onChange={(e) =>
                      setEditForm({ ...editForm, department: e.target.value })
                    }
                    className="mt-1 h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300">
                    Designation
                  </label>
                  <input
                    type="text"
                    value={editForm.designation || ""}
                    onChange={(e) =>
                      setEditForm({ ...editForm, designation: e.target.value })
                    }
                    className="mt-1 h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300">
                    Phone
                  </label>
                  <input
                    type="text"
                    value={editForm.phone || ""}
                    onChange={(e) =>
                      setEditForm({ ...editForm, phone: e.target.value })
                    }
                    className="mt-1 h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300">
                    CNIC
                  </label>
                  <input
                    type="text"
                    value={editForm.cnic || ""}
                    onChange={(e) =>
                      setEditForm({ ...editForm, cnic: e.target.value })
                    }
                    className="mt-1 h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-200 outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">
                  Notes
                </label>
                <textarea
                  rows={2}
                  value={editForm.notes || ""}
                  onChange={(e) =>
                    setEditForm({ ...editForm, notes: e.target.value })
                  }
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-xs text-slate-200 outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditingStaff(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {isSaving && <LoaderCircle className="h-3.5 w-3.5 animate-spin" />}
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}