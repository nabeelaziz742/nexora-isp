"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  CalendarClock,
  Clock3,
  Pencil,
  Plus,
  Power,
  Search,
  Trash2,
} from "lucide-react";
import { communicationsService } from "@/services/communications.service";

export default function CommunicationSchedulesPage() {
  const [schedules, setSchedules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSchedules();
  }, []);

  async function loadSchedules() {
    try {
      const response = await communicationsService.getSchedules();

      const items = Array.isArray(response)
        ? response
        : (response as any).results ?? [];

      setSchedules(items);
    } finally {
      setLoading(false);
    }
  }

  const stats = [
    {
      title: "Active Rules",
      value: schedules.filter((s) => s.is_enabled).length,
      color: "text-green-400",
    },
    {
      title: "Disabled",
      value: schedules.filter((s) => !s.is_enabled).length,
      color: "text-amber-400",
    },
    {
      title: "Today's Runs",
      value: schedules.length,
      color: "text-cyan-400",
    },
    {
      title: "Failed",
      value: 0,
      color: "text-red-400",
    },
  ];

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.20em] text-green-400">
            Communication
          </p>

          <h1 className="mt-2 text-2xl font-semibold text-white">
            Automation Schedules
          </h1>

          <p className="mt-2 text-sm text-[#64748B]">
            Configure recurring communication rules and automations.
          </p>
        </div>

        <Link
          href="/communications/schedules/create"
          className="flex items-center gap-2 bg-green-500 px-5 py-2 text-sm font-medium text-black hover:bg-green-400"
        >
          <Plus className="h-4 w-4" />
          Create Schedule
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((card) => (
          <div
            key={card.title}
            className="border border-[#202938] bg-[#0D1117] p-5"
          >
            <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
              {card.title}
            </p>

            <h2 className={`mt-4 text-3xl font-semibold ${card.color}`}>
              {card.value}
            </h2>
          </div>
        ))}
      </div>

      <div className="border border-[#202938] bg-[#0D1117]">
        <div className="flex flex-col gap-4 border-b border-[#202938] p-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative w-full max-w-md">
            <Search className="absolute left-3 top-3 h-4 w-4 text-[#64748B]" />

            <input
              placeholder="Search schedules..."
              className="w-full border border-[#202938] bg-[#080B10] py-2 pl-10 pr-4 text-sm text-white outline-none"
            />
          </div>

          <select className="border border-[#202938] bg-[#080B10] px-3 py-2 text-sm text-white">
            <option>All Providers</option>
            <option>WhatsApp</option>
            <option>SMS</option>
            <option>Email</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#202938] bg-[#080B10] text-left text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                <th className="px-5 py-4 font-medium">Rule</th>
                <th className="px-5 py-4 font-medium">Trigger</th>
                <th className="px-5 py-4 font-medium">Provider</th>
                <th className="px-5 py-4 font-medium">Next Run</th>
                <th className="px-5 py-4 font-medium">Status</th>
                <th className="px-5 py-4 text-right font-medium">Actions</th>
              </tr>
            </thead>

            <tbody>
              {loading && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-5 py-8 text-center text-sm text-[#64748B]"
                  >
                    Loading schedules...
                  </td>
                </tr>
              )}

              {!loading && schedules.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-5 py-8 text-center text-sm text-[#64748B]"
                  >
                    No schedules found.
                  </td>
                </tr>
              )}

              {!loading &&
                schedules.map((schedule) => (
                  <tr
                    key={schedule.id}
                    className="border-b border-[#202938] transition hover:bg-[#080B10]"
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#111827]">
                          <CalendarClock className="h-5 w-5 text-cyan-400" />
                        </div>

                        <div>
                          <h3 className="font-medium text-white">
                            {schedule.automation_name ?? "-"}
                          </h3>

                          <p className="mt-1 text-xs text-[#64748B]">
                            #{String(schedule.id).slice(0, 8)}
                          </p>
                        </div>
                      </div>
                    </td>

                    <td className="px-5 py-4 text-sm text-[#CBD5E1]">
                      {schedule.trigger ?? "-"}
                    </td>

                    <td className="px-5 py-4">
                      <span className="rounded-md border border-[#202938] bg-[#111827] px-3 py-1 text-xs text-cyan-400">
                        {schedule.provider_name ?? "-"}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2 text-sm text-[#CBD5E1]">
                        <Clock3 className="h-4 w-4 text-[#64748B]" />
                        {schedule.next_run
                          ? new Date(schedule.next_run).toLocaleString()
                          : "--"}
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${
                          schedule.is_enabled
                            ? "bg-green-500/15 text-green-400"
                            : "bg-red-500/15 text-red-400"
                        }`}
                      >
                        {schedule.is_enabled ? "Enabled" : "Disabled"}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      <div className="flex justify-end gap-2">
                        <button className="rounded-md border border-[#202938] bg-[#111827] p-2 hover:border-green-500">
                          <Power className="h-4 w-4 text-green-400" />
                        </button>

                        <button className="rounded-md border border-[#202938] bg-[#111827] p-2 hover:border-blue-500">
                          <Pencil className="h-4 w-4 text-blue-400" />
                        </button>

                        <button className="rounded-md border border-[#202938] bg-[#111827] p-2 hover:border-red-500">
                          <Trash2 className="h-4 w-4 text-red-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}