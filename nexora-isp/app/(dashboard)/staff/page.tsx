"use client";

import { useEffect, useState } from "react";
import {
  CircleAlert,
  LoaderCircle,
  Plus,
  UserRoundCog,
} from "lucide-react";

import { ApiError } from "@/services/api-error";
import {
  OrganizationStaff,
  staffService,
} from "@/services/staff-service";

export default function StaffManagementPage() {
  const [staff, setStaff] = useState<
    OrganizationStaff[]
  >([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadStaff() {
      try {
        setIsLoading(true);
        setError("");

        const response = await staffService.getStaff();

        setStaff(response);
      } catch (loadError) {
        setError(
          loadError instanceof ApiError
            ? loadError.message
            : "Unable to load organization staff.",
        );
      } finally {
        setIsLoading(false);
      }
    }

    void loadStaff();
  }, []);

  async function handleActiveStateChange(
    membership: OrganizationStaff,
  ) {
    if (membership.role === "OWNER") {
      return;
    }

    try {
      setError("");

      const updatedMembership =
        await staffService.setActiveState(
          membership.id,
          !membership.is_active,
        );

      setStaff((currentStaff) =>
        currentStaff.map((staffMember) =>
          staffMember.id === updatedMembership.id
            ? updatedMembership
            : staffMember,
        ),
      );
    } catch (updateError) {
      setError(
        updateError instanceof ApiError
          ? updateError.message
          : "Unable to update staff access.",
      );
    }
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
            Access Control
          </p>

          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
            Staff Management
          </h1>

          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            Create and manage staff access for this ISP
            organization.
          </p>
        </div>

        <a
          href="/staff/add"
          className="flex h-10 items-center justify-center gap-2 bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-500"
        >
          <Plus className="h-4 w-4" />
          Add Staff
        </a>
      </section>

      {error && (
        <div className="flex items-start gap-3 border border-red-500/30 bg-red-500/10 px-4 py-3">
          <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />

          <p className="text-xs leading-5 text-red-300">
            {error}
          </p>
        </div>
      )}

      <section className="border border-[#202938] bg-[#0D1117]">
        <div className="border-b border-[#202938] px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center bg-blue-500/10">
              <UserRoundCog className="h-4 w-4 text-blue-400" />
            </div>

            <div>
              <h2 className="text-sm font-semibold text-slate-100">
                Organization Staff & Roles
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Staff and technician access within the
                current organization.
              </p>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="flex min-h-48 items-center justify-center">
            <LoaderCircle className="h-5 w-5 animate-spin text-blue-400" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead>
                <tr className="border-b border-[#202938]">
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-600">
                    Staff Member
                  </th>

                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-600">
                    Role
                  </th>

                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-600">
                    Status
                  </th>

                  <th className="px-5 py-3 text-right text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-600">
                    Access
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-[#202938]">
                {staff.map((staffMember) => (
                  <tr key={staffMember.id}>
                    <td className="px-5 py-4">
                      <p className="text-sm font-medium text-slate-200">
                        {staffMember.full_name ||
                          staffMember.email}
                      </p>

                      <p className="mt-1 text-xs text-slate-600">
                        {staffMember.email}
                      </p>
                    </td>

                    <td className="px-5 py-4">
                      <span className="bg-blue-500/10 px-2 py-1 text-[10px] font-semibold text-blue-400">
                        {staffMember.role}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      <span
                        className={
                          staffMember.is_active
                            ? "text-xs font-medium text-emerald-400"
                            : "text-xs font-medium text-red-400"
                        }
                      >
                        {staffMember.is_active
                          ? "Active"
                          : "Inactive"}
                      </span>
                    </td>

                    <td className="px-5 py-4 text-right">
                      {staffMember.role === "OWNER" ? (
                        <span className="text-xs text-slate-600">
                          Protected
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() =>
                            handleActiveStateChange(
                              staffMember,
                            )
                          }
                          className={
                            staffMember.is_active
                              ? "border border-red-500/30 px-3 py-2 text-xs font-medium text-red-400 transition hover:bg-red-500/10"
                              : "border border-emerald-500/30 px-3 py-2 text-xs font-medium text-emerald-400 transition hover:bg-emerald-500/10"
                          }
                        >
                          {staffMember.is_active
                            ? "Disable"
                            : "Enable"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}

                {staff.length === 0 && (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-5 py-12 text-center text-sm text-slate-600"
                    >
                      No organization staff found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}