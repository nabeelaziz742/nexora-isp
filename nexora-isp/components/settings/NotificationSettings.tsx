"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import ErrorState from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import {
  communicationsService,
  type CommunicationAutomation,
  type CommunicationProvider,
} from "@/services/communications.service";

type Channel = CommunicationProvider["provider_type"];

const CHANNELS: { type: Channel; name: string; description: string }[] = [
  {
    type: "WHATSAPP",
    name: "WhatsApp",
    description: "Customer billing, outage and service lifecycle communication.",
  },
  {
    type: "SMS",
    name: "SMS",
    description: "Critical service alerts and payment workflow notifications.",
  },
  {
    type: "EMAIL",
    name: "Email",
    description: "Bills, payment confirmations and structured customer notices.",
  },
];

const EVENTS: { trigger: string; eventName: string; description: string }[] = [
  { trigger: "INVOICE_GENERATED", eventName: "Bill Generated", description: "Notify customer when a new billing cycle bill is generated." },
  { trigger: "PAYMENT_VERIFIED", eventName: "Payment Received", description: "Confirm a verified customer payment." },
  { trigger: "SERVICE_SUSPENDED", eventName: "Service Suspended", description: "Notify customer when service is suspended for verified non-payment." },
  { trigger: "SERVICE_RESTORED", eventName: "Service Restored", description: "Confirm service restoration after payment verification." },
  { trigger: "CUSTOMER_CREATED", eventName: "Customer Welcome", description: "Welcome a newly activated customer." },
  { trigger: "COMPLAINT_CREATED", eventName: "Complaint Logged", description: "Acknowledge a new customer complaint." },
  { trigger: "COMPLAINT_CLOSED", eventName: "Complaint Resolved", description: "Tell the customer their complaint was resolved." },
];

function channelStatus(providers: CommunicationProvider[], type: Channel) {
  const matching = providers.filter((provider) => provider.provider_type === type);
  if (matching.some((provider) => provider.is_connected)) {
    return { enabled: true, label: "Connected" };
  }
  if (type === "SMS") {
    return { enabled: false, label: "SMS gateway not available yet" };
  }
  if (matching.length > 0) {
    return { enabled: false, label: "Configured, not connected" };
  }
  return { enabled: false, label: "Configuration Required" };
}

export default function NotificationSettings() {
  const [providers, setProviders] = useState<CommunicationProvider[]>([]);
  const [automations, setAutomations] = useState<CommunicationAutomation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [providerData, automationData] = await Promise.all([
        communicationsService.getProviders(),
        communicationsService.getAutomations(),
      ]);
      setProviders(providerData);
      setAutomations(automationData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load notification settings.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  if (loading) {
    return <SkeletonCard />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void loadData()} />;
  }

  function isRouted(trigger: string, channel: Channel) {
    return automations.some(
      (automation) =>
        automation.is_enabled &&
        automation.trigger === trigger &&
        automation.provider_type === channel,
    );
  }

  return (
    <div className="space-y-6">
      <section className="border border-[#202938] bg-[#0D1117]">
        <div className="flex items-start justify-between gap-4 border-b border-[#202938] px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Notification Channels
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Customer communication delivery channels
            </p>
          </div>

          <Link
            href="/communications/providers"
            className="flex shrink-0 items-center gap-1 text-xs font-medium text-blue-400 transition hover:text-blue-300"
          >
            Manage Providers
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="grid gap-px bg-[#202938] md:grid-cols-3">
          {CHANNELS.map((channel) => {
            const status = channelStatus(providers, channel.type);

            return (
              <div
                key={channel.type}
                className="bg-[#0D1117] p-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-slate-200">
                      {channel.name}
                    </p>

                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      {channel.description}
                    </p>
                  </div>

                  <div
                    className={`relative mt-1 h-5 w-9 shrink-0 ${
                      status.enabled
                        ? "bg-blue-600"
                        : "bg-slate-700"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 h-4 w-4 bg-white ${
                        status.enabled
                          ? "left-[18px]"
                          : "left-0.5"
                      }`}
                    />
                  </div>
                </div>

                <div className="mt-4 border-t border-[#202938] pt-3">
                  <span
                    className={`text-[10px] font-medium ${
                      status.enabled
                        ? "text-emerald-400"
                        : "text-amber-400"
                    }`}
                  >
                    {status.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="overflow-hidden border border-[#202938] bg-[#0D1117]">
        <div className="flex items-start justify-between gap-4 border-b border-[#202938] px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Notification Event Matrix
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Channels with an enabled automation for each customer event
            </p>
          </div>

          <Link
            href="/communications/automations"
            className="flex shrink-0 items-center gap-1 text-xs font-medium text-blue-400 transition hover:text-blue-300"
          >
            Manage Automations
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] border-collapse">
            <thead>
              <tr className="border-b border-[#202938] bg-[#0A0E14]">
                <TableHead>Operational Event</TableHead>
                <TableHead>WhatsApp</TableHead>
                <TableHead>SMS</TableHead>
                <TableHead>Email</TableHead>
              </tr>
            </thead>

            <tbody>
              {EVENTS.map((event) => (
                <tr
                  key={event.trigger}
                  className="border-b border-[#202938] last:border-b-0"
                >
                  <td className="px-5 py-4">
                    <p className="text-xs font-medium text-slate-200">
                      {event.eventName}
                    </p>

                    <p className="mt-1 max-w-2xl text-[11px] leading-5 text-slate-500">
                      {event.description}
                    </p>
                  </td>

                  <ChannelCell enabled={isRouted(event.trigger, "WHATSAPP")} />
                  <ChannelCell enabled={isRouted(event.trigger, "SMS")} />
                  <ChannelCell enabled={isRouted(event.trigger, "EMAIL")} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

interface TableHeadProps {
  children: React.ReactNode;
}

function TableHead({ children }: TableHeadProps) {
  return (
    <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
      {children}
    </th>
  );
}

interface ChannelCellProps {
  enabled: boolean;
}

function ChannelCell({
  enabled,
}: ChannelCellProps) {
  return (
    <td className="px-5 py-4">
      <span
        className={`inline-flex px-2 py-1 text-[10px] font-semibold ${
          enabled
            ? "bg-emerald-500/10 text-emerald-400"
            : "bg-slate-500/10 text-slate-600"
        }`}
      >
        {enabled ? "ENABLED" : "OFF"}
      </span>
    </td>
  );
}
