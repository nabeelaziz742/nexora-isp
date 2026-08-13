"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import {
  communicationsService,
  CommunicationDashboard,
} from "@/services/communications.service";

import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  CalendarClock,
  CheckCircle2,
  Clock3,
  FileText,
  Gauge,
  Mail,
  MessageCircle,
  RefreshCw,
  Send,
  Settings,
  ShieldCheck,
  Smartphone,
  TrendingUp,
  XCircle,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function getOverviewCards(dashboard: CommunicationDashboard | null) {
  return [
    {
      title: "Messages Today",
      value: dashboard?.messages_today.toLocaleString() ?? "0",
      description: "All providers",
      color: "text-cyan-400",
      icon: Activity,
      trend: "+12%",
      trendUp: true,
    },
    {
      title: "Delivered",
      value: (dashboard?.delivered ?? 0).toLocaleString(),
      description: "Successful deliveries",
      color: "text-green-400",
      icon: CheckCircle2,
      trend: "+8%",
      trendUp: true,
    },
    {
      title: "Failed",
      value: (dashboard?.failed ?? 0).toLocaleString(),
      description: "Need retry",
      color: "text-red-400",
      icon: XCircle,
      trend: "-4%",
      trendUp: false,
    },
    {
      title: "Pending Queue",
      value: (dashboard?.pending ?? 0).toLocaleString(),
      description: "Waiting to send",
      color: "text-amber-400",
      icon: Clock3,
      trend: "-6%",
      trendUp: false,
    },
    {
      title: "Scheduled Jobs",
      value: (dashboard?.scheduled_jobs ?? 0).toLocaleString(),
      description: "Upcoming automations",
      color: "text-purple-400",
      icon: CalendarClock,
      trend: "+2%",
      trendUp: true,
    },
    {
      title: "Templates",
      value: (dashboard?.templates ?? 0).toLocaleString(),
      description: "Active templates",
      color: "text-blue-400",
      icon: FileText,
      trend: "+3%",
      trendUp: true,
    },
    {
      title: "Success Rate",
      value: `${dashboard?.success_rate ?? 0}%`,
      description: "Last 30 days",
      color: "text-green-400",
      icon: TrendingUp,
      trend: "+0.4%",
      trendUp: true,
    },
    {
      title: "Broadcasts",
      value: "12",
      description: "This month",
      color: "text-orange-400",
      icon: Send,
      trend: "+12%",
      trendUp: true,
    },
    {
      title: "Automations",
      value: "31",
      description: "Enabled",
      color: "text-emerald-400",
      icon: ShieldCheck,
      trend: "+5%",
      trendUp: true,
    },
  ];
}

const quickActions = [
  {
    title: "Templates",
    href: "/communications/templates",
    icon: FileText,
    description: "Create reusable communication templates.",
  },
  {
    title: "Broadcast",
    href: "/communications/broadcast",
    icon: Send,
    description: "Send announcements to customers.",
  },
  {
    title: "Schedules",
    href: "/communications/schedules",
    icon: CalendarClock,
    description: "Manage recurring reminders.",
  },
  {
    title: "Logs",
    href: "/communications/logs",
    icon: Activity,
    description: "View delivery history.",
  },
  {
    title: "Settings",
    href: "/communications/settings",
    icon: Settings,
    description: "Configure providers.",
  },
];

function getProviderStatus(dashboard: CommunicationDashboard | null) {
  return [
    {
      name: "WhatsApp",
      icon: MessageCircle,
      status: dashboard?.providers.whatsapp ? "Connected" : "Disconnected",
      color: dashboard?.providers.whatsapp
        ? "text-green-400"
        : "text-red-400",
      latency: "120ms",
      lastSync: "2 mins ago",
      apiVersion: "Cloud API v19.0",
    },
    {
      name: "SMS",
      icon: Smartphone,
      status: dashboard?.providers.sms ? "Connected" : "Disconnected",
      color: dashboard?.providers.sms ? "text-cyan-400" : "text-red-400",
      latency: "340ms",
      lastSync: "5 mins ago",
      apiVersion: "Gateway v2.1",
    },
    {
      name: "Email",
      icon: Mail,
      status: dashboard?.providers.email ? "Connected" : "Disconnected",
      color: dashboard?.providers.email ? "text-blue-400" : "text-red-400",
      latency: "210ms",
      lastSync: "8 mins ago",
      apiVersion: "SMTP v3",
    },
  ];
}

const communicationHealth = [
  {
    label: "Queue Health",
    value: "Healthy",
  },
  {
    label: "Webhook",
    value: "Running",
  },
  {
    label: "Automation Engine",
    value: "Active",
  },
  {
    label: "Retry Service",
    value: "Operational",
  },
];

const recentActivity = [
  {
    customer: "Ali Raza",
    type: "Invoice Reminder",
    provider: "WhatsApp",
    status: "Delivered",
    time: "2 mins ago",
  },
  {
    customer: "Ahmed Khan",
    type: "Payment Confirmation",
    provider: "SMS",
    status: "Delivered",
    time: "5 mins ago",
  },
  {
    customer: "Usman",
    type: "Complaint Received",
    provider: "Email",
    status: "Pending",
    time: "12 mins ago",
  },
  {
    customer: "Hamza",
    type: "Welcome Message",
    provider: "WhatsApp",
    status: "Delivered",
    time: "18 mins ago",
  },
  {
    customer: "Bilal Tariq",
    type: "Overdue Notice",
    provider: "SMS",
    status: "Failed",
    time: "24 mins ago",
  },
];

const initialScheduledJobs = [
  {
    title: "Bill Reminder",
    schedule: "Daily • 09:00 AM",
    nextRun: "Today, 09:00 AM",
    enabled: true,
  },
  {
    title: "Overdue Reminder",
    schedule: "Daily • 06:00 PM",
    nextRun: "Today, 06:00 PM",
    enabled: true,
  },
  {
    title: "Suspension Notice",
    schedule: "Every Monday",
    nextRun: "Mon, 09:00 AM",
    enabled: true,
  },
  {
    title: "Welcome Message",
    schedule: "On Customer Creation",
    nextRun: "On trigger",
    enabled: false,
  },
];

const automationOverview = [
  {
    label: "Active Rules",
    value: "31",
    color: "text-emerald-400",
  },
  {
    label: "Disabled Rules",
    value: "4",
    color: "text-[#64748B]",
  },
  {
    label: "Executed Today",
    value: "128",
    color: "text-cyan-400",
  },
  {
    label: "Queued",
    value: "12",
    color: "text-amber-400",
  },
];

const recentBroadcasts = [
  {
    title: "Invoice Reminder",
    audience: "1,425 Customers",
    status: "Completed",
    color: "text-green-400",
  },
  {
    title: "Welcome Campaign",
    audience: "98 Customers",
    status: "Running",
    color: "text-cyan-400",
  },
  {
    title: "Maintenance Notice",
    audience: "421 Customers",
    status: "Scheduled",
    color: "text-purple-400",
  },
];

const deliveryTrend = [
  { day: "Mon", messages: 2120 },
  { day: "Tue", messages: 2310 },
  { day: "Wed", messages: 1980 },
  { day: "Thu", messages: 2540 },
  { day: "Fri", messages: 2710 },
  { day: "Sat", messages: 1860 },
  { day: "Sun", messages: 2486 },
];

const usageDistribution = [
  { name: "WhatsApp", value: 68, color: "bg-green-400" },
  { name: "SMS", value: 22, color: "bg-cyan-400" },
  { name: "Email", value: 10, color: "bg-blue-400" },
];

const activityStatusStyles: Record<
  string,
  { badge: string; icon: typeof CheckCircle2 }
> = {
  Delivered: {
    badge: "border-green-400/30 bg-green-400/10 text-green-400",
    icon: CheckCircle2,
  },
  Pending: {
    badge: "border-amber-400/30 bg-amber-400/10 text-amber-400",
    icon: Clock3,
  },
  Failed: {
    badge: "border-red-400/30 bg-red-400/10 text-red-400",
    icon: XCircle,
  },
};

export default function CommunicationsPage() {
  const [scheduledJobs, setScheduledJobs] = useState(initialScheduledJobs);

  const [dashboard, setDashboard] =
    useState<CommunicationDashboard | null>(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const toggleJob = (title: string) => {
    setScheduledJobs((jobs) =>
      jobs.map((job) =>
        job.title === title ? { ...job, enabled: !job.enabled } : job
      )
    );
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      setLoading(true);

      const data =
        await communicationsService.getDashboard();

      setDashboard(data);

      setError("");
    } catch (err) {
      console.error(err);

      setError("Failed to load dashboard.");
    } finally {
      setLoading(false);
    }
  }

  const overviewCards = getOverviewCards(dashboard);
  const providerStatus = getProviderStatus(dashboard);

  return (
    <div className="space-y-6 p-6">

      <div className="flex flex-wrap items-end justify-between gap-4">

        <div>

          <p className="text-[10px] font-semibold uppercase tracking-[0.20em] text-green-400">
            Communication
          </p>

          <h1 className="mt-2 text-2xl font-semibold text-[#F8FAFC]">
            Communication Center
          </h1>

          <p className="mt-2 text-sm text-[#64748B]">
            Centralized WhatsApp messaging,
            automation, reminders and customer
            communications.
          </p>

        </div>

        <div className="flex items-center gap-3">

          <button
            type="button"
            onClick={loadDashboard}
            className="flex items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 py-2 text-xs font-medium text-[#94A3B8] transition-all duration-200 hover:border-[#3B82F6] hover:text-white"
          >

            <RefreshCw
              className={`h-4 w-4 ${
                loading ? "animate-spin" : ""
              }`}
            />
            Refresh

          </button>

          <button
            type="button"
            className="flex items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 py-2 text-xs font-medium text-[#94A3B8] transition-all duration-200 hover:border-[#3B82F6] hover:text-white"
          >

            <FileText className="h-4 w-4" />
            Create Template

          </button>

          <button
            type="button"
            className="flex items-center gap-2 bg-green-500 px-4 py-2 text-xs font-semibold text-black transition-all duration-200 hover:bg-green-400"
          >

            <Send className="h-4 w-4" />
            New Broadcast

          </button>

        </div>

      </div>

      {error && (

        <div className="border border-red-400/30 bg-red-400/10 px-4 py-3 text-xs text-red-400">
          {error}
        </div>

      )}

      {loading && (

        <div className="rounded border border-[#202938] bg-[#0D1117] p-6 text-center text-[#94A3B8]">
          Loading Communication Dashboard...
        </div>

      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">

        {overviewCards.map((card) => {

          const Icon = card.icon;
          const TrendIcon = card.trendUp ? ArrowUpRight : ArrowDownRight;

          return (

            <div
              key={card.title}
              className="border border-[#202938] bg-[#0D1117] p-5 transition-all duration-200 hover:border-[#3B82F6]"
            >

              <div className="flex items-start justify-between">

                <div>

                  <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                    {card.title}
                  </p>

                  <h2 className={`mt-4 text-3xl font-semibold ${card.color}`}>
                    {card.value}
                  </h2>

                  <div className="mt-3 flex items-center gap-2">

                    <span
                      className={`flex items-center gap-1 text-xs font-medium ${
                        card.trendUp ? "text-green-400" : "text-red-400"
                      }`}
                    >

                      <TrendIcon className="h-3 w-3" />
                      {card.trend}

                    </span>

                    <p className="text-xs text-[#64748B]">
                      {card.description}
                    </p>

                  </div>

                </div>

                <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-[#202938] bg-[#111827]">

                  <Icon className={`h-5 w-5 ${card.color}`} />

                </div>

              </div>

            </div>

          );

        })}

      </div>

      <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">

        <div className="border border-[#202938] bg-[#0D1117]">

          <div className="border-b border-[#202938] px-5 py-4">

            <h2 className="text-sm font-semibold text-white">
              Quick Actions
            </h2>

          </div>

          <div className="space-y-3 p-4">

            {quickActions.map((action) => {

              const Icon = action.icon;

              return (

                <Link
                  key={action.title}
                  href={action.href}
                  className="flex items-center gap-4 border border-[#202938] bg-[#080B10] p-4 transition-all duration-200 hover:border-[#3B82F6] hover:bg-[#111827]"
                >

                  <div className="flex h-11 w-11 items-center justify-center bg-[#111827]">

                    <Icon className="h-5 w-5 text-blue-400" />

                  </div>

                  <div>

                    <h3 className="text-sm font-medium text-white">
                      {action.title}
                    </h3>

                    <p className="mt-1 text-xs text-[#64748B]">
                      {action.description}
                    </p>

                  </div>

                </Link>

              );

            })}

          </div>

          <div className="border-t border-[#202938]">

            <div className="border-b border-[#202938] px-5 py-4">

              <h2 className="text-sm font-semibold text-white">
                Communication Health
              </h2>

            </div>

            <div className="grid grid-cols-2 gap-3 p-4">

              {communicationHealth.map((item) => (

                <div
                  key={item.label}
                  className="border border-[#202938] bg-[#080B10] p-4"
                >

                  <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                    {item.label}
                  </p>

                  <p className="mt-3 text-sm font-semibold text-green-400">
                    {item.value}
                  </p>

                </div>

              ))}

            </div>

          </div>

          <div className="border-t border-[#202938]">

            <div className="border-b border-[#202938] px-5 py-4">

              <h2 className="text-sm font-semibold text-white">
                Usage Distribution
              </h2>

              <p className="mt-1 text-xs text-[#64748B]">
                Share of messages by provider.
              </p>

            </div>

            <div className="space-y-4 p-4">

              {usageDistribution.map((item) => (

                <div key={item.name}>

                  <div className="mb-1.5 flex items-center justify-between text-xs">

                    <span className="text-[#94A3B8]">{item.name}</span>
                    <span className="font-medium text-white">{item.value}%</span>

                  </div>

                  <div className="h-2 w-full overflow-hidden rounded-full bg-[#111827]">

                    <div
                      className={`h-full rounded-full ${item.color}`}
                      style={{ width: `${item.value}%` }}
                    />

                  </div>

                </div>

              ))}

            </div>

          </div>

        </div>

        <div className="space-y-6">

          <div className="border border-[#202938] bg-[#0D1117]">

            <div className="flex items-center justify-between border-b border-[#202938] px-5 py-4">

              <div>

                <h2 className="text-sm font-semibold text-white">
                  Communication Providers
                </h2>

                <p className="mt-1 text-xs text-[#64748B]">
                  Current messaging infrastructure.
                </p>

              </div>

              <MessageCircle className="h-5 w-5 text-green-400" />

            </div>

            <div className="grid grid-cols-1 gap-4 p-5 sm:grid-cols-3">

              {providerStatus.map((provider) => {

                const Icon = provider.icon;

                return (

                  <div
                    key={provider.name}
                    className="border border-[#202938] bg-[#080B10] p-4"
                  >

                    <div className="flex items-center gap-4">

                      <div className="flex h-11 w-11 items-center justify-center bg-[#111827]">

                        <Icon className={`h-5 w-5 ${provider.color}`} />

                      </div>

                      <div>

                        <h3 className="text-sm font-medium text-white">
                          {provider.name}
                        </h3>

                        <p className={`mt-1 text-xs ${provider.color}`}>
                          {provider.status}
                        </p>

                      </div>

                    </div>

                    <div className="mt-4 space-y-2 border-t border-[#202938] pt-3 text-xs">

                      <div className="flex items-center justify-between">

                        <span className="text-[#64748B]">Latency</span>
                        <span className="text-[#94A3B8]">{provider.latency}</span>

                      </div>

                      <div className="flex items-center justify-between">

                        <span className="text-[#64748B]">Last Sync</span>
                        <span className="text-[#94A3B8]">{provider.lastSync}</span>

                      </div>

                      <div className="flex items-center justify-between">

                        <span className="text-[#64748B]">API Version</span>
                        <span className="text-[#94A3B8]">{provider.apiVersion}</span>

                      </div>

                    </div>

                  </div>

                );

              })}

            </div>

            <div className="grid grid-cols-3 gap-4 border-t border-[#202938] p-5">

              <div className="border border-[#202938] bg-[#080B10] p-4">

                <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                  Queue
                </p>

                <h3 className="mt-3 text-lg font-semibold text-blue-400">
                  36
                </h3>

              </div>

              <div className="border border-[#202938] bg-[#080B10] p-4">

                <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                  Success
                </p>

                <h3 className="mt-3 text-lg font-semibold text-green-400">
                  98.8%
                </h3>

              </div>

              <div className="border border-[#202938] bg-[#080B10] p-4">

                <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                  Failed
                </p>

                <h3 className="mt-3 text-lg font-semibold text-red-400">
                  19
                </h3>

              </div>

            </div>

          </div>

          <div className="border border-[#202938] bg-[#0D1117]">

            <div className="border-b border-[#202938] px-5 py-4">

              <h2 className="text-sm font-semibold text-white">
                Recent Communication Activity
              </h2>

            </div>

            <div className="overflow-x-auto">

              <table className="w-full text-left text-sm">

                <thead>

                  <tr className="border-b border-[#202938] text-[10px] uppercase tracking-[0.15em] text-[#64748B]">

                    <th className="px-5 py-3 font-medium">Customer</th>
                    <th className="px-5 py-3 font-medium">Type</th>
                    <th className="px-5 py-3 font-medium">Provider</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Time</th>

                  </tr>

                </thead>

                <tbody>

                  {recentActivity.map((item) => {

                    const statusStyle = activityStatusStyles[item.status];
                    const StatusIcon = statusStyle.icon;

                    return (

                      <tr
                        key={`${item.customer}-${item.time}`}
                        className="border-b border-[#202938] last:border-b-0"
                      >

                        <td className="px-5 py-3 text-white">{item.customer}</td>
                        <td className="px-5 py-3 text-[#94A3B8]">{item.type}</td>
                        <td className="px-5 py-3 text-[#94A3B8]">{item.provider}</td>
                        <td className="px-5 py-3">

                          <span
                            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${statusStyle.badge}`}
                          >

                            <StatusIcon className="h-3 w-3" />
                            {item.status}

                          </span>

                        </td>
                        <td className="px-5 py-3 text-[#64748B]">{item.time}</td>

                      </tr>

                    );

                  })}

                </tbody>

              </table>

            </div>

          </div>

          <div className="border border-[#202938] bg-[#0D1117]">

            <div className="border-b border-[#202938] px-5 py-4">

              <h2 className="text-sm font-semibold text-white">
                Scheduled Jobs
              </h2>

            </div>

            <div className="grid grid-cols-1 gap-4 p-5 sm:grid-cols-2">

              {scheduledJobs.map((job) => (

                <div
                  key={job.title}
                  className="border border-[#202938] bg-[#080B10] p-4"
                >

                  <div className="flex items-start justify-between gap-3">

                    <div>

                      <h3 className="text-sm font-medium text-white">
                        {job.title}
                      </h3>

                      <p className="mt-1 text-xs text-[#64748B]">
                        {job.schedule}
                      </p>

                    </div>

                    <button
                      type="button"
                      onClick={() => toggleJob(job.title)}
                      aria-pressed={job.enabled}
                      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors duration-200 ${
                        job.enabled ? "bg-green-500" : "bg-[#202938]"
                      }`}
                    >

                      <span
                        className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform duration-200 ${
                          job.enabled ? "translate-x-4" : "translate-x-0.5"
                        }`}
                      />

                    </button>

                  </div>

                  <div className="mt-4 flex items-center justify-between border-t border-[#202938] pt-3 text-xs">

                    <div>

                      <p className="text-[#64748B]">Next Run</p>
                      <p className="mt-1 text-[#94A3B8]">{job.nextRun}</p>

                    </div>

                    <span
                      className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                        job.enabled
                          ? "border-green-400/30 bg-green-400/10 text-green-400"
                          : "border-[#202938] bg-[#111827] text-[#64748B]"
                      }`}
                    >

                      {job.enabled ? "Active" : "Paused"}

                    </span>

                  </div>

                </div>

              ))}

            </div>

          </div>

          <div className="border border-[#202938] bg-[#0D1117]">

            <div className="border-b border-[#202938] px-5 py-4">

              <h2 className="text-sm font-semibold text-white">
                Automation Overview
              </h2>

            </div>

            <div className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-4">

              {automationOverview.map((item) => (

                <div
                  key={item.label}
                  className="border border-[#202938] bg-[#080B10] p-4"
                >

                  <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                    {item.label}
                  </p>

                  <h3 className={`mt-3 text-2xl font-semibold ${item.color}`}>
                    {item.value}
                  </h3>

                </div>

              ))}

            </div>

          </div>

          <div className="border border-[#202938] bg-[#0D1117]">

            <div className="border-b border-[#202938] px-5 py-4">

              <h2 className="text-sm font-semibold text-white">
                Recent Broadcasts
              </h2>

            </div>

            <div className="divide-y divide-[#202938]">

              {recentBroadcasts.map((broadcast) => (

                <div
                  key={broadcast.title}
                  className="flex items-center justify-between px-5 py-4"
                >

                  <div className="flex items-center gap-4">

                    <div className="flex h-10 w-10 items-center justify-center bg-[#111827]">

                      <Send className="h-4 w-4 text-orange-400" />

                    </div>

                    <div>

                      <h3 className="text-sm font-medium text-white">
                        {broadcast.title}
                      </h3>

                      <p className="mt-1 text-xs text-[#64748B]">
                        {broadcast.audience}
                      </p>

                    </div>

                  </div>

                  <span className={`text-xs font-medium ${broadcast.color}`}>
                    {broadcast.status}
                  </span>

                </div>

              ))}

            </div>

          </div>

          <div className="border border-[#202938] bg-[#0D1117]">

            <div className="flex items-center justify-between border-b border-[#202938] px-5 py-4">

              <div>

                <h2 className="text-sm font-semibold text-white">
                  Message Delivery Trend
                </h2>

                <p className="mt-1 text-xs text-[#64748B]">
                  Messages sent, last 7 days.
                </p>

              </div>

              <div className="flex items-center gap-2 text-xs text-[#64748B]">

                <Gauge className="h-4 w-4" />
                7 Days

              </div>

            </div>

            <div className="h-64 p-5">

              <ResponsiveContainer width="100%" height="100%">

                <LineChart data={deliveryTrend}>

                  <CartesianGrid strokeDasharray="3 3" stroke="#202938" vertical={false} />
                  <XAxis
                    dataKey="day"
                    stroke="#64748B"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: "#202938" }}
                  />
                  <YAxis
                    stroke="#64748B"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    width={40}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0D1117",
                      border: "1px solid #202938",
                      borderRadius: 0,
                      fontSize: 12,
                      color: "#F8FAFC",
                    }}
                    labelStyle={{ color: "#94A3B8" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="messages"
                    stroke="#22D3EE"
                    strokeWidth={2}
                    dot={{ r: 3, fill: "#22D3EE" }}
                    activeDot={{ r: 5 }}
                  />

                </LineChart>

              </ResponsiveContainer>

            </div>

          </div>

        </div>

      </div>

    </div>
  );
}
