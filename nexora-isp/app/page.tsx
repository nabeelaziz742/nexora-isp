"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  Building2,
  CheckCircle2,
  Eye,
  EyeOff,
  Lock,
  Mail,
  RadioTower,
  ShieldCheck,
  Zap,
} from "lucide-react";

import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { login } from "@/services/auth.service";
import { ApiError } from "@/services/api-error";

const REMEMBER_ORG_KEY = "nexora_remember_org_code";
const REMEMBER_EMAIL_KEY = "nexora_remember_email";

export default function LoginPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    organization_code: "",
    email: "",
    password: "",
  });

  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{
    organization_code?: string;
    email?: string;
    password?: string;
  }>({});

  // Restore remembered organization code and email on mount
  useEffect(() => {
    try {
      const savedOrg = window.localStorage.getItem(REMEMBER_ORG_KEY);
      const savedEmail = window.localStorage.getItem(REMEMBER_EMAIL_KEY);

      if (savedOrg || savedEmail) {
        setForm((prev) => ({
          ...prev,
          organization_code: savedOrg ?? "",
          email: savedEmail ?? "",
        }));
        setRememberMe(true);
      }
    } catch {
      // Storage access blocked or unavailable
    }
  }, []);

  function validateForm(): boolean {
    const errors: {
      organization_code?: string;
      email?: string;
      password?: string;
    } = {};

    if (!form.organization_code.trim()) {
      errors.organization_code = "Organization code is required";
    }

    if (!form.email.trim()) {
      errors.email = "Email address is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      errors.email = "Enter a valid email address";
    }

    if (!form.password) {
      errors.password = "Password is required";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const result = await login({
        organization_code: form.organization_code.trim().toUpperCase(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
      });

      // Handle Remember Me (Only store Org Code and Email — NEVER store password or tokens)
      try {
        if (rememberMe) {
          window.localStorage.setItem(
            REMEMBER_ORG_KEY,
            form.organization_code.trim().toUpperCase(),
          );
          window.localStorage.setItem(
            REMEMBER_EMAIL_KEY,
            form.email.trim().toLowerCase(),
          );
        } else {
          window.localStorage.removeItem(REMEMBER_ORG_KEY);
          window.localStorage.removeItem(REMEMBER_EMAIL_KEY);
        }
      } catch {
        // Ignore storage errors
      }

      // Role-aware initial routing
      if (result.role === "TECHNICIAN") {
        router.replace("/field-operations");
      } else {
        router.replace("/command-center");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to connect to NEXORA authentication service. Please check your network.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen w-full bg-[#070A0F] text-slate-100 antialiased">
      {/* Left side: Telemetry branding banner (desktop only) */}
      <div className="relative hidden w-1/2 flex-col justify-between border-r border-[#202938] bg-[#0A0E15] p-12 lg:flex xl:p-16">
        {/* Subtle grid background pattern */}
        <div
          className="pointer-events-none absolute inset-0 opacity-15"
          style={{
            backgroundImage:
              "radial-gradient(#3B82F6 1px, transparent 1px), radial-gradient(#1E293B 1px, transparent 1px)",
            backgroundSize: "28px 28px",
            backgroundPosition: "0 0, 14px 14px",
          }}
        />

        {/* Top brand header */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-blue-500/40 bg-blue-600 shadow-md shadow-blue-500/20">
            <RadioTower className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-base font-bold tracking-[0.14em] text-white">
              NEXORA
            </span>
            <span className="ml-1.5 rounded-sm bg-blue-500/20 px-1.5 py-0.5 text-[9px] font-semibold text-blue-400">
              ISP OS
            </span>
          </div>
        </div>

        {/* Middle telemetry & capability highlights */}
        <div className="relative z-10 my-auto max-w-lg space-y-8">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-400">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
              Unified ISP Operating System
            </div>
            <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-white xl:text-4xl">
              Enterprise Telecom & Billing Management
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-slate-400">
              Real-time multi-tenant telemetry, automated subscriber lifecycles,
              field operations dispatch, and intelligent revenue recovery.
            </p>
          </div>

          {/* Operational feature tags */}
          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="flex items-center gap-2.5 rounded-lg border border-[#202938] bg-[#0D1117] p-3 text-xs text-slate-300">
              <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-400" />
              <span>Tenant Data Isolation</span>
            </div>
            <div className="flex items-center gap-2.5 rounded-lg border border-[#202938] bg-[#0D1117] p-3 text-xs text-slate-300">
              <Zap className="h-4 w-4 shrink-0 text-blue-400" />
              <span>Automated Recovery</span>
            </div>
            <div className="flex items-center gap-2.5 rounded-lg border border-[#202938] bg-[#0D1117] p-3 text-xs text-slate-300">
              <Activity className="h-4 w-4 shrink-0 text-purple-400" />
              <span>NOC & Incident Center</span>
            </div>
            <div className="flex items-center gap-2.5 rounded-lg border border-[#202938] bg-[#0D1117] p-3 text-xs text-slate-300">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-cyan-400" />
              <span>Idempotent Ledger</span>
            </div>
          </div>
        </div>

        {/* Bottom system security stamp */}
        <div className="relative z-10 flex items-center justify-between border-t border-[#202938] pt-6 text-[11px] text-slate-500">
          <span>NEXORA Telecom Platform v2.0</span>
          <span>End-to-End Cryptographic JWT Session</span>
        </div>
      </div>

      {/* Right side: Login form card */}
      <div className="flex w-full flex-col justify-center px-6 py-12 lg:w-1/2 lg:px-16 xl:px-24">
        <div className="mx-auto w-full max-w-md">
          {/* Mobile brand header (shown on small screens) */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 shadow-md shadow-blue-500/20">
              <RadioTower className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="text-base font-bold tracking-[0.12em] text-white">
                NEXORA ISP
              </span>
              <p className="text-[10px] uppercase tracking-wider text-slate-500">
                Command Portal
              </p>
            </div>
          </div>

          <div className="mb-6">
            <h2 className="text-2xl font-bold tracking-tight text-white">
              Sign In to Your Workspace
            </h2>
            <p className="mt-1.5 text-xs text-slate-400">
              Enter your tenant organization code and operator credentials.
            </p>
          </div>

          {/* Top error notification banner */}
          {error && (
            <div
              className="mb-5 rounded-lg border border-red-500/30 bg-red-500/10 p-3.5 text-xs leading-relaxed text-red-300"
              role="alert"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Organization Code Field */}
            <div>
              <label
                htmlFor="organization_code"
                className="mb-1.5 flex items-center justify-between text-xs font-medium text-slate-300"
              >
                <span>Organization Code</span>
                <span className="text-[10px] text-slate-500">Tenant identifier</span>
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                  <Building2 className="h-4 w-4" />
                </div>
                <input
                  id="organization_code"
                  type="text"
                  autoComplete="organization"
                  autoCapitalize="characters"
                  spellCheck={false}
                  disabled={loading}
                  value={form.organization_code}
                  onChange={(e) => {
                    setForm({ ...form, organization_code: e.target.value });
                    if (fieldErrors.organization_code) {
                      setFieldErrors({ ...fieldErrors, organization_code: undefined });
                    }
                  }}
                  placeholder="e.g. ALPHA-NET"
                  aria-invalid={!!fieldErrors.organization_code}
                  aria-describedby={fieldErrors.organization_code ? "org-error" : undefined}
                  className={`w-full rounded-lg border bg-[#0D1117] py-2.5 pl-9 pr-3 text-xs text-white uppercase outline-none transition placeholder:text-slate-600 focus:ring-1 ${
                    fieldErrors.organization_code
                      ? "border-red-500/60 focus:border-red-500 focus:ring-red-500/30"
                      : "border-[#202938] focus:border-blue-500 focus:ring-blue-500/30"
                  }`}
                />
              </div>
              {fieldErrors.organization_code && (
                <p id="org-error" className="mt-1 text-[11px] text-red-400">
                  {fieldErrors.organization_code}
                </p>
              )}
            </div>

            {/* Email Field */}
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-xs font-medium text-slate-300"
              >
                Operator Email
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  spellCheck={false}
                  disabled={loading}
                  value={form.email}
                  onChange={(e) => {
                    setForm({ ...form, email: e.target.value });
                    if (fieldErrors.email) {
                      setFieldErrors({ ...fieldErrors, email: undefined });
                    }
                  }}
                  placeholder="operator@isp.com"
                  aria-invalid={!!fieldErrors.email}
                  aria-describedby={fieldErrors.email ? "email-error" : undefined}
                  className={`w-full rounded-lg border bg-[#0D1117] py-2.5 pl-9 pr-3 text-xs text-white outline-none transition placeholder:text-slate-600 focus:ring-1 ${
                    fieldErrors.email
                      ? "border-red-500/60 focus:border-red-500 focus:ring-red-500/30"
                      : "border-[#202938] focus:border-blue-500 focus:ring-blue-500/30"
                  }`}
                />
              </div>
              {fieldErrors.email && (
                <p id="email-error" className="mt-1 text-[11px] text-red-400">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-xs font-medium text-slate-300"
              >
                Password
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  disabled={loading}
                  value={form.password}
                  onChange={(e) => {
                    setForm({ ...form, password: e.target.value });
                    if (fieldErrors.password) {
                      setFieldErrors({ ...fieldErrors, password: undefined });
                    }
                  }}
                  placeholder="••••••••••••"
                  aria-invalid={!!fieldErrors.password}
                  aria-describedby={fieldErrors.password ? "password-error" : undefined}
                  className={`w-full rounded-lg border bg-[#0D1117] py-2.5 pl-9 pr-10 text-xs text-white outline-none transition placeholder:text-slate-600 focus:ring-1 ${
                    fieldErrors.password
                      ? "border-red-500/60 focus:border-red-500 focus:ring-red-500/30"
                      : "border-[#202938] focus:border-blue-500 focus:ring-blue-500/30"
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-500 transition hover:text-slate-300"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {fieldErrors.password && (
                <p id="password-error" className="mt-1 text-[11px] text-red-400">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            {/* Remember Me Checkbox (Only remembers Org Code & Email, NEVER password) */}
            <div className="flex items-center justify-between pt-1">
              <label className="flex cursor-pointer items-center gap-2 select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  disabled={loading}
                  className="h-3.5 w-3.5 rounded border-[#202938] bg-[#0D1117] text-blue-600 accent-blue-600 focus:ring-0 focus:ring-offset-0"
                />
                <span className="text-[11px] text-slate-400 hover:text-slate-300">
                  Remember organization & email
                </span>
              </label>

              <span className="text-[11px] text-slate-600">
                SSL Secured
              </span>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex h-11 w-full items-center justify-center rounded-lg bg-blue-600 text-xs font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-500 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <LoadingSpinner size="sm" tone="white" label="Authenticating..." />
              ) : (
                "Authenticate & Open Workspace"
              )}
            </button>
          </form>

          {/* New ISP registration link */}
          <div className="mt-8 border-t border-[#202938] pt-5 text-center text-xs text-slate-500">
            <span>New ISP Provider? </span>
            <a
              href="/signup"
              className="font-medium text-blue-400 transition hover:text-blue-300 hover:underline"
            >
              Register your ISP organization
            </a>
          </div>
        </div>
      </div>
    </main>
  );
}
