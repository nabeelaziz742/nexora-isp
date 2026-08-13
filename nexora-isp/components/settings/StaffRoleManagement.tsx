"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  Loader2,
  Plus,
  ShieldCheck,
  UserCog,
  Users,
  Wrench,
} from "lucide-react";

import {
  CreateStaffPayload,
  OrganizationStaff,
  staffService,
} from "@/services/staff-service";

const initialForm: CreateStaffPayload = {
  first_name: "",
  last_name: "",
  email: "",
  password: "",
  role: "STAFF",
};

export default function StaffRoleManagement() {
  const [staff, setStaff] = useState<
    OrganizationStaff[]
  >([]);
  const [form, setForm] =
    useState<CreateStaffPayload>(initialForm);

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);

  const loadStaff = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const response = await staffService.getStaff();

      setStaff(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load organization staff.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStaff();
  }, [loadStaff]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();

    try {
      setCreating(true);
      setError("");

      await staffService.createStaff(form);

      setForm(initialForm);
      setShowForm(false);

      await loadStaff();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to create staff account.",
      );
    } finally {
      setCreating(false);
    }
  }

  async function toggleStaff(
    member: OrganizationStaff,
  ) {
    try {
      setError("");

      await staffService.setActiveState(
        member.id,
        !member.is_active,
      );

      await loadStaff();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to update staff account.",
      );
    }
  }

  return (
    <section className="border border-slate-800 bg-[#0D1117]">
      <div className="flex flex-col gap-4 border-b border-slate-800 px-5 py-5 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-blue-400" />

            <h2 className="text-sm font-semibold text-slate-100">
              All Staff
            </h2>
          </div>

          <p className="mt-2 text-xs text-slate-500">
            Organization owners, staff and technicians
            with tenant access.
          </p>
        </div>

        <button
          type="button"
          onClick={() =>
            setShowForm((value) => !value)
          }
          className="inline-flex h-9 items-center justify-center gap-2 bg-blue-600 px-4 text-xs font-medium text-white transition hover:bg-blue-500"
        >
          <Plus className="h-4 w-4" />
          Add Staff
        </button>
      </div>

      {error ? (
        <div className="border-b border-red-950 bg-red-950/20 px-5 py-3 text-xs text-red-400">
          {error}
        </div>
      ) : null}

      {showForm ? (
        <form
          onSubmit={handleSubmit}
          className="grid gap-4 border-b border-slate-800 bg-[#090D13] p-5 md:grid-cols-2"
        >
          <input
            required
            value={form.first_name}
            onChange={(event) =>
              setForm({
                ...form,
                first_name: event.target.value,
              })
            }
            placeholder="First name"
            className="h-10 border border-slate-700 bg-[#070A0F] px-3 text-sm text-slate-100 outline-none focus:border-blue-500"
          />

          <input
            required
            value={form.last_name}
            onChange={(event) =>
              setForm({
                ...form,
                last_name: event.target.value,
              })
            }
            placeholder="Last name"
            className="h-10 border border-slate-700 bg-[#070A0F] px-3 text-sm text-slate-100 outline-none focus:border-blue-500"
          />

          <input
            required
            type="email"
            value={form.email}
            onChange={(event) =>
              setForm({
                ...form,
                email: event.target.value,
              })
            }
            placeholder="Staff email"
            className="h-10 border border-slate-700 bg-[#070A0F] px-3 text-sm text-slate-100 outline-none focus:border-blue-500"
          />

          <input
            required
            minLength={8}
            type="password"
            value={form.password}
            onChange={(event) =>
              setForm({
                ...form,
                password: event.target.value,
              })
            }
            placeholder="Temporary password"
            className="h-10 border border-slate-700 bg-[#070A0F] px-3 text-sm text-slate-100 outline-none focus:border-blue-500"
          />

          <select
            value={form.role}
            onChange={(event) =>
              setForm({
                ...form,
                role: event.target.value as
                  | "STAFF"
                  | "TECHNICIAN",
              })
            }
            className="h-10 border border-slate-700 bg-[#070A0F] px-3 text-sm text-slate-100 outline-none focus:border-blue-500"
          >
            <option value="STAFF">Staff</option>
            <option value="TECHNICIAN">
              Technician
            </option>
          </select>

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setShowForm(false);
                setForm(initialForm);
              }}
              className="h-10 border border-slate-700 px-4 text-xs text-slate-300 transition hover:bg-slate-900"
            >
              Cancel
            </button>

            <button
              disabled={creating}
              type="submit"
              className="inline-flex h-10 items-center gap-2 bg-blue-600 px-4 text-xs font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {creating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <UserCog className="h-4 w-4" />
              )}

              Create Staff
            </button>
          </div>
        </form>
      ) : null}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left">
          <thead>
            <tr className="border-b border-slate-800 text-[10px] uppercase tracking-[0.12em] text-slate-500">
              <th className="px-5 py-3 font-medium">
                Staff Member
              </th>

              <th className="px-5 py-3 font-medium">
                Role
              </th>

              <th className="px-5 py-3 font-medium">
                Status
              </th>

              <th className="px-5 py-3 text-right font-medium">
                Access
              </th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td
                  colSpan={4}
                  className="px-5 py-10 text-center text-sm text-slate-500"
                >
                  Loading organization staff...
                </td>
              </tr>
            ) : staff.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="px-5 py-12 text-center"
                >
                  <Users className="mx-auto h-5 w-5 text-slate-700" />

                  <p className="mt-3 text-sm text-slate-400">
                    No staff memberships found.
                  </p>

                  <p className="mt-1 text-xs text-slate-600">
                    Add a staff member or technician to
                    this organization.
                  </p>
                </td>
              </tr>
            ) : (
              staff.map((member) => (
                <tr
                  key={member.id}
                  className="border-b border-slate-800/80"
                >
                  <td className="px-5 py-4">
                    <p className="text-sm font-medium text-slate-100">
                      {member.full_name || member.email}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {member.email}
                    </p>
                  </td>

                  <td className="px-5 py-4">
                    <div className="flex items-center gap-2 text-xs text-slate-300">
                      {member.role === "OWNER" ? (
                        <ShieldCheck className="h-4 w-4 text-violet-400" />
                      ) : member.role ===
                        "TECHNICIAN" ? (
                        <Wrench className="h-4 w-4 text-amber-400" />
                      ) : (
                        <UserCog className="h-4 w-4 text-blue-400" />
                      )}

                      {member.role}
                    </div>
                  </td>

                  <td className="px-5 py-4">
                    <span
                      className={
                        member.is_active
                          ? "text-xs text-emerald-400"
                          : "text-xs text-red-400"
                      }
                    >
                      {member.is_active
                        ? "ACTIVE"
                        : "INACTIVE"}
                    </span>
                  </td>

                  <td className="px-5 py-4 text-right">
                    {member.role === "OWNER" ? (
                      <span className="text-xs text-slate-600">
                        Protected
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() =>
                          toggleStaff(member)
                        }
                        className="border border-slate-700 px-3 py-2 text-xs text-slate-300 transition hover:border-blue-500 hover:text-blue-400"
                      >
                        {member.is_active
                          ? "Deactivate"
                          : "Activate"}
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}