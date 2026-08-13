"use client";

import Link from "next/link";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { communicationsService } from "@/services/communications.service";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  Plus,
  Search,
  Filter,
  Zap,
  PlayCircle,
  Settings2,
  Clock3,
  Pencil,
  Trash2,
} from "lucide-react";

export default function CommunicationAutomationsPage() {
  const [automations, setAutomations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");

  const [triggerFilter, setTriggerFilter] =
    useState("ALL");

  const [enabledFilter, setEnabledFilter] =
    useState("ALL");

  const [stats, setStats] = useState({
    total: 0,
    enabled: 0,
    disabled: 0,
    executedToday: 0,
  });

  const [executeOpen, setExecuteOpen] =
    useState(false);

  const [selectedAutomation, setSelectedAutomation] =
    useState<any>(null);

  const [customerId, setCustomerId] =
    useState("");

  useEffect(() => {
    loadAutomations();
  }, [
    search,
    triggerFilter,
    enabledFilter,
  ]);

  async function loadAutomations() {
    try {
      setLoading(true);

      const response =
        await communicationsService.getAutomations({
          search,
          trigger:
            triggerFilter === "ALL"
              ? undefined
              : triggerFilter,
          enabled:
            enabledFilter === "ALL"
              ? undefined
              : enabledFilter === "ENABLED",
        });

      const items = response ?? [];

      setAutomations(items);

      const today = new Date();

      setStats({
        total: items.length,

        enabled: items.filter(
          (a: any) => a.is_enabled,
        ).length,

        disabled: items.filter(
          (a: any) => !a.is_enabled,
        ).length,

        executedToday: items.filter((a: any) => {
          if (!a.last_executed_at) return false;

          const d = new Date(
            a.last_executed_at,
          );

          return (
            d.getDate() === today.getDate() &&
            d.getMonth() ===
              today.getMonth() &&
            d.getFullYear() ===
              today.getFullYear()
          );
        }).length,
      });
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to load automations.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function toggleAutomation(
    automation: any,
  ) {
    try {
      if (automation.is_enabled) {
        await communicationsService.disableAutomation(
          automation.id,
        );
      } else {
        await communicationsService.enableAutomation(
          automation.id,
        );
      }

      toast.success(
        automation.is_enabled
          ? "Automation disabled."
          : "Automation enabled.",
      );

      loadAutomations();
    } catch (error) {
      console.error(error);
      toast.error(
        "Unable to update automation.",
      );
    }
  }

  function handleExecute(
    automation: any,
  ) {
    setSelectedAutomation(automation);
    setCustomerId("");
    setExecuteOpen(true);
  }

  async function executeAutomationNow() {
    if (!selectedAutomation) return;

    if (!customerId.trim()) {
      toast.error(
        "Customer ID is required.",
      );
      return;
    }

    try {
      await communicationsService.executeAutomation(
        selectedAutomation.id,
        customerId,
      );

      toast.success(
        "Automation executed successfully.",
      );

      setExecuteOpen(false);

      loadAutomations();
    } catch (error) {
      console.error(error);

      toast.error(
        "Execution failed.",
      );
    }
  }

  async function handleDelete(id: string) {
    if (
      !confirm(
        "Delete this automation?",
      )
    )
      return;

    try {
      await communicationsService.deleteAutomation(
        id,
      );

      toast.success(
        "Automation deleted.",
      );

      loadAutomations();
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to delete automation.",
      );
    }
  }

  const statCards = useMemo(
    () => [
      {
        title: "Total Automations",
        value: stats.total,
        color: "text-cyan-400",
        icon: Settings2,
      },
      {
        title: "Enabled",
        value: stats.enabled,
        color: "text-green-400",
        icon: Zap,
      },
      {
        title: "Disabled",
        value: stats.disabled,
        color: "text-red-400",
        icon: Clock3,
      },
      {
        title: "Executed Today",
        value: stats.executedToday,
        color: "text-blue-400",
        icon: PlayCircle,
      },
    ],
    [stats],
  );

  return (
    <div className="space-y-6 p-6">

      {/* Header */}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">

        <div>

          <p className="text-[10px] font-semibold uppercase tracking-[0.20em] text-green-400">
            Communication
          </p>

          <h1 className="mt-2 text-2xl font-semibold text-white">
            Automation Engine
          </h1>

          <p className="mt-2 text-sm text-[#64748B]">
            Configure automated communication
            workflows triggered by business
            events.
          </p>

        </div>

        <div className="flex items-center gap-3">

          <button
            className="flex items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 py-2 text-sm text-white hover:border-blue-500"
          >

            <Filter className="h-4 w-4"/>

            Filters

          </button>

          <Link
            href="/communications/automations/create"
            className="flex items-center gap-2 bg-green-500 px-4 py-2 text-sm font-medium text-black hover:bg-green-400"
          >

            <Plus className="h-4 w-4"/>

            Create Automation

          </Link>

        </div>

      </div>

      {/* Stats */}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">

        {statCards.map((card) => {

          const Icon = card.icon;

          return (

            <div
              key={card.title}
              className="border border-[#202938] bg-[#0D1117] p-5"
            >

              <div className="flex items-center justify-between">

                <div>

                  <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
                    {card.title}
                  </p>

                  <h2
                    className={`mt-4 text-3xl font-semibold ${card.color}`}
                  >
                    {card.value}
                  </h2>

                </div>

                <Icon
                  className={`h-7 w-7 ${card.color}`}
                />

              </div>

            </div>

          );

        })}

      </div>

      {/* Filters */}

      <div className="border border-[#202938] bg-[#0D1117]">

        <div className="flex flex-col gap-4 border-b border-[#202938] p-5 lg:flex-row lg:items-center lg:justify-between">

          <div className="relative w-full max-w-md">

            <Search className="absolute left-3 top-3 h-4 w-4 text-[#64748B]" />

            <input
              value={search}
              onChange={(e) =>
                setSearch(e.target.value)
              }
              placeholder="Search automations..."
              className="w-full border border-[#202938] bg-[#080B10] py-2 pl-10 pr-4 text-sm text-white outline-none"
            />

          </div>

          <div className="flex items-center gap-3">

            <select
              value={triggerFilter}
              onChange={(e) =>
                setTriggerFilter(
                  e.target.value,
                )
              }
              className="border border-[#202938] bg-[#080B10] px-3 py-2 text-sm text-white"
            >

              <option value="ALL">
                All Triggers
              </option>

              <option value="CUSTOMER_CREATED">
                Customer Created
              </option>

              <option value="SERVICE_ACTIVATED">
                Service Activated
              </option>

              <option value="INVOICE_CREATED">
                Invoice Created
              </option>

              <option value="PAYMENT_RECEIVED">
                Payment Received
              </option>

              <option value="TICKET_CREATED">
                Ticket Created
              </option>

            </select>

            <select
              value={enabledFilter}
              onChange={(e) =>
                setEnabledFilter(
                  e.target.value,
                )
              }
              className="border border-[#202938] bg-[#080B10] px-3 py-2 text-sm text-white"
            >

              <option value="ALL">
                All Status
              </option>

              <option value="ENABLED">
                Enabled
              </option>

              <option value="DISABLED">
                Disabled
              </option>

            </select>

          </div>

        </div>

                <div className="overflow-x-auto">

          <table className="w-full">

            <thead>

              <tr className="border-b border-[#202938] bg-[#080B10] text-left text-[10px] uppercase tracking-[0.15em] text-[#64748B]">

                <th className="px-5 py-4 font-medium">
                  Automation
                </th>

                <th className="px-5 py-4 font-medium">
                  Trigger
                </th>

                <th className="px-5 py-4 font-medium">
                  Template
                </th>

                <th className="px-5 py-4 font-medium">
                  Delay
                </th>

                <th className="px-5 py-4 font-medium">
                  Retry
                </th>

                <th className="px-5 py-4 font-medium">
                  Status
                </th>

                <th className="px-5 py-4 font-medium">
                  Last Execution
                </th>

                <th className="px-5 py-4 text-right font-medium">
                  Actions
                </th>

              </tr>

            </thead>

            <tbody>

              {loading &&
                Array.from({
                  length: 6,
                }).map((_, index) => (
                  <tr key={index}>
                    <td
                      colSpan={8}
                      className="px-5 py-5"
                    >
                      <div className="h-10 animate-pulse rounded bg-[#111827]" />
                    </td>
                  </tr>
                ))}

              {!loading &&
                automations.length === 0 && (
                  <tr>

                    <td
                      colSpan={8}
                      className="py-14 text-center"
                    >

                      <div className="flex flex-col items-center gap-3">

                        <Settings2 className="h-10 w-10 text-[#475569]" />

                        <p className="text-sm text-[#CBD5E1]">
                          No automations found.
                        </p>

                        <p className="text-xs text-[#64748B]">
                          Create your first automation workflow.
                        </p>

                      </div>

                    </td>

                  </tr>
                )}

              {!loading &&
                automations.map(
                  (automation: any) => (

                    <tr
                      key={automation.id}
                      className="border-b border-[#202938] transition-colors hover:bg-[#080B10]"
                    >

                      <td className="px-5 py-4">

                        <div>

                          <h3 className="font-medium text-white">
                            {automation.name}
                          </h3>

                          <p className="mt-1 text-xs text-[#64748B]">
                            {automation.description ||
                              "No description"}
                          </p>

                        </div>

                      </td>

                      <td className="px-5 py-4">

                        <span className="rounded-md border border-[#202938] bg-[#111827] px-3 py-1 text-xs text-cyan-400">

                          {automation.trigger}

                        </span>

                      </td>

                      <td className="px-5 py-4">

                        <div>

                          <p className="text-sm text-white">
                            {automation.template_name}
                          </p>

                          <p className="text-xs text-[#64748B]">
                            {automation.provider_name}
                          </p>

                        </div>

                      </td>

                      <td className="px-5 py-4">

                        <span className="text-sm text-[#CBD5E1]">

                          {automation.delay_minutes}
                          {" "}min

                        </span>

                      </td>

                      <td className="px-5 py-4">

                        <span className="text-sm text-[#CBD5E1]">

                          {automation.max_retry_attempts}

                        </span>

                      </td>

                      <td className="px-5 py-4">

                        <button
                          onClick={() =>
                            toggleAutomation(
                              automation,
                            )
                          }
                          className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                            automation.is_enabled
                              ? "bg-green-500/15 text-green-400"
                              : "bg-red-500/15 text-red-400"
                          }`}
                        >

                          {automation.is_enabled
                            ? "Enabled"
                            : "Disabled"}

                        </button>

                      </td>

                      <td className="px-5 py-4">

                        {automation.last_executed_at ? (

                          <div>

                            <p className="text-sm text-white">

                              {new Date(
                                automation.last_executed_at,
                              ).toLocaleDateString()}

                            </p>

                            <p className="text-xs text-[#64748B]">

                              {automation.last_execution_status}

                            </p>

                          </div>

                        ) : (

                          <span className="text-xs text-[#64748B]">

                            Never

                          </span>

                        )}

                      </td>

                      <td className="px-5 py-4">

                        <div className="flex justify-end gap-2">

                          <button
                            onClick={() =>
                              handleExecute(
                                automation,
                              )
                            }
                            className="rounded-md border border-[#202938] bg-[#111827] p-2 transition hover:border-green-500"
                            title="Execute Now"
                          >

                            <PlayCircle className="h-4 w-4 text-green-400"/>

                          </button>

                          <Link
                            href={`/communications/automations/${automation.id}`}
                            className="rounded-md border border-[#202938] bg-[#111827] p-2 transition hover:border-blue-500"
                          >

                            <Pencil className="h-4 w-4 text-blue-400"/>

                          </Link>

                          <button
                            onClick={() =>
                              handleDelete(
                                automation.id,
                              )
                            }
                            className="rounded-md border border-[#202938] bg-[#111827] p-2 transition hover:border-red-500"
                          >

                            <Trash2 className="h-4 w-4 text-red-400"/>

                          </button>

                        </div>

                      </td>

                    </tr>

                  ),
                )}

            </tbody>

          </table>

        </div>

      </div>

      <Dialog
        open={executeOpen}
        onOpenChange={setExecuteOpen}
      >
        <DialogContent className="max-w-md bg-[#0D1117] border-[#202938]">

          <DialogHeader>
            <DialogTitle>
              Execute Automation
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">

            <p className="text-sm text-[#94A3B8]">
              Running{" "}
              <span className="text-white">
                {selectedAutomation?.name}
              </span>{" "}
              immediately for a specific customer.
            </p>

            <div>

              <label className="mb-2 block text-sm text-white">
                Customer ID
              </label>

              <input
                value={customerId}
                onChange={(e) =>
                  setCustomerId(e.target.value)
                }
                placeholder="Enter customer ID..."
                className="w-full border border-[#202938] bg-[#080B10] px-4 py-2 text-white outline-none"
              />

            </div>

            <div className="flex justify-end gap-3 pt-2">

              <button
                type="button"
                onClick={() => setExecuteOpen(false)}
                className="rounded-md border border-[#202938] bg-[#111827] px-4 py-2 text-sm text-white transition hover:border-cyan-500"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={executeAutomationNow}
                className="rounded-md bg-green-500 px-5 py-2 text-sm font-medium text-black transition hover:bg-green-400"
              >
                Execute Now
              </button>

            </div>

          </div>

        </DialogContent>
      </Dialog>

    </div>
  );
}
