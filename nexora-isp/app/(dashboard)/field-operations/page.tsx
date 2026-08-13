"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Loader2,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  Send,
  UserRound,
  Wrench,
  X,
} from "lucide-react";
import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  CreateWorkOrderInput,
  CurrentSession,
  SupportComplaint,
  SupportIncident,
  Technician,
  WorkOrder,
  WorkOrderPriority,
  WorkOrderType,
  fieldOperationsService,
} from "@/services/field-operations.service";

const WORK_TYPES: WorkOrderType[] = [
  "INSTALLATION",
  "REPAIR",
  "DEVICE_REPLACEMENT",
  "NETWORK_MAINTENANCE",
  "SITE_VISIT",
  "OTHER",
];

const PRIORITIES: WorkOrderPriority[] = [
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
];

function formatDate(value: string | null) {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-PK", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusClass(status: string) {
  switch (status) {
    case "CREATED":
      return "text-amber-400";
    case "ASSIGNED":
      return "text-blue-400";
    case "DISPATCHED":
      return "text-violet-400";
    case "ONSITE":
      return "text-cyan-400";
    case "COMPLETED":
      return "text-emerald-400";
    default:
      return "text-slate-400";
  }
}

function priorityClass(priority: string) {
  switch (priority) {
    case "CRITICAL":
      return "text-red-400";
    case "HIGH":
      return "text-orange-400";
    case "MEDIUM":
      return "text-amber-400";
    default:
      return "text-slate-400";
  }
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
  icon: typeof Wrench;
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

export default function FieldOperationsPage() {
  const [session, setSession] =
    useState<CurrentSession | null>(null);

  const [workOrders, setWorkOrders] = useState<
    WorkOrder[]
  >([]);

  const [technicians, setTechnicians] = useState<
    Technician[]
  >([]);

  const [technicianId, setTechnicianId] =
    useState("");

  const [complaints, setComplaints] = useState<
    SupportComplaint[]
  >([]);

  const [incidents, setIncidents] = useState<
    SupportIncident[]
  >([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [actionId, setActionId] = useState<
    string | null
  >(null);

  const [showCreate, setShowCreate] = useState(false);

  const [complaintId, setComplaintId] = useState("");
  const [incidentId, setIncidentId] = useState("");
  const [workType, setWorkType] =
    useState<WorkOrderType>("REPAIR");
  const [priority, setPriority] =
    useState<WorkOrderPriority>("MEDIUM");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const isManagement =
    session?.role === "OWNER"
    || session?.role === "STAFF";

  const isTechnician =
    session?.role === "TECHNICIAN";

  const loadData = useCallback(
    async (background = false) => {
      try {
        if (background) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        setError("");

        const sessionResponse =
          await fieldOperationsService.getSession();

        setSession(sessionResponse);

        if (
          sessionResponse.role === "OWNER"
          || sessionResponse.role === "STAFF"
        ) {
          const [
            workOrderResponse,
            technicianResponse,
            complaintResponse,
            incidentResponse,
          ] = await Promise.all([
            fieldOperationsService.getWorkOrders(),
            fieldOperationsService.getTechnicians(),
            fieldOperationsService.getComplaints(),
            fieldOperationsService.getIncidents(),
          ]);

          setWorkOrders(workOrderResponse);
          setTechnicians(technicianResponse);
          setComplaints(complaintResponse);
          setIncidents(incidentResponse);
        } else {
          const workOrderResponse =
            await fieldOperationsService.getWorkOrders();

          setWorkOrders(workOrderResponse);
          setTechnicians([]);
          setComplaints([]);
          setIncidents([]);
        }
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load field operations.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const metrics = useMemo(() => {
    return {
      active: workOrders.filter(
        (item) => item.status !== "COMPLETED",
      ).length,
      created: workOrders.filter(
        (item) => item.status === "CREATED",
      ).length,
      assigned: workOrders.filter(
        (item) => item.status === "ASSIGNED",
      ).length,
      dispatched: workOrders.filter(
        (item) => item.status === "DISPATCHED",
      ).length,
      onsite: workOrders.filter(
        (item) => item.status === "ONSITE",
      ).length,
      completed: workOrders.filter(
        (item) => item.status === "COMPLETED",
      ).length,
    };
  }, [workOrders]);

  const filteredWorkOrders = useMemo(() => {
    const value = search.trim().toLowerCase();

    if (!value) {
      return workOrders;
    }

    return workOrders.filter((item) =>
      [
        item.work_order_number,
        item.title,
        item.work_type,
        item.priority,
        item.status,
        item.customer_number ?? "",
        item.customer_name ?? "",
        item.service_number ?? "",
        item.complaint_number ?? "",
        item.incident_number ?? "",
        item.assigned_technician_name ?? "",
        item.assigned_technician_email ?? "",
      ].some((field) =>
        field.toLowerCase().includes(value),
      ),
    );
  }, [search, workOrders]);

  const selectedComplaint = useMemo(
    () =>
      complaints.find(
        (item) => item.id === complaintId,
      ) ?? null,
    [complaintId, complaints],
  );

  const selectedIncident = useMemo(
    () =>
      incidents.find(
        (item) => item.id === incidentId,
      ) ?? null,
    [incidentId, incidents],
  );

  function resetCreateForm() {
    setComplaintId("");
    setIncidentId("");
    setTechnicianId("");
    setWorkType("REPAIR");
    setPriority("MEDIUM");
    setTitle("");
    setDescription("");
  }

  function selectComplaint(value: string) {
    setComplaintId(value);

    const complaint = complaints.find(
      (item) => item.id === value,
    );

    if (complaint) {
      setTitle(complaint.subject);
      setDescription(complaint.description);

      if (complaint.priority === "CRITICAL") {
        setPriority("CRITICAL");
      } else if (complaint.priority === "HIGH") {
        setPriority("HIGH");
      } else if (complaint.priority === "LOW") {
        setPriority("LOW");
      } else {
        setPriority("MEDIUM");
      }

      if (complaint.category === "INSTALLATION") {
        setWorkType("INSTALLATION");
      } else if (complaint.category === "DEVICE") {
        setWorkType("DEVICE_REPLACEMENT");
      } else {
        setWorkType("REPAIR");
      }
    }
  }

  function selectIncident(value: string) {
    setIncidentId(value);

    const incident = incidents.find(
      (item) => item.id === value,
    );

    if (incident && !complaintId) {
      setTitle(incident.title);
      setDescription(incident.description);
      setWorkType("NETWORK_MAINTENANCE");

      if (incident.severity === "CRITICAL") {
        setPriority("CRITICAL");
      } else if (incident.severity === "MAJOR") {
        setPriority("HIGH");
      } else {
        setPriority("MEDIUM");
      }
    }
  }

  async function handleCreate(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!technicianId) {
      setError(
        "Select a technician before creating the field job.",
      );
      return;
    }

    try {
      setCreating(true);
      setError("");

      const payload: CreateWorkOrderInput = {
        work_type: workType,
        priority,
        title: title.trim(),
        description: description.trim(),
      };

      if (selectedComplaint) {
        payload.complaint_id = selectedComplaint.id;
        payload.customer_id = selectedComplaint.customer_id;
        payload.service_account_id =
          selectedComplaint.service_account_id;
      }

      if (selectedIncident) {
        payload.incident_id = selectedIncident.id;
        payload.network_node_id =
          selectedIncident.network_node_id;
      }

      await fieldOperationsService.createAndAssignWorkOrder(
        payload,
        technicianId,
      );

      setShowCreate(false);
      resetCreateForm();

      await loadData(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to create and assign field job.",
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleAssign(workOrder: WorkOrder) {
    const technicianId = window.prompt(
      [
        "Enter technician ID:",
        "",
        ...technicians.map(
          (technician) =>
            `${technician.full_name || technician.email} — ${technician.id}`,
        ),
      ].join("\n"),
    );

    if (!technicianId?.trim()) {
      return;
    }

    try {
      setActionId(workOrder.id);
      setError("");

      await fieldOperationsService.assignTechnician(
        workOrder.id,
        technicianId.trim(),
      );

      await loadData(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to assign technician.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function handleDispatch(workOrder: WorkOrder) {
    const notes =
      window.prompt(
        "Dispatch notes:",
      )?.trim() ?? "";

    try {
      setActionId(workOrder.id);
      setError("");

      await fieldOperationsService.dispatchWorkOrder(
        workOrder.id,
        notes,
      );

      await loadData(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to dispatch field job.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function handleOnsite(workOrder: WorkOrder) {
    const notes =
      window.prompt(
        "Onsite notes:",
      )?.trim() ?? "";

    try {
      setActionId(workOrder.id);
      setError("");

      await fieldOperationsService.markOnsite(
        workOrder.id,
        notes,
      );

      await loadData(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to mark job onsite.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function handleComplete(
    workOrder: WorkOrder,
  ) {
    const notes = window.prompt(
      "Completion notes are required:",
    );

    if (!notes?.trim()) {
      return;
    }

    try {
      setActionId(workOrder.id);
      setError("");

      await fieldOperationsService.completeWorkOrder(
        workOrder.id,
        notes.trim(),
      );

      await loadData(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to complete field job.",
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
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
            {isTechnician
              ? "Technician Workspace"
              : "Field Operations"}
          </p>

          <h1 className="mt-2 text-xl font-semibold tracking-tight text-[#F8FAFC]">
            {isTechnician
              ? "My Assigned Field Jobs"
              : "Field Operations"}
          </h1>

          <p className="mt-1 text-sm text-[#64748B]">
            {isTechnician
              ? "View and progress only field jobs assigned to your technician account."
              : "Coordinate technician assignment, dispatch and service restoration work."}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-10 min-w-[260px] items-center gap-2 border border-[#202938] bg-[#0D1117] px-3">
            <Search className="h-4 w-4 text-slate-500" />

            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search field jobs..."
              className="w-full bg-transparent text-xs text-slate-100 outline-none placeholder:text-slate-600"
            />
          </div>

          <button
            type="button"
            disabled={refreshing}
            onClick={() => void loadData(true)}
            className="flex h-10 items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 text-xs text-slate-300 transition hover:border-blue-500 hover:text-blue-400 disabled:opacity-50"
          >
            <RefreshCw
              className={`h-4 w-4 ${
                refreshing ? "animate-spin" : ""
              }`}
            />
            Refresh
          </button>

          {isManagement ? (
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="flex h-10 items-center gap-2 bg-[#3B82F6] px-4 text-xs font-medium text-white transition hover:bg-[#2563EB]"
            >
              <Plus className="h-4 w-4" />
              Create Field Job
            </button>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="border border-red-900/60 bg-red-950/30 px-4 py-3 text-xs text-red-400">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <MetricCard
          label="Active Jobs"
          value={metrics.active}
          description="Open field lifecycle"
          icon={Wrench}
        />

        <MetricCard
          label="Awaiting Assignment"
          value={metrics.created}
          description="Created work orders"
          icon={ClipboardList}
        />

        <MetricCard
          label="Assigned"
          value={metrics.assigned}
          description="Technician assigned"
          icon={UserRound}
        />

        <MetricCard
          label="Dispatched"
          value={metrics.dispatched}
          description="Released to field"
          icon={Send}
        />

        <MetricCard
          label="Onsite"
          value={metrics.onsite}
          description="Technician onsite"
          icon={MapPin}
        />

        <MetricCard
          label="Completed"
          value={metrics.completed}
          description="Completed work orders"
          icon={CheckCircle2}
        />
      </div>

      <section className="border border-[#202938] bg-[#0D1117]">
        <div className="border-b border-[#202938] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">
            {isTechnician
              ? "My Work Queue"
              : "Field Work Orders"}
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Live work-order lifecycle from tenant field operations.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1200px] text-left">
            <thead>
              <tr className="border-b border-[#202938] text-[10px] uppercase tracking-[0.12em] text-slate-500">
                <th className="px-5 py-3">Work Order</th>
                <th className="px-5 py-3">Job</th>
                <th className="px-5 py-3">Customer</th>
                <th className="px-5 py-3">Source</th>
                <th className="px-5 py-3">Priority</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Technician</th>
                <th className="px-5 py-3 text-right">
                  Action
                </th>
              </tr>
            </thead>

            <tbody>
              {filteredWorkOrders.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-5 py-12 text-center text-sm text-slate-500"
                  >
                    No field work orders found.
                  </td>
                </tr>
              ) : (
                filteredWorkOrders.map((workOrder) => (
                  <tr
                    key={workOrder.id}
                    className="border-b border-[#202938]/80"
                  >
                    <td className="px-5 py-4">
                      <p className="text-xs font-medium text-blue-400">
                        {workOrder.work_order_number}
                      </p>

                      <p className="mt-1 text-[11px] text-slate-600">
                        {formatDate(workOrder.created_at)}
                      </p>
                    </td>

                    <td className="px-5 py-4">
                      <p className="text-xs font-medium text-slate-100">
                        {workOrder.title}
                      </p>

                      <p className="mt-1 text-[11px] text-slate-600">
                        {workOrder.work_type}
                      </p>
                    </td>

                    <td className="px-5 py-4">
                      <p className="text-xs text-slate-300">
                        {workOrder.customer_name ?? "—"}
                      </p>

                      <p className="mt-1 text-[11px] text-slate-600">
                        {workOrder.service_number
                          ?? workOrder.customer_number
                          ?? "—"}
                      </p>
                    </td>

                    <td className="px-5 py-4 text-xs text-slate-400">
                      {workOrder.complaint_number
                        ?? workOrder.incident_number
                        ?? "Manual Field Job"}
                    </td>

                    <td className="px-5 py-4">
                      <span
                        className={`text-xs ${priorityClass(
                          workOrder.priority,
                        )}`}
                      >
                        {workOrder.priority}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      <span
                        className={`text-xs ${statusClass(
                          workOrder.status,
                        )}`}
                      >
                        {workOrder.status}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      <p className="text-xs text-slate-300">
                        {workOrder.assigned_technician_name
                          || "Unassigned"}
                      </p>

                      {workOrder.assigned_technician_email ? (
                        <p className="mt-1 text-[11px] text-slate-600">
                          {
                            workOrder.assigned_technician_email
                          }
                        </p>
                      ) : null}
                    </td>

                    <td className="px-5 py-4 text-right">
                      {actionId === workOrder.id ? (
                        <Loader2 className="ml-auto h-4 w-4 animate-spin text-blue-400" />
                      ) : null}

                      {actionId !== workOrder.id
                      && isManagement
                      && workOrder.status === "CREATED" ? (
                        <button
                          type="button"
                          onClick={() =>
                            void handleAssign(workOrder)
                          }
                          className="border border-blue-500/50 px-3 py-2 text-[11px] text-blue-400 transition hover:bg-blue-500/10"
                        >
                          Assign Technician
                        </button>
                      ) : null}

                      {actionId !== workOrder.id
                      && isManagement
                      && workOrder.status === "ASSIGNED" ? (
                        <button
                          type="button"
                          onClick={() =>
                            void handleDispatch(workOrder)
                          }
                          className="border border-violet-500/50 px-3 py-2 text-[11px] text-violet-400 transition hover:bg-violet-500/10"
                        >
                          Dispatch
                        </button>
                      ) : null}

                      {actionId !== workOrder.id
                      && isTechnician
                      && workOrder.status === "DISPATCHED" ? (
                        <button
                          type="button"
                          onClick={() =>
                            void handleOnsite(workOrder)
                          }
                          className="border border-cyan-500/50 px-3 py-2 text-[11px] text-cyan-400 transition hover:bg-cyan-500/10"
                        >
                          Mark Onsite
                        </button>
                      ) : null}

                      {actionId !== workOrder.id
                      && isTechnician
                      && workOrder.status === "ONSITE" ? (
                        <button
                          type="button"
                          onClick={() =>
                            void handleComplete(workOrder)
                          }
                          className="border border-emerald-500/50 px-3 py-2 text-[11px] text-emerald-400 transition hover:bg-emerald-500/10"
                        >
                          Complete Job
                        </button>
                      ) : null}

                      {actionId !== workOrder.id
                      && workOrder.status === "COMPLETED" ? (
                        <span className="text-[11px] text-emerald-400">
                          Completed
                        </span>
                      ) : null}

                      {actionId !== workOrder.id
                      && isManagement
                      && (
                        workOrder.status === "DISPATCHED"
                        || workOrder.status === "ONSITE"
                      ) ? (
                        <span className="text-[11px] text-slate-500">
                          Technician in progress
                        </span>
                      ) : null}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {showCreate && isManagement ? (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto border border-[#202938] bg-[#0D1117]">
            <div className="flex items-center justify-between border-b border-[#202938] px-5 py-4">
              <div>
                <h2 className="text-sm font-semibold text-slate-100">
                  Create Field Job
                </h2>

                <p className="mt-1 text-xs text-slate-500">
                  Create a real tenant work order from a
                  complaint, incident or manual field requirement.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="text-slate-500 hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form
              onSubmit={handleCreate}
              className="space-y-4 p-5"
            >
              <div>
                <label className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                  Support Complaint
                </label>

                <select
                  value={complaintId}
                  onChange={(event) =>
                    selectComplaint(event.target.value)
                  }
                  className="mt-2 h-10 w-full border border-[#202938] bg-[#090D13] px-3 text-xs text-slate-200 outline-none"
                >
                  <option value="">
                    No complaint
                  </option>

                  {complaints
                    .filter(
                      (item) =>
                        item.status !== "CLOSED",
                    )
                    .map((item) => (
                      <option
                        key={item.id}
                        value={item.id}
                      >
                        {item.complaint_number} —{" "}
                        {item.customer_name} —{" "}
                        {item.subject}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                  Network Incident
                </label>

                <select
                  value={incidentId}
                  onChange={(event) =>
                    selectIncident(event.target.value)
                  }
                  className="mt-2 h-10 w-full border border-[#202938] bg-[#090D13] px-3 text-xs text-slate-200 outline-none"
                >
                  <option value="">
                    No incident
                  </option>

                  {incidents
                    .filter(
                      (item) =>
                        item.status !== "RESOLVED",
                    )
                    .map((item) => (
                      <option
                        key={item.id}
                        value={item.id}
                      >
                        {item.incident_number} —{" "}
                        {item.title}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                  Assign Technician
                </label>

                <select
                  required
                  value={technicianId}
                  onChange={(event) =>
                    setTechnicianId(event.target.value)
                  }
                  className="mt-2 h-10 w-full border border-[#202938] bg-[#090D13] px-3 text-xs text-slate-200 outline-none"
                >
                  <option value="">
                    Select technician
                  </option>

                  {technicians.map((technician) => (
                    <option
                      key={technician.id}
                      value={technician.id}
                    >
                      {technician.full_name || technician.email}
                      {" — "}
                      {technician.email}
                    </option>
                  ))}
                </select>

                {technicians.length === 0 ? (
                  <p className="mt-2 text-[11px] text-amber-400">
                    No active technician membership is available
                    for this organization.
                  </p>
                ) : (
                  <p className="mt-2 text-[11px] text-slate-600">
                    The new work order will be assigned to this
                    technician immediately after creation.
                  </p>
                )}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                    Work Type
                  </label>

                  <select
                    value={workType}
                    onChange={(event) =>
                      setWorkType(
                        event.target.value as WorkOrderType,
                      )
                    }
                    className="mt-2 h-10 w-full border border-[#202938] bg-[#090D13] px-3 text-xs text-slate-200 outline-none"
                  >
                    {WORK_TYPES.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                    Priority
                  </label>

                  <select
                    value={priority}
                    onChange={(event) =>
                      setPriority(
                        event.target
                          .value as WorkOrderPriority,
                      )
                    }
                    className="mt-2 h-10 w-full border border-[#202938] bg-[#090D13] px-3 text-xs text-slate-200 outline-none"
                  >
                    {PRIORITIES.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                  Job Title
                </label>

                <input
                  required
                  value={title}
                  onChange={(event) =>
                    setTitle(event.target.value)
                  }
                  className="mt-2 h-10 w-full border border-[#202938] bg-[#090D13] px-3 text-xs text-slate-200 outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
                  Description
                </label>

                <textarea
                  required
                  value={description}
                  onChange={(event) =>
                    setDescription(event.target.value)
                  }
                  rows={5}
                  className="mt-2 w-full resize-none border border-[#202938] bg-[#090D13] p-3 text-xs text-slate-200 outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="h-10 border border-[#202938] px-4 text-xs text-slate-400"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={creating || !technicianId}
                  className="flex h-10 items-center gap-2 bg-blue-600 px-4 text-xs font-medium text-white disabled:opacity-50"
                >
                  {creating ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}

                  Create & Assign Job
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {isTechnician ? (
        <div className="flex items-start gap-3 border border-blue-900/50 bg-blue-950/20 p-4">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-blue-400" />

          <p className="text-xs leading-5 text-slate-400">
            Technician access is restricted to work orders
            assigned to this account. Creation, technician
            assignment and dispatch controls are unavailable.
          </p>
        </div>
      ) : null}
    </div>
  );
}
