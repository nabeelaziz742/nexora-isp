"use client";

import {
  RefreshCcw,
  Search,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import AutomationDeliveryOverview from "@/components/notifications/AutomationDeliveryOverview";
import NotificationDeliveryLog from "@/components/notifications/NotificationDeliveryLog";
import NotificationMetricCard from "@/components/notifications/NotificationMetricCard";
import { notificationService } from "@/services/notification.service";

import type {
  AutomationDeliverySummary,
  NotificationChannel,
  NotificationDeliveryLogItem,
  NotificationJob,
  NotificationJobStatus,
  NotificationMetric,
  NotificationSummary,
} from "@/types/notifications";

function formatEventType(eventType: string): string {
  return eventType
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-PK", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function NotificationsPage() {
  const [jobs, setJobs] = useState<NotificationJob[]>([]);
  const [summary, setSummary] =
    useState<NotificationSummary | null>(null);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] =
    useState<NotificationJobStatus | "">("");
  const [channelFilter, setChannelFilter] =
    useState<NotificationChannel | "">("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [jobsResponse, summaryResponse] =
        await Promise.all([
          notificationService.getJobs({
            search,
            status: statusFilter,
            channel: channelFilter,
          }),
          notificationService.getSummary(),
        ]);

      setJobs(jobsResponse);
      setSummary(summaryResponse);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load notification operations.",
      );
    } finally {
      setLoading(false);
    }
  }, [
    search,
    statusFilter,
    channelFilter,
  ]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadNotifications();
    }, 250);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [loadNotifications]);

  const metrics = useMemo<NotificationMetric[]>(() => {
    return [
      {
        id: "total",
        label: "Total Jobs",
        value: String(summary?.total ?? 0),
        description: "Tenant notification ledger",
        tone: "PRIMARY",
      },
      {
        id: "sent",
        label: "Sent",
        value: String(summary?.sent ?? 0),
        description: "Provider accepted delivery",
        tone: "HEALTHY",
      },
      {
        id: "pending",
        label: "Pending",
        value: String(summary?.pending ?? 0),
        description: "Awaiting processing",
        tone: "WARNING",
      },
      {
        id: "processing",
        label: "Processing",
        value: String(summary?.processing ?? 0),
        description: "Provider delivery in progress",
        tone: "PRIMARY",
      },
      {
        id: "failed",
        label: "Failed",
        value: String(summary?.failed ?? 0),
        description: "Delivery requires attention",
        tone:
          (summary?.failed ?? 0) > 0
            ? "CRITICAL"
            : "HEALTHY",
      },
      {
        id: "channels",
        label: "SMS / WhatsApp",
        value: `${summary?.sms ?? 0} / ${
          summary?.whatsapp ?? 0
        }`,
        description: "Channel distribution",
        tone: "PRIMARY",
      },
    ];
  }, [summary]);

  const eventSummaries = useMemo<
    AutomationDeliverySummary[]
  >(() => {
    const groups = new Map<
      string,
      AutomationDeliverySummary
    >();

    jobs.forEach((job) => {
      const current = groups.get(job.event_type) ?? {
        id: job.event_type,
        eventType: job.event_type,
        title: formatEventType(job.event_type),
        targeted: 0,
        delivered: 0,
        failed: 0,
        whatsappDelivered: 0,
        smsDelivered: 0,
      };

      current.targeted += 1;

      if (job.status === "SENT") {
        current.delivered += 1;

        if (job.channel === "WHATSAPP") {
          current.whatsappDelivered += 1;
        }

        if (job.channel === "SMS") {
          current.smsDelivered += 1;
        }
      }

      if (job.status === "FAILED") {
        current.failed += 1;
      }

      groups.set(job.event_type, current);
    });

    return Array.from(groups.values());
  }, [jobs]);

  const deliveryLog = useMemo<
    NotificationDeliveryLogItem[]
  >(() => {
    return jobs.map((job) => ({
      id: job.id,
      eventCode: job.id.slice(0, 8).toUpperCase(),
      customerName: job.customer_name,
      customerCode: job.customer_number,
      eventType: job.event_type,
      channel: job.channel,
      status: job.status,
      messageContext: job.message,
      triggeredAt: formatDateTime(job.created_at),
    }));
  }, [jobs]);

  return (
    <div className="space-y-5">
      <section className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-blue-400">
            Customer Communication Operations
          </p>

          <h1 className="mt-2 text-xl font-semibold tracking-tight text-slate-50">
            Notification Operations
          </h1>

          <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-500">
            Monitor real tenant-scoped SMS and WhatsApp
            notification jobs, provider processing and delivery
            outcomes.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void loadNotifications()}
          disabled={loading}
          className="flex h-10 items-center justify-center gap-2 border border-[#202938] bg-[#0D1117] px-4 text-xs font-medium text-slate-300 transition-colors hover:bg-[#121821] disabled:opacity-50"
        >
          <RefreshCcw
            className={`h-3.5 w-3.5 ${
              loading ? "animate-spin" : ""
            }`}
          />
          Refresh
        </button>
      </section>

      <section className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        {metrics.map((metric) => (
          <NotificationMetricCard
            key={metric.id}
            metric={metric}
          />
        ))}
      </section>

      <section className="border border-[#202938] bg-[#0D1117] p-3">
        <div className="grid gap-2 lg:grid-cols-[minmax(0,1fr)_190px_190px]">
          <label className="flex h-10 items-center gap-2 border border-[#202938] bg-[#0A0E14] px-3">
            <Search className="h-3.5 w-3.5 text-slate-600" />

            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search customer, service, event or provider..."
              className="min-w-0 flex-1 bg-transparent text-xs text-slate-200 outline-none placeholder:text-slate-600"
            />
          </label>

          <select
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(
                event.target.value as
                  | NotificationJobStatus
                  | "",
              )
            }
            className="h-10 border border-[#202938] bg-[#0A0E14] px-3 text-xs text-slate-300 outline-none"
          >
            <option value="">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="PROCESSING">
              Processing
            </option>
            <option value="SENT">Sent</option>
            <option value="FAILED">Failed</option>
            <option value="CANCELLED">
              Cancelled
            </option>
          </select>

          <select
            value={channelFilter}
            onChange={(event) =>
              setChannelFilter(
                event.target.value as
                  | NotificationChannel
                  | "",
              )
            }
            className="h-10 border border-[#202938] bg-[#0A0E14] px-3 text-xs text-slate-300 outline-none"
          >
            <option value="">All Channels</option>
            <option value="SMS">SMS</option>
            <option value="WHATSAPP">
              WhatsApp
            </option>
          </select>
        </div>
      </section>

      {error ? (
        <div className="border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400">
          {error}
        </div>
      ) : null}

      <AutomationDeliveryOverview
        summaries={eventSummaries}
      />

      <NotificationDeliveryLog
        deliveries={deliveryLog}
      />
    </div>
  );
}