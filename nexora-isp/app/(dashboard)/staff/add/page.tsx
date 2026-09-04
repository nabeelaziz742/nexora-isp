"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CircleAlert,
  LoaderCircle,
  UserPlus,
} from "lucide-react";

import { ApiError } from "@/services/api-error";
import { Area, geoService } from "@/services/geo.service";
import { OperationalRole, staffService } from "@/services/staff-service";

export default function AddStaffPage() {
  const router = useRouter();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<OperationalRole>("STAFF");
  const [phone, setPhone] = useState("");
  const [alternatePhone, setAlternatePhone] = useState("");
  const [cnic, setCnic] = useState("");
  const [department, setDepartment] = useState("");
  const [designation, setDesignation] = useState("");
  const [assignedAreaId, setAssignedAreaId] = useState("");
  const [joiningDate, setJoiningDate] = useState("");
  const [notes, setNotes] = useState("");

  const [areas, setAreas] = useState<Area[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    geoService
      .getAreas({ status: "active" })
      .then(setAreas)
      .catch(() => setAreas([]));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      setIsSubmitting(true);
      setError("");

      await staffService.createStaff({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim().toLowerCase(),
        password,
        role,
        phone: phone.trim() || undefined,
        alternate_phone: alternatePhone.trim() || undefined,
        cnic: cnic.trim() || undefined,
        department: department.trim() || undefined,
        designation: designation.trim() || undefined,
        assigned_area_id: assignedAreaId || null,
        joining_date: joiningDate || null,
        notes: notes.trim() || undefined,
      });

      router.push("/staff");
      router.refresh();
    } catch (submitError) {
      setError(
        submitError instanceof ApiError
          ? submitError.message
          : "Unable to create staff member.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <section>
        <Link
          href="/staff"
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-400 transition hover:text-blue-400"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Staff Management
        </Link>

        <p className="mt-6 text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
          Access & Workforce Control
        </p>

        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
          Add Staff Member
        </h1>

        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Create a new operational staff profile, assign role, department, and operational territory.
        </p>
      </section>

      {error && (
        <div className="flex items-start gap-3 border border-red-500/30 bg-red-500/10 px-4 py-3 rounded-lg">
          <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
          <p className="text-xs leading-5 text-red-300">{error}</p>
        </div>
      )}

      <section className="border border-[#202938] bg-[#0D1117] rounded-xl overflow-hidden shadow-xl">
        <div className="border-b border-[#202938] px-5 py-4 bg-slate-900/40">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center bg-blue-500/10 rounded-lg">
              <UserPlus className="h-4 w-4 text-blue-400" />
            </div>

            <div>
              <h2 className="text-sm font-semibold text-slate-100">
                Staff Profile & Authentication
              </h2>
              <p className="mt-0.5 text-xs text-slate-400">
                Enter personal details, credentials, and operational responsibilities.
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-5 p-5 md:grid-cols-2">
            <FormField label="First Name" required>
              <input
                type="text"
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="e.g. Tariq"
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Last Name" required>
              <input
                type="text"
                required
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="e.g. Mahmood"
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Email Address (Login Username)" required>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tariq@isp.local"
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Initial Password" required>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Operational Role" required>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as OperationalRole)}
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              >
                <option value="STAFF">Staff (Standard Operational)</option>
                <option value="RECOVERY_OFFICER">Recovery Officer (Defaulters & Collections)</option>
                <option value="OPERATOR">Operator (Desk & Billing Support)</option>
                <option value="TECHNICIAN">Technician (Field & Network)</option>
                <option value="SUPPORT_OFFICER">Support Officer (Complaints & Helpdesk)</option>
                <option value="FIELD_OFFICER">Field Officer (Onsite Surveys)</option>
                <option value="MANAGER">Operations Manager</option>
                <option value="ACCOUNTANT">Accountant / Finance</option>
                <option value="ADMIN">System Administrator</option>
              </select>
            </FormField>

            <FormField label="Assigned Area / Territory">
              <select
                value={assignedAreaId}
                onChange={(e) => setAssignedAreaId(e.target.value)}
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              >
                <option value="">-- No specific area assigned --</option>
                {areas.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.city_name || "City"})
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Department">
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="e.g. Recovery & Collections, Support, Technical"
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Designation">
              <input
                type="text"
                value={designation}
                onChange={(e) => setDesignation(e.target.value)}
                placeholder="e.g. Senior Recovery Officer"
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Phone Number">
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="03001234567"
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="CNIC / ID Card">
              <input
                type="text"
                value={cnic}
                onChange={(e) => setCnic(e.target.value)}
                placeholder="35201-XXXXXXX-X"
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Joining Date">
              <input
                type="date"
                value={joiningDate}
                onChange={(e) => setJoiningDate(e.target.value)}
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Alternate Phone">
              <input
                type="text"
                value={alternatePhone}
                onChange={(e) => setAlternatePhone(e.target.value)}
                placeholder="Optional backup phone"
                className="h-10 w-full rounded-lg border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>
          </div>

          <div className="px-5 pb-5">
            <FormField label="Staff Notes & Additional Details">
              <textarea
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Operational notes, shift timings, or special assignment notes..."
                className="w-full rounded-lg border border-[#2B3545] bg-[#070A0F] p-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-[#202938] bg-slate-900/30 px-5 py-4">
            <Link
              href="/staff"
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
            >
              {isSubmitting && <LoaderCircle className="h-4 w-4 animate-spin" />}
              Create Staff Account
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function FormField({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-slate-300">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
    </div>
  );
}