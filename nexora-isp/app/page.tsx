"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, RadioTower } from "lucide-react";

import { login } from "@/services/auth.service";
import { ApiError } from "@/services/api-error";

export default function Home() {
  const router = useRouter();

  const [showPassword, setShowPassword] = useState(false);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  const [form, setForm] = useState({
    organization_code: "",
    email: "",
    password: "",
  });

  async function handleSubmit(
    e: React.FormEvent<HTMLFormElement>,
  ) {
    e.preventDefault();

    setLoading(true);
    setError("");

    try {
      await login(form);

      router.replace("/command-center");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to login.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#070A0F] px-6">
      <div className="w-full max-w-md rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 shadow-2xl">

        <div className="mb-8 flex flex-col items-center">

          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-lg bg-blue-600">
            <RadioTower className="h-7 w-7 text-white" />
          </div>

          <h1 className="text-2xl font-bold text-white">
            NEXORA ISP
          </h1>

          <p className="mt-2 text-sm text-slate-400">
            Sign in to continue
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-5"
        >
          <div>
            <label className="mb-2 block text-sm text-slate-300">
              Organization Code
            </label>

            <input
              required
              value={form.organization_code}
              onChange={(e) =>
                setForm({
                  ...form,
                  organization_code: e.target.value,
                })
              }
              className="w-full rounded-lg border border-[#263142] bg-[#101720] px-4 py-3 text-white outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm text-slate-300">
              Email
            </label>

            <input
              type="email"
              required
              value={form.email}
              onChange={(e) =>
                setForm({
                  ...form,
                  email: e.target.value,
                })
              }
              className="w-full rounded-lg border border-[#263142] bg-[#101720] px-4 py-3 text-white outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm text-slate-300">
              Password
            </label>

            <div className="relative">

              <input
                type={
                  showPassword ? "text" : "password"
                }
                required
                value={form.password}
                onChange={(e) =>
                  setForm({
                    ...form,
                    password: e.target.value,
                  })
                }
                className="w-full rounded-lg border border-[#263142] bg-[#101720] px-4 py-3 pr-12 text-white outline-none focus:border-blue-500"
              />

              <button
                type="button"
                onClick={() =>
                  setShowPassword(!showPassword)
                }
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
              >
                {showPassword ? (
                  <EyeOff size={18} />
                ) : (
                  <Eye size={18} />
                )}
              </button>

            </div>
          </div>

          {error && (
            <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <button
            disabled={loading}
            className="flex h-12 w-full items-center justify-center rounded-lg bg-blue-600 font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              "Sign In"
            )}
          </button>

        </form>
      </div>
    </main>
  );
}