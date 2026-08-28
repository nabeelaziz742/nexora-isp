"use client";

import Link from "next/link";
import { useState } from "react";
import { Loader2, RadioTower } from "lucide-react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/services/api-error";
import { registerISP } from "@/services/onboarding.service";

export default function SignupPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    company_name: "",
    city: "",
    first_name: "",
    last_name: "",
    email: "",
    password: "",
  });

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const result = await registerISP(form);
      sessionStorage.setItem(
        "nexora_registration_token",
        result.access_token,
      );
      router.push(`/registration/${result.access_token}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to create your account.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#070A0F] px-6 py-12 text-white">
      <div className="mx-auto max-w-2xl rounded-2xl border border-[#1C2431] bg-[#0D1117] p-8 shadow-2xl">
        <div className="mb-8 flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600">
            <RadioTower className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Create ISP Account</h1>
            <p className="text-sm text-slate-400">
              Register your ISP and submit your payment for verification.
            </p>
          </div>
        </div>

        <form onSubmit={submit} className="grid gap-5 md:grid-cols-2">
          {[
            ["company_name", "ISP / Company Name", "text"],
            ["city", "City", "text"],
            ["first_name", "Owner First Name", "text"],
            ["last_name", "Owner Last Name", "text"],
            ["email", "Owner Email", "email"],
            ["password", "Password", "password"],
          ].map(([key, label, type]) => (
            <div
              key={key}
              className={
                key === "company_name" ? "md:col-span-2" : ""
              }
            >
              <label className="mb-2 block text-sm text-slate-300">
                {label}
              </label>
              <input
                required={key !== "city" && key !== "last_name"}
                type={type}
                value={form[key as keyof typeof form]}
                onChange={(event) =>
                  setForm({ ...form, [key]: event.target.value })
                }
                className="w-full rounded-lg border border-[#263142] bg-[#101720] px-4 py-3 text-white outline-none focus:border-blue-500"
              />
            </div>
          ))}

          {error && (
            <div className="md:col-span-2 rounded-lg bg-red-500/10 p-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <button
            disabled={loading}
            className="md:col-span-2 flex h-12 items-center justify-center rounded-lg bg-blue-600 font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              "Create Account & Continue to Payment"
            )}
          </button>

          <p className="md:col-span-2 text-center text-sm text-slate-500">
            Already registered?{" "}
            <Link
              href="/"
              className="text-blue-400 hover:text-blue-300"
            >
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
}
