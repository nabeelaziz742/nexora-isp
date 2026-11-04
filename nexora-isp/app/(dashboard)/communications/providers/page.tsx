"use client";

import { useEffect, useMemo, useState } from "react";

import {
  Search,
  Plus,
  MessageCircle,
  Mail,
  Smartphone,
  RefreshCw,
  PlugZap,
  Pencil,
  Trash2,
  Loader2,
  X,
} from "lucide-react";

import { useToast } from "@/hooks/useToast";
import { ApiError } from "@/services/api-error";
import {
  communicationsService,
  type CommunicationProvider as Provider,
  type CommunicationProviderPayload,
} from "@/services/communications.service";

const emptyForm: CommunicationProviderPayload = {
  name: "",
  provider_type: "WHATSAPP",
  status: "ACTIVE",
  business_id: "",
  phone_number_id: "",
  access_token: "",
  api_url: "",
  sender_id: "",
};

function errorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    const payload = error.payload as { message?: string } | null;
    return payload?.message || error.message || fallback;
  }
  return error instanceof Error ? error.message : fallback;
}

export default function CommunicationProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const toast = useToast();

  const [formOpen, setFormOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [form, setForm] = useState<CommunicationProviderPayload>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  function openCreate() {
    setEditingProvider(null);
    setForm(emptyForm);
    setFormOpen(true);
  }

  function openEdit(provider: Provider) {
    setEditingProvider(provider);
    setForm({
      name: provider.name,
      provider_type: provider.provider_type,
      status: provider.status,
      business_id: provider.business_id ?? "",
      phone_number_id: provider.phone_number_id ?? "",
      access_token: "",
      api_url: provider.api_url ?? "",
      sender_id: provider.sender_id ?? "",
    });
    setFormOpen(true);
  }

  function updateForm(field: keyof CommunicationProviderPayload, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSave() {
    if (!form.name.trim()) {
      toast.error("Provider name is required.");
      return;
    }
    try {
      setSaving(true);
      const payload = { ...form, name: form.name.trim() };
      if (editingProvider) {
        await communicationsService.updateProviderSettings(editingProvider.id, payload);
        toast.success("Provider updated. Run Test Connection to connect it.");
      } else {
        await communicationsService.createProvider(payload);
        toast.success("Provider added. Run Test Connection to connect it.");
      }
      setFormOpen(false);
      await loadProviders();
    } catch (error) {
      toast.error(errorMessage(error, "Unable to save provider."));
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(provider: Provider) {
    try {
      setBusyId(provider.id);
      const result = (await communicationsService.testProviderConnection(
        provider.id,
      )) as { message?: string };
      toast.success(result?.message || "Provider connected.");
    } catch (error) {
      toast.error(errorMessage(error, "Connection test failed."));
    } finally {
      setBusyId(null);
      await loadProviders();
    }
  }

  async function handleDelete(provider: Provider) {
    if (!window.confirm(`Delete provider "${provider.name}"?`)) {
      return;
    }
    try {
      setBusyId(provider.id);
      await communicationsService.deleteProvider(provider.id);
      toast.success("Provider deleted.");
      await loadProviders();
    } catch (error) {
      toast.error(errorMessage(error, "Unable to delete provider."));
    } finally {
      setBusyId(null);
    }
  }

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
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
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

          <button
            type="button"
            onClick={openCreate}
            className="ml-4 flex items-center gap-2 bg-green-500 px-4 py-2 text-sm font-medium text-black hover:bg-green-400"
          >
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
                      <div className="flex flex-wrap justify-end gap-2">
                        <button
                          type="button"
                          title="Test connection"
                          aria-label={`Test connection for ${provider.name}`}
                          onClick={() => handleTest(provider)}
                          disabled={busyId === provider.id}
                          className="rounded border border-[#202938] bg-[#111827] p-2 hover:border-cyan-500 disabled:opacity-50"
                        >
                          {busyId === provider.id ? (
                            <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
                          ) : (
                            <PlugZap className="h-4 w-4 text-cyan-400" />
                          )}
                        </button>
                        <button
                          type="button"
                          title="Edit provider"
                          aria-label={`Edit ${provider.name}`}
                          onClick={() => openEdit(provider)}
                          className="rounded border border-[#202938] bg-[#111827] p-2 hover:border-blue-500"
                        >
                          <Pencil className="h-4 w-4 text-blue-400" />
                        </button>
                        <button
                          type="button"
                          title="Delete provider"
                          aria-label={`Delete ${provider.name}`}
                          onClick={() => handleDelete(provider)}
                          disabled={busyId === provider.id}
                          className="rounded border border-[#202938] bg-[#111827] p-2 hover:border-red-500 disabled:opacity-50"
                        >
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

      {formOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg border border-[#202938] bg-[#0D1117] p-6">
            <div className="flex items-center justify-between border-b border-[#202938] pb-3">
              <h2 className="text-base font-semibold text-white">
                {editingProvider ? "Edit Provider" : "Add Provider"}
              </h2>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setFormOpen(false)}
                className="text-[#64748B] hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1 block text-xs text-[#94A3B8]">Name *</span>
                  <input
                    value={form.name}
                    onChange={(e) => updateForm("name", e.target.value)}
                    placeholder="e.g. Main WhatsApp"
                    className="w-full border border-[#202938] bg-[#080B10] px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
                  />
                </label>

                <label className="block">
                  <span className="mb-1 block text-xs text-[#94A3B8]">Type *</span>
                  <select
                    value={form.provider_type}
                    disabled={Boolean(editingProvider)}
                    onChange={(e) => updateForm("provider_type", e.target.value)}
                    className="w-full border border-[#202938] bg-[#080B10] px-3 py-2 text-sm text-white outline-none focus:border-cyan-500 disabled:opacity-60"
                  >
                    <option value="WHATSAPP">WhatsApp Cloud API</option>
                    <option value="EMAIL">Email</option>
                    <option value="SMS">SMS</option>
                  </select>
                </label>
              </div>

              {form.provider_type === "WHATSAPP" && (
                <>
                  <label className="block">
                    <span className="mb-1 block text-xs text-[#94A3B8]">Phone Number ID *</span>
                    <input
                      value={form.phone_number_id}
                      onChange={(e) => updateForm("phone_number_id", e.target.value)}
                      placeholder="From Meta WhatsApp Manager > API Setup"
                      className="w-full border border-[#202938] bg-[#080B10] px-3 py-2 font-mono text-sm text-white outline-none focus:border-cyan-500"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-1 block text-xs text-[#94A3B8]">
                      Access Token *{" "}
                      {editingProvider?.has_access_token && (
                        <span className="text-green-400">(saved, leave blank to keep)</span>
                      )}
                    </span>
                    <input
                      type="password"
                      autoComplete="off"
                      value={form.access_token}
                      onChange={(e) => updateForm("access_token", e.target.value)}
                      placeholder="Permanent system user token"
                      className="w-full border border-[#202938] bg-[#080B10] px-3 py-2 font-mono text-sm text-white outline-none focus:border-cyan-500"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-1 block text-xs text-[#94A3B8]">WhatsApp Business Account ID</span>
                    <input
                      value={form.business_id}
                      onChange={(e) => updateForm("business_id", e.target.value)}
                      className="w-full border border-[#202938] bg-[#080B10] px-3 py-2 font-mono text-sm text-white outline-none focus:border-cyan-500"
                    />
                  </label>
                </>
              )}

              {form.provider_type === "EMAIL" && (
                <p className="text-xs text-[#94A3B8]">
                  Email uses the server&apos;s SMTP settings. Test Connection checks that the server can reach the mail host.
                </p>
              )}

              {form.provider_type === "SMS" && (
                <p className="text-xs text-amber-400">
                  SMS sending is not available yet. The provider can be saved but will not send messages.
                </p>
              )}

              <label className="block">
                <span className="mb-1 block text-xs text-[#94A3B8]">Status</span>
                <select
                  value={form.status}
                  onChange={(e) => updateForm("status", e.target.value)}
                  className="w-full border border-[#202938] bg-[#080B10] px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
                >
                  <option value="ACTIVE">Active</option>
                  <option value="INACTIVE">Inactive</option>
                </select>
              </label>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setFormOpen(false)}
                className="border border-[#202938] px-4 py-2 text-sm text-[#CBD5E1] hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 bg-green-500 px-4 py-2 text-sm font-medium text-black hover:bg-green-400 disabled:opacity-60"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                {editingProvider ? "Save Changes" : "Add Provider"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}