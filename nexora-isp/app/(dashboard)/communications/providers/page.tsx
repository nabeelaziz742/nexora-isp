"use client";

import { useEffect, useMemo, useState } from "react";

import {
  Search,
  Plus,
  MessageCircle,
  Mail,
  Smartphone,
  RefreshCw,
  Eye,
  Pencil,
  Trash2,
} from "lucide-react";

import { communicationsService } from "@/services/communications.service";

interface Provider {
  id: string;
  name: string;
  provider_type: "WHATSAPP" | "SMS" | "EMAIL";
  status: string;
  is_default: boolean;
  is_connected: boolean;
  created_at: string;
  updated_at: string;
}

export default function CommunicationProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  async function loadProviders() {
    try {
      setLoading(true);

      const response = await communicationsService.getProviders();

      const items = Array.isArray(response)
        ? response
        : (response as any).results ?? [];

      setProviders(items);
    } catch (error) {
      console.error("Failed to load providers", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProviders();
  }, []);

  const filteredProviders = useMemo(() => {
    return providers.filter((provider) =>
      provider.name.toLowerCase().includes(search.toLowerCase()),
    );
  }, [providers, search]);

  const stats = useMemo(
    () => ({
      total: providers.length,
      whatsapp: providers.filter(
        (provider) => provider.provider_type === "WHATSAPP",
      ).length,
      sms: providers.filter((provider) => provider.provider_type === "SMS")
        .length,
      email: providers.filter(
        (provider) => provider.provider_type === "EMAIL",
      ).length,
    }),
    [providers],
  );

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.20em] text-cyan-400">
            Communication
          </p>

          <h1 className="mt-2 text-3xl font-semibold text-white">
            Providers
          </h1>

          <p className="mt-2 text-sm text-[#64748B]">
            Manage WhatsApp, SMS and Email providers.
          </p>
        </div>

        <button
          className="flex items-center gap-2 bg-cyan-500 px-4 py-2 text-sm font-medium text-black transition hover:bg-cyan-400"
          onClick={loadProviders}
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="border border-[#202938] bg-[#0D1117] p-5">
          <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
            Total Providers
          </p>
          <h2 className="mt-4 text-3xl font-semibold text-cyan-400">
            {stats.total}
          </h2>
        </div>

        <div className="border border-[#202938] bg-[#0D1117] p-5">
          <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
            WhatsApp
          </p>
          <h2 className="mt-4 text-3xl font-semibold text-green-400">
            {stats.whatsapp}
          </h2>
        </div>

        <div className="border border-[#202938] bg-[#0D1117] p-5">
          <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
            SMS
          </p>
          <h2 className="mt-4 text-3xl font-semibold text-amber-400">
            {stats.sms}
          </h2>
        </div>

        <div className="border border-[#202938] bg-[#0D1117] p-5">
          <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
            Email
          </p>
          <h2 className="mt-4 text-3xl font-semibold text-blue-400">
            {stats.email}
          </h2>
        </div>
      </div>

      <div className="border border-[#202938] bg-[#0D1117]">
        <div className="flex items-center justify-between border-b border-[#202938] p-5">
          <div className="relative w-full max-w-md">
            <Search className="absolute left-3 top-3 h-4 w-4 text-[#64748B]" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search providers..."
              className="w-full border border-[#202938] bg-[#080B10] py-2 pl-10 pr-4 text-sm text-white outline-none"
            />
          </div>

          <button className="ml-4 flex items-center gap-2 bg-green-500 px-4 py-2 text-sm font-medium text-black hover:bg-green-400">
            <Plus className="h-4 w-4" />
            Add Provider
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#202938] bg-[#080B10] text-left text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                <th className="px-5 py-4">Provider</th>
                <th className="px-5 py-4">Type</th>
                <th className="px-5 py-4">Status</th>
                <th className="px-5 py-4">Connected</th>
                <th className="px-5 py-4">Default</th>
                <th className="px-5 py-4 text-right">Actions</th>
              </tr>
            </thead>

            <tbody>
              {loading &&
                Array.from({ length: 5 }).map((_, index) => (
                  <tr key={index}>
                    <td colSpan={6} className="px-5 py-5">
                      <div className="h-10 animate-pulse rounded bg-[#111827]" />
                    </td>
                  </tr>
                ))}

              {!loading &&
                filteredProviders.map((provider) => (
                  <tr
                    key={provider.id}
                    className="border-b border-[#202938] transition hover:bg-[#080B10]"
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#202938] bg-[#111827]">
                          {provider.provider_type === "WHATSAPP" && (
                            <MessageCircle className="h-5 w-5 text-green-400" />
                          )}
                          {provider.provider_type === "SMS" && (
                            <Smartphone className="h-5 w-5 text-amber-400" />
                          )}
                          {provider.provider_type === "EMAIL" && (
                            <Mail className="h-5 w-5 text-blue-400" />
                          )}
                        </div>

                        <div>
                          <p className="font-medium text-white">
                            {provider.name}
                          </p>
                          <p className="text-xs text-[#64748B]">
                            {provider.id}
                          </p>
                        </div>
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      <span className="rounded border border-[#202938] bg-[#111827] px-2 py-1 text-xs text-cyan-400">
                        {provider.provider_type}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-medium ${
                          provider.status === "ACTIVE"
                            ? "bg-green-500/15 text-green-400"
                            : "bg-red-500/15 text-red-400"
                        }`}
                      >
                        {provider.status}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      {provider.is_connected ? (
                        <span className="text-green-400">Connected</span>
                      ) : (
                        <span className="text-red-400">Disconnected</span>
                      )}
                    </td>

                    <td className="px-5 py-4">
                      {provider.is_default ? (
                        <span className="rounded bg-cyan-500/15 px-2 py-1 text-xs text-cyan-400">
                          Default
                        </span>
                      ) : (
                        "-"
                      )}
                    </td>

                    <td className="px-5 py-4">
                      <div className="flex justify-end gap-2">
                        <button className="rounded border border-[#202938] bg-[#111827] p-2 hover:border-cyan-500">
                          <Eye className="h-4 w-4 text-cyan-400" />
                        </button>
                        <button className="rounded border border-[#202938] bg-[#111827] p-2 hover:border-blue-500">
                          <Pencil className="h-4 w-4 text-blue-400" />
                        </button>
                        <button className="rounded border border-[#202938] bg-[#111827] p-2 hover:border-red-500">
                          <Trash2 className="h-4 w-4 text-red-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}

              {!loading && filteredProviders.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-[#64748B]">
                    No providers found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}