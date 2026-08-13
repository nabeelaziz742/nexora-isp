"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CircleAlert,
  LoaderCircle,
  UserPlus,
} from "lucide-react";

import { ApiError } from "@/services/api-error";
import { staffService } from "@/services/staff-service";

type StaffRole = "STAFF" | "TECHNICIAN";

export default function AddStaffPage() {
  const router = useRouter();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] =
    useState<StaffRole>("STAFF");

  const [isSubmitting, setIsSubmitting] =
    useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
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
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-500 transition hover:text-blue-400"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Staff Management
        </Link>

        <p className="mt-6 text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
          Access Control
        </p>

        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
          Add Staff
        </h1>

        <p className="mt-2 max-w-3xl text-sm text-slate-500">
          Create a staff or technician account and grant
          access to the current ISP organization.
        </p>
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
              <UserPlus className="h-4 w-4 text-blue-400" />
            </div>

            <div>
              <h2 className="text-sm font-semibold text-slate-100">
                Staff Account
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Enter staff identity and organization role.
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-5 p-5 md:grid-cols-2">
            <FormField label="First Name">
              <input
                type="text"
                required
                value={firstName}
                onChange={(event) =>
                  setFirstName(event.target.value)
                }
                className="h-11 w-full border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Last Name">
              <input
                type="text"
                value={lastName}
                onChange={(event) =>
                  setLastName(event.target.value)
                }
                className="h-11 w-full border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Email Address">
              <input
                type="email"
                required
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                className="h-11 w-full border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Temporary Password">
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                className="h-11 w-full border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              />
            </FormField>

            <FormField label="Organization Role">
              <select
                value={role}
                onChange={(event) =>
                  setRole(
                    event.target.value as StaffRole,
                  )
                }
                className="h-11 w-full border border-[#2B3545] bg-[#070A0F] px-3 text-sm text-slate-200 outline-none transition focus:border-blue-500"
              >
                <option value="STAFF">Staff</option>
                <option value="TECHNICIAN">
                  Technician
                </option>
              </select>
            </FormField>
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-[#202938] px-5 py-4">
            <Link
              href="/staff"
              className="flex h-10 items-center justify-center border border-[#2B3545] px-4 text-sm font-medium text-slate-400 transition hover:bg-[#121821] hover:text-slate-200"
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={isSubmitting}
              className="flex h-10 items-center justify-center gap-2 bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <UserPlus className="h-4 w-4" />
              )}

              {isSubmitting
                ? "Creating Staff..."
                : "Create Staff"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

interface FormFieldProps {
  label: string;
  children: React.ReactNode;
}

function FormField({
  label,
  children,
}: FormFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-600">
        {label}
      </span>

      {children}
    </label>
  );
}