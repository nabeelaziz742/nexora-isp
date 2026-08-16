"use client";

import { useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/services/api-error";
import { superAdminLogin } from "@/services/onboarding.service";

export default function SuperAdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await superAdminLogin(email, password);
      localStorage.setItem("nexora_superadmin_access", result.access);
      localStorage.setItem("nexora_superadmin_refresh", result.refresh);
      router.replace("/superadmin");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#070A0F] px-6 text-white">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-[#1C2431] bg-[#0D1117] p-8 shadow-2xl">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-blue-600"><ShieldCheck className="h-7 w-7" /></div>
          <h1 className="text-2xl font-bold">Nexora Super Admin</h1>
          <p className="mt-2 text-sm text-slate-400">Platform administration and payment verification</p>
        </div>
        <div className="space-y-5">
          <div><label className="mb-2 block text-sm text-slate-300">Email</label><input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-lg border border-[#263142] bg-[#101720] px-4 py-3 text-white outline-none focus:border-blue-500" /></div>
          <div><label className="mb-2 block text-sm text-slate-300">Password</label><input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-lg border border-[#263142] bg-[#101720] px-4 py-3 text-white outline-none focus:border-blue-500" /></div>
          {error && <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-400">{error}</div>}
          <button disabled={loading} className="flex h-12 w-full items-center justify-center rounded-lg bg-blue-600 font-medium hover:bg-blue-700 disabled:opacity-50">{loading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Sign In"}</button>
        </div>
      </form>
    </main>
  );
}
