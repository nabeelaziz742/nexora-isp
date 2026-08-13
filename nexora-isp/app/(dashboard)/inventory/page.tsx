"use client";

import {
  AlertTriangle,
  Archive,
  Box,
  CheckCircle2,
  Loader2,
  RefreshCw,
  RotateCcw,
  Search,
  Wrench,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  DeviceAssignment,
  InventoryDevice,
  ReturnCondition,
  inventoryService,
} from "@/services/inventory.service";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-PK", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function MetricCard({
  label,
  value,
  description,
  icon: Icon,
}: {
  label: string;
  value: number;
  description: string;
  icon: typeof Box;
}) {
  return (
    <div className="border border-[#202938] bg-[#0D1117] p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-slate-500">
            {label}
          </p>

          <p className="mt-3 text-2xl font-semibold text-slate-50">
            {value}
          </p>
        </div>

        <div className="flex h-9 w-9 items-center justify-center border border-[#202938] bg-[#121821]">
          <Icon className="h-4 w-4 text-blue-400" />
        </div>
      </div>

      <p className="mt-3 border-t border-[#202938] pt-3 text-xs text-slate-500">
        {description}
      </p>
    </div>
  );
}

function statusClass(status: string) {
  switch (status) {
    case "AVAILABLE":
      return "text-emerald-400";
    case "ASSIGNED":
      return "text-blue-400";
    case "FAULTY":
      return "text-red-400";
    case "IN_REPAIR":
      return "text-amber-400";
    case "RETIRED":
      return "text-slate-500";
    default:
      return "text-slate-300";
  }
}

export default function InventoryPage() {
  const [devices, setDevices] = useState<
    InventoryDevice[]
  >([]);
  const [assignments, setAssignments] = useState<
    DeviceAssignment[]
  >([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionId, setActionId] = useState<
    string | null
  >(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const loadInventory = useCallback(
    async (background = false) => {
      try {
        if (background) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        setError("");

        const [
          deviceResponse,
          assignmentResponse,
        ] = await Promise.all([
          inventoryService.getDevices(),
          inventoryService.getAssignments(),
        ]);

        setDevices(deviceResponse);
        setAssignments(assignmentResponse);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load inventory operations.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadInventory();
  }, [loadInventory]);

  const metrics = useMemo(() => {
    return {
      total: devices.length,
      available: devices.filter(
        (device) => device.status === "AVAILABLE",
      ).length,
      assigned: devices.filter(
        (device) => device.status === "ASSIGNED",
      ).length,
      faulty: devices.filter(
        (device) => device.status === "FAULTY",
      ).length,
      inRepair: devices.filter(
        (device) => device.status === "IN_REPAIR",
      ).length,
      retired: devices.filter(
        (device) => device.status === "RETIRED",
      ).length,
    };
  }, [devices]);

  const activeAssignments = useMemo(
    () =>
      assignments.filter(
        (assignment) => assignment.is_active,
      ),
    [assignments],
  );

  const filteredDevices = useMemo(() => {
    const value = search.trim().toLowerCase();

    if (!value) {
      return devices;
    }

    return devices.filter((device) =>
      [
        device.asset_tag,
        device.device_type,
        device.manufacturer,
        device.model_name,
        device.serial_number,
        device.mac_address,
        device.status,
        device.assigned_service_number ?? "",
        device.assigned_customer_number ?? "",
        device.assigned_customer_name ?? "",
      ].some((field) =>
        field.toLowerCase().includes(value),
      ),
    );
  }, [devices, search]);

  const filteredAssignments = useMemo(() => {
    const value = search.trim().toLowerCase();

    if (!value) {
      return activeAssignments;
    }

    return activeAssignments.filter((assignment) =>
      [
        assignment.asset_tag,
        assignment.device_type,
        assignment.service_number,
        assignment.customer_number,
        assignment.customer_name,
      ].some((field) =>
        field.toLowerCase().includes(value),
      ),
    );
  }, [activeAssignments, search]);

  async function handleReturn(
    assignment: DeviceAssignment,
  ) {
    const rawCondition = window
      .prompt(
        "Return condition: GOOD, DAMAGED or FAULTY",
        "GOOD",
      )
      ?.trim()
      .toUpperCase();

    if (
      rawCondition !== "GOOD"
      && rawCondition !== "DAMAGED"
      && rawCondition !== "FAULTY"
    ) {
      return;
    }

    const notes =
      window.prompt(
        "Return notes (optional):",
      )?.trim() ?? "";

    try {
      setActionId(assignment.id);
      setError("");

      await inventoryService.returnDevice(
        assignment.id,
        rawCondition as ReturnCondition,
        notes,
      );

      await loadInventory(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to return device.",
      );
    } finally {
      setActionId(null);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
            Asset Operations
          </p>

          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
            Inventory & Device Operations
          </h1>

          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            Live tenant inventory, serialized device state and
            subscriber equipment custody.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-10 min-w-[280px] items-center gap-2 border border-[#202938] bg-[#0D1117] px-3">
            <Search className="h-4 w-4 text-slate-500" />

            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search devices or custody..."
              className="w-full bg-transparent text-xs text-slate-100 outline-none placeholder:text-slate-600"
            />
          </div>

          <button
            type="button"
            disabled={refreshing}
            onClick={() => void loadInventory(true)}
            className="flex h-10 items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 text-xs text-slate-300 transition hover:border-blue-500 hover:text-blue-400 disabled:opacity-50"
          >
            <RefreshCw
              className={`h-4 w-4 ${
                refreshing ? "animate-spin" : ""
              }`}
            />
            Refresh
          </button>
        </div>
      </section>

      {error ? (
        <div className="border border-red-900/60 bg-red-950/30 px-4 py-3 text-xs text-red-400">
          {error}
        </div>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <MetricCard
          label="Total Assets"
          value={metrics.total}
          description="Registered inventory devices"
          icon={Box}
        />

        <MetricCard
          label="Available"
          value={metrics.available}
          description="Ready for service assignment"
          icon={CheckCircle2}
        />

        <MetricCard
          label="Assigned"
          value={metrics.assigned}
          description="Devices in active custody"
          icon={Archive}
        />

        <MetricCard
          label="Faulty"
          value={metrics.faulty}
          description="Devices marked faulty"
          icon={AlertTriangle}
        />

        <MetricCard
          label="In Repair"
          value={metrics.inRepair}
          description="Devices under repair"
          icon={Wrench}
        />

        <MetricCard
          label="Retired"
          value={metrics.retired}
          description="Retired inventory assets"
          icon={Archive}
        />
      </section>

      <section className="border border-[#202938] bg-[#0D1117]">
        <div className="border-b border-[#202938] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">
            Active Device Custody
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Current device-to-service assignments from the
            custody ledger.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[950px] text-left">
            <thead>
              <tr className="border-b border-[#202938] text-[10px] uppercase tracking-[0.12em] text-slate-500">
                <th className="px-5 py-3">Asset</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">Service</th>
                <th className="px-5 py-3">Customer</th>
                <th className="px-5 py-3">Assigned</th>
                <th className="px-5 py-3">Assigned By</th>
                <th className="px-5 py-3 text-right">
                  Custody
                </th>
              </tr>
            </thead>

            <tbody>
              {filteredAssignments.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-5 py-10 text-center text-sm text-slate-500"
                  >
                    No active device custody records found.
                  </td>
                </tr>
              ) : (
                filteredAssignments.map((assignment) => (
                  <tr
                    key={assignment.id}
                    className="border-b border-[#202938]/80"
                  >
                    <td className="px-5 py-4 text-xs font-medium text-slate-100">
                      {assignment.asset_tag}
                    </td>

                    <td className="px-5 py-4 text-xs text-slate-300">
                      {assignment.device_type}
                    </td>

                    <td className="px-5 py-4 text-xs text-blue-400">
                      {assignment.service_number}
                    </td>

                    <td className="px-5 py-4">
                      <p className="text-xs text-slate-300">
                        {assignment.customer_name}
                      </p>

                      <p className="mt-1 text-[11px] text-slate-600">
                        {assignment.customer_number}
                      </p>
                    </td>

                    <td className="px-5 py-4 text-xs text-slate-500">
                      {formatDate(assignment.assigned_at)}
                    </td>

                    <td className="px-5 py-4 text-xs text-slate-500">
                      {assignment.assigned_by_email
                        ?? "System"}
                    </td>

                    <td className="px-5 py-4 text-right">
                      <button
                        type="button"
                        disabled={
                          actionId === assignment.id
                        }
                        onClick={() =>
                          void handleReturn(assignment)
                        }
                        className="inline-flex items-center gap-2 border border-[#334155] px-3 py-2 text-[11px] text-slate-300 transition hover:border-blue-500 hover:text-blue-400 disabled:opacity-50"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />

                        {actionId === assignment.id
                          ? "Returning..."
                          : "Return Device"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="border border-[#202938] bg-[#0D1117]">
        <div className="border-b border-[#202938] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">
            Inventory Asset Registry
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Current device registry and operational status.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px] text-left">
            <thead>
              <tr className="border-b border-[#202938] text-[10px] uppercase tracking-[0.12em] text-slate-500">
                <th className="px-5 py-3">Asset Tag</th>
                <th className="px-5 py-3">Device</th>
                <th className="px-5 py-3">Serial</th>
                <th className="px-5 py-3">MAC</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Service</th>
                <th className="px-5 py-3">Customer</th>
              </tr>
            </thead>

            <tbody>
              {filteredDevices.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-5 py-10 text-center text-sm text-slate-500"
                  >
                    No inventory devices found.
                  </td>
                </tr>
              ) : (
                filteredDevices.map((device) => (
                  <tr
                    key={device.id}
                    className="border-b border-[#202938]/80"
                  >
                    <td className="px-5 py-4 text-xs font-medium text-slate-100">
                      {device.asset_tag}
                    </td>

                    <td className="px-5 py-4">
                      <p className="text-xs text-slate-300">
                        {device.device_type}
                      </p>

                      <p className="mt-1 text-[11px] text-slate-600">
                        {[
                          device.manufacturer,
                          device.model_name,
                        ]
                          .filter(Boolean)
                          .join(" ") || "—"}
                      </p>
                    </td>

                    <td className="px-5 py-4 text-xs text-slate-500">
                      {device.serial_number || "—"}
                    </td>

                    <td className="px-5 py-4 text-xs text-slate-500">
                      {device.mac_address || "—"}
                    </td>

                    <td className="px-5 py-4">
                      <span
                        className={`text-xs ${statusClass(
                          device.status,
                        )}`}
                      >
                        {device.status}
                      </span>
                    </td>

                    <td className="px-5 py-4 text-xs text-blue-400">
                      {device.assigned_service_number ?? "—"}
                    </td>

                    <td className="px-5 py-4">
                      <p className="text-xs text-slate-300">
                        {device.assigned_customer_name ?? "—"}
                      </p>

                      {device.assigned_customer_number ? (
                        <p className="mt-1 text-[11px] text-slate-600">
                          {device.assigned_customer_number}
                        </p>
                      ) : null}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <p className="text-[11px] text-slate-600">
        Inventory metrics are calculated from current tenant
        device records. No mock stock movement or inferred field
        custody values are displayed.
      </p>
    </div>
  );
}