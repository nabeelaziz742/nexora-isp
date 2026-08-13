"use client";

import {
  Mail,
  MessageCircle,
  Save,
  Server,
  Smartphone,
} from "lucide-react";
import { useEffect, useState } from "react";
import { communicationsService } from "@/services/communications.service";

export default function CommunicationSettingsPage() {
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadProviders();
  }, []);

  async function loadProviders() {
    try {
      const response =
        await communicationsService.getProviderSettings();

      setProviders(
        Array.isArray(response)
          ? response
          : (response as any).results ?? []
      );
    } finally {
      setLoading(false);
    }
  }

  function updateProvider(id: string, field: string, value: any) {
    setProviders((prev) =>
      prev.map((p) =>
        p.id === id
          ? {
              ...p,
              [field]: value,
            }
          : p
      )
    );
  }

  async function saveAll() {
    setSaving(true);

    try {
      await Promise.all(
        providers.map((provider) =>
          communicationsService.updateProviderSettings(
            provider.id,
            provider
          )
        )
      );

      await loadProviders();
    } finally {
      setSaving(false);
    }
  }

  async function handleTestConnection(id: string) {
    try {
      await communicationsService.testProviderConnection(id);
      await loadProviders();
    } catch (error) {
      console.error("Test connection failed:", error);
    }
  }

  const whatsapp = providers.find(
    (p) => p.provider_type === "WHATSAPP"
  );

  const sms = providers.find(
    (p) => p.provider_type === "SMS"
  );

  const email = providers.find(
    (p) => p.provider_type === "EMAIL"
  );

  const activeCount = providers.length;
  const connectedCount = providers.filter((p) => p.is_connected).length;
  const pendingCount = providers.filter((p) => !p.is_connected).length;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.20em] text-green-400">
            Communication
          </p>

          <h1 className="mt-2 text-2xl font-semibold text-white">
            Communication Settings
          </h1>

          <p className="mt-2 text-sm text-[#64748B]">
            Configure WhatsApp, SMS and Email providers.
          </p>
        </div>

        <button
          onClick={saveAll}
          disabled={saving}
          className="flex items-center gap-2 bg-green-500 px-5 py-2 text-sm font-medium text-black hover:bg-green-400 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {saving ? "Saving..." : "Save Configuration"}
        </button>
      </div>

      {loading && (
        <div className="border border-[#202938] bg-[#0D1117] p-8 text-center text-sm text-[#64748B]">
          Loading provider settings...
        </div>
      )}

      {!loading && (
        <>
          <div className="grid gap-6 xl:grid-cols-3">
            {/* WhatsApp */}
            <div className="border border-[#202938] bg-[#0D1117]">
              <div className="flex items-center gap-3 border-b border-[#202938] px-5 py-4">
                <MessageCircle className="h-5 w-5 text-green-400" />

                <h2 className="font-semibold text-white">
                  WhatsApp Cloud API
                </h2>
              </div>

              <div className="space-y-4 p-5">
                <input
                  placeholder="Business ID"
                  value={whatsapp?.business_id ?? ""}
                  onChange={(e) =>
                    whatsapp &&
                    updateProvider(
                      whatsapp.id,
                      "business_id",
                      e.target.value
                    )
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <input
                  placeholder="Phone Number ID"
                  value={whatsapp?.phone_number_id ?? ""}
                  onChange={(e) =>
                    whatsapp &&
                    updateProvider(
                      whatsapp.id,
                      "phone_number_id",
                      e.target.value
                    )
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <input
                  placeholder="Access Token"
                  value={whatsapp?.access_token ?? ""}
                  onChange={(e) =>
                    whatsapp &&
                    updateProvider(
                      whatsapp.id,
                      "access_token",
                      e.target.value
                    )
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <input
                  placeholder="Webhook Verify Token"
                  value={whatsapp?.webhook_verify_token ?? ""}
                  onChange={(e) =>
                    whatsapp &&
                    updateProvider(
                      whatsapp.id,
                      "webhook_verify_token",
                      e.target.value
                    )
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <button
                  onClick={() =>
                    whatsapp && handleTestConnection(whatsapp.id)
                  }
                  disabled={!whatsapp}
                  className="w-full border border-[#202938] bg-[#111827] py-3 text-white hover:border-green-500 disabled:opacity-50"
                >
                  Test Connection
                </button>
              </div>
            </div>

            {/* SMS */}
            <div className="border border-[#202938] bg-[#0D1117]">
              <div className="flex items-center gap-3 border-b border-[#202938] px-5 py-4">
                <Smartphone className="h-5 w-5 text-amber-400" />

                <h2 className="font-semibold text-white">
                  SMS Provider
                </h2>
              </div>

              <div className="space-y-4 p-5">
                <input
                  placeholder="API URL"
                  value={sms?.api_url ?? ""}
                  onChange={(e) =>
                    sms &&
                    updateProvider(sms.id, "api_url", e.target.value)
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <input
                  placeholder="API Key"
                  value={sms?.access_token ?? ""}
                  onChange={(e) =>
                    sms &&
                    updateProvider(
                      sms.id,
                      "access_token",
                      e.target.value
                    )
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <input
                  placeholder="Sender ID"
                  value={sms?.sender_id ?? ""}
                  onChange={(e) =>
                    sms &&
                    updateProvider(sms.id, "sender_id", e.target.value)
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <button
                  onClick={() => sms && handleTestConnection(sms.id)}
                  disabled={!sms}
                  className="w-full border border-[#202938] bg-[#111827] py-3 text-white hover:border-amber-500 disabled:opacity-50"
                >
                  Test SMS Provider
                </button>
              </div>
            </div>

            {/* Email */}
            <div className="border border-[#202938] bg-[#0D1117]">
              <div className="flex items-center gap-3 border-b border-[#202938] px-5 py-4">
                <Mail className="h-5 w-5 text-blue-400" />

                <h2 className="font-semibold text-white">
                  Email SMTP
                </h2>
              </div>

              <div className="space-y-4 p-5">
                <input
                  placeholder="SMTP Host"
                  value={email?.smtp_host ?? ""}
                  onChange={(e) =>
                    email &&
                    updateProvider(
                      email.id,
                      "smtp_host",
                      e.target.value
                    )
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <input
                  placeholder="SMTP Port"
                  value={email?.smtp_port ?? ""}
                  onChange={(e) =>
                    email &&
                    updateProvider(
                      email.id,
                      "smtp_port",
                      e.target.value
                    )
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <input
                  placeholder="Username"
                  value={email?.smtp_username ?? ""}
                  onChange={(e) =>
                    email &&
                    updateProvider(
                      email.id,
                      "smtp_username",
                      e.target.value
                    )
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <input
                  placeholder="Password"
                  type="password"
                  value={email?.smtp_password ?? ""}
                  onChange={(e) =>
                    email &&
                    updateProvider(
                      email.id,
                      "smtp_password",
                      e.target.value
                    )
                  }
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={email?.use_tls ?? false}
                    onChange={(e) =>
                      email &&
                      updateProvider(
                        email.id,
                        "use_tls",
                        e.target.checked
                      )
                    }
                  />

                  <span className="text-sm text-white">
                    Enable TLS
                  </span>
                </div>

                <button
                  onClick={() =>
                    email && handleTestConnection(email.id)
                  }
                  disabled={!email}
                  className="w-full border border-[#202938] bg-[#111827] py-3 text-white hover:border-blue-500 disabled:opacity-50"
                >
                  Test SMTP
                </button>
              </div>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
            <div className="border border-[#202938] bg-[#0D1117]">
              <div className="flex items-center gap-3 border-b border-[#202938] px-5 py-4">
                <Server className="h-5 w-5 text-cyan-400" />

                <h2 className="font-semibold text-white">
                  Provider Status
                </h2>
              </div>

              <div className="space-y-4 p-5">
                {providers.map((provider) => (
                  <div
                    key={provider.id}
                    className="flex items-center justify-between border border-[#202938] bg-[#080B10] p-4"
                  >
                    <span className="text-white">
                      {provider.name ?? provider.provider_type}
                    </span>

                    <span
                      className={`rounded-full px-3 py-1 text-xs font-medium ${
                        provider.is_connected
                          ? "bg-green-500/15 text-green-400"
                          : "bg-red-500/15 text-red-400"
                      }`}
                    >
                      {provider.is_connected
                        ? "Connected"
                        : "Disconnected"}
                    </span>
                  </div>
                ))}

                {providers.length === 0 && (
                  <p className="text-center text-sm text-[#64748B]">
                    No providers configured.
                  </p>
                )}
              </div>
            </div>

            <div className="border border-[#202938] bg-[#0D1117]">
              <div className="border-b border-[#202938] px-5 py-4">
                <h2 className="font-semibold text-white">
                  Configuration Summary
                </h2>
              </div>

              <div className="grid gap-4 p-5 md:grid-cols-2">
                <div className="border border-[#202938] bg-[#080B10] p-4">
                  <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                    Active Providers
                  </p>

                  <h3 className="mt-3 text-2xl font-semibold text-green-400">
                    {activeCount}
                  </h3>
                </div>

                <div className="border border-[#202938] bg-[#080B10] p-4">
                  <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                    Connected
                  </p>

                  <h3 className="mt-3 text-2xl font-semibold text-cyan-400">
                    {connectedCount}
                  </h3>
                </div>

                <div className="border border-[#202938] bg-[#080B10] p-4">
                  <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                    Pending Tests
                  </p>

                  <h3 className="mt-3 text-2xl font-semibold text-amber-400">
                    {pendingCount}
                  </h3>
                </div>

                <div className="border border-[#202938] bg-[#080B10] p-4">
                  <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                    Last Updated
                  </p>

                  <h3 className="mt-3 text-lg font-semibold text-white">
                    Today
                  </h3>
                </div>
              </div>

              <div className="border-t border-[#202938] p-5">
                <button
                  onClick={saveAll}
                  disabled={saving}
                  className="w-full bg-green-500 py-3 text-sm font-semibold text-black transition hover:bg-green-400 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save Communication Settings"}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}