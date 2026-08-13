"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Loader2,
  RefreshCw,
  Search,
  Ticket,
  Users,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Complaint,
  ComplaintStatus,
  Incident,
  IncidentStatus,
  supportService,
} from "@/services/support.service";

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
  icon: typeof Ticket;
}) {
  return (
    <div className="border border-[#202938] bg-[#0D1117] p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-[#64748B]">
            {label}
          </p>

          <p className="mt-3 text-2xl font-semibold text-[#F8FAFC]">
            {value}
          </p>
        </div>

        <div className="flex h-9 w-9 items-center justify-center border border-[#202938] bg-[#121821]">
          <Icon className="h-4 w-4 text-blue-400" />
        </div>
      </div>

      <p className="mt-3 border-t border-[#202938] pt-3 text-xs text-[#64748B]">
        {description}
      </p>
    </div>
  );
}

function nextComplaintStatus(
  status: ComplaintStatus,
): ComplaintStatus | null {
  const transitions: Record<
    ComplaintStatus,
    ComplaintStatus | null
  > = {
    OPEN: "IN_PROGRESS",
    IN_PROGRESS: "RESOLVED",
    RESOLVED: "CLOSED",
    CLOSED: null,
  };

  return transitions[status];
}

function nextIncidentStatus(
  status: IncidentStatus,
): IncidentStatus | null {
  const transitions: Record<
    IncidentStatus,
    IncidentStatus | null
  > = {
    OPEN: "INVESTIGATING",
    INVESTIGATING: "IDENTIFIED",
    IDENTIFIED: "MONITORING",
    MONITORING: "RESOLVED",
    RESOLVED: null,
  };

  return transitions[status];
}

export default function SupportPage() {
  const [complaints, setComplaints] = useState<Complaint[]>(
    [],
  );
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionId, setActionId] = useState<string | null>(
    null,
  );
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const loadSupportData = useCallback(
    async (background = false) => {
      try {
        if (background) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        setError("");

        const [
          complaintResponse,
          incidentResponse,
        ] = await Promise.all([
          supportService.getComplaints(),
          supportService.getIncidents(),
        ]);

        setComplaints(complaintResponse);
        setIncidents(incidentResponse);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load support operations.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadSupportData();
  }, [loadSupportData]);

  const metrics = useMemo(() => {
    const openComplaints = complaints.filter(
      (item) =>
        item.status === "OPEN"
        || item.status === "IN_PROGRESS",
    ).length;

    const activeIncidents = incidents.filter(
      (item) => item.status !== "RESOLVED",
    ).length;

    const criticalComplaints = complaints.filter(
      (item) =>
        item.priority === "CRITICAL"
        && item.status !== "CLOSED",
    ).length;

    const affectedServices = new Set(
      incidents
        .filter((item) => item.status !== "RESOLVED")
        .flatMap((item) =>
          item.affected_services.map(
            (service) => service.service_account_id,
          ),
        ),
    ).size;

    const resolvedComplaints = complaints.filter(
      (item) =>
        item.status === "RESOLVED"
        || item.status === "CLOSED",
    ).length;

    const resolvedIncidents = incidents.filter(
      (item) => item.status === "RESOLVED",
    ).length;

    return {
      openComplaints,
      activeIncidents,
      criticalComplaints,
      affectedServices,
      resolvedComplaints,
      resolvedIncidents,
    };
  }, [complaints, incidents]);

  const filteredComplaints = useMemo(() => {
    const value = search.trim().toLowerCase();

    if (!value) {
      return complaints;
    }

    return complaints.filter((item) =>
      [
        item.complaint_number,
        item.customer_number,
        item.customer_name,
        item.service_number ?? "",
        item.subject,
        item.category,
        item.priority,
        item.status,
      ].some((field) =>
        field.toLowerCase().includes(value),
      ),
    );
  }, [complaints, search]);

  const filteredIncidents = useMemo(() => {
    const value = search.trim().toLowerCase();

    if (!value) {
      return incidents;
    }

    return incidents.filter((item) =>
      [
        item.incident_number,
        item.title,
        item.network_node_name ?? "",
        item.network_node_code ?? "",
        item.severity,
        item.status,
      ].some((field) =>
        field.toLowerCase().includes(value),
      ),
    );
  }, [incidents, search]);

  async function advanceComplaint(
    complaint: Complaint,
  ) {
    const targetStatus = nextComplaintStatus(
      complaint.status,
    );

    if (!targetStatus) {
      return;
    }

    let resolutionNotes = "";

    if (targetStatus === "RESOLVED") {
      resolutionNotes =
        window.prompt(
          "Enter complaint resolution notes:",
        )?.trim() ?? "";

      if (!resolutionNotes) {
        return;
      }
    }

    try {
      setActionId(complaint.id);
      setError("");

      await supportService.transitionComplaint(
        complaint.id,
        targetStatus,
        resolutionNotes,
      );

      await loadSupportData(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to update complaint.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function advanceIncident(
    incident: Incident,
  ) {
    const targetStatus = nextIncidentStatus(
      incident.status,
    );

    if (!targetStatus) {
      return;
    }

    let rootCause = "";
    let resolutionNotes = "";

    if (targetStatus === "IDENTIFIED") {
      rootCause =
        window.prompt(
          "Enter verified incident root cause:",
        )?.trim() ?? "";

      if (!rootCause) {
        return;
      }
    }

    if (targetStatus === "RESOLVED") {
      resolutionNotes =
        window.prompt(
          "Enter incident resolution notes:",
        )?.trim() ?? "";

      if (!resolutionNotes) {
        return;
      }
    }

    try {
      setActionId(incident.id);
      setError("");

      await supportService.transitionIncident(
        incident.id,
        targetStatus,
        rootCause,
        resolutionNotes,
      );

      await loadSupportData(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to update incident.",
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
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-blue-400">
            Support Operations
          </p>

          <h1 className="mt-2 text-xl font-semibold tracking-tight text-[#F8FAFC]">
            Support & Incident Management
          </h1>

          <p className="mt-1 text-sm text-[#64748B]">
            Live tenant-scoped complaints, incidents and
            affected service operations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex h-10 min-w-[280px] items-center gap-2 border border-[#202938] bg-[#0D1117] px-3">
            <Search className="h-4 w-4 text-[#64748B]" />

            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search complaints and incidents..."
              className="w-full bg-transparent text-xs text-[#F8FAFC] outline-none placeholder:text-[#475569]"
            />
          </div>

          <button
            type="button"
            onClick={() => void loadSupportData(true)}
            disabled={refreshing}
            className="flex h-10 items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 text-xs text-[#CBD5E1] transition hover:border-blue-500 hover:text-blue-400 disabled:opacity-50"
          >
            <RefreshCw
              className={`h-4 w-4 ${
                refreshing ? "animate-spin" : ""
              }`}
            />
            Refresh
          </button>
        </div>
      </div>

      {error ? (
        <div className="border border-red-900/60 bg-red-950/30 px-4 py-3 text-xs text-red-400">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <MetricCard
          label="Open Tickets"
          value={metrics.openComplaints}
          description="Open and in-progress complaints"
          icon={Ticket}
        />

        <MetricCard
          label="Active Incidents"
          value={metrics.activeIncidents}
          description="Unresolved network incidents"
          icon={AlertTriangle}
        />

        <MetricCard
          label="Critical Tickets"
          value={metrics.criticalComplaints}
          description="Active critical-priority complaints"
          icon={AlertTriangle}
        />

        <MetricCard
          label="Affected Services"
          value={metrics.affectedServices}
          description="Exact services in active incidents"
          icon={Users}
        />

        <MetricCard
          label="Resolved Tickets"
          value={metrics.resolvedComplaints}
          description="Resolved or closed complaints"
          icon={CheckCircle2}
        />

        <MetricCard
          label="Resolved Incidents"
          value={metrics.resolvedIncidents}
          description="Completed incident lifecycles"
          icon={CheckCircle2}
        />
      </div>

      <section className="border border-[#202938] bg-[#0D1117]">
        <div className="border-b border-[#202938] px-5 py-4">
          <h2 className="text-sm font-semibold text-[#F8FAFC]">
            Active Incident Operations
          </h2>

          <p className="mt-1 text-xs text-[#64748B]">
            Real incidents and explicitly persisted affected
            service accounts.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1000px] text-left">
            <thead>
              <tr className="border-b border-[#202938] text-[10px] uppercase tracking-[0.12em] text-[#64748B]">
                <th className="px-5 py-3">Incident</th>
                <th className="px-5 py-3">Node</th>
                <th className="px-5 py-3">Severity</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Affected</th>
                <th className="px-5 py-3">Started</th>
                <th className="px-5 py-3 text-right">
                  Lifecycle
                </th>
              </tr>
            </thead>

            <tbody>
              {filteredIncidents.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-5 py-10 text-center text-sm text-[#64748B]"
                  >
                    No incidents found.
                  </td>
                </tr>
              ) : (
                filteredIncidents.map((incident) => {
                  const nextStatus = nextIncidentStatus(
                    incident.status,
                  );

                  return (
                    <tr
                      key={incident.id}
                      className="border-b border-[#202938]/80"
                    >
                      <td className="px-5 py-4">
                        <p className="text-xs font-medium text-[#F8FAFC]">
                          {incident.incident_number}
                        </p>
                        <p className="mt-1 max-w-[280px] truncate text-xs text-[#64748B]">
                          {incident.title}
                        </p>
                      </td>

                      <td className="px-5 py-4 text-xs text-[#CBD5E1]">
                        {incident.network_node_code
                          ?? incident.network_node_name
                          ?? "Not linked"}
                      </td>

                      <td className="px-5 py-4">
                        <span className="text-xs text-amber-400">
                          {incident.severity}
                        </span>
                      </td>

                      <td className="px-5 py-4 text-xs text-blue-400">
                        {incident.status}
                      </td>

                      <td className="px-5 py-4 text-xs text-[#F8FAFC]">
                        {incident.affected_services.length}
                      </td>

                      <td className="px-5 py-4 text-xs text-[#64748B]">
                        {formatDate(incident.started_at)}
                      </td>

                      <td className="px-5 py-4 text-right">
                        {nextStatus ? (
                          <button
                            type="button"
                            disabled={actionId === incident.id}
                            onClick={() =>
                              void advanceIncident(incident)
                            }
                            className="border border-[#334155] px-3 py-2 text-[11px] text-[#CBD5E1] transition hover:border-blue-500 hover:text-blue-400 disabled:opacity-50"
                          >
                            {actionId === incident.id
                              ? "Updating..."
                              : `Move to ${nextStatus}`}
                          </button>
                        ) : (
                          <span className="text-xs text-emerald-400">
                            RESOLVED
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="border border-[#202938] bg-[#0D1117]">
        <div className="border-b border-[#202938] px-5 py-4">
          <h2 className="text-sm font-semibold text-[#F8FAFC]">
            Complaint Operations
          </h2>

          <p className="mt-1 text-xs text-[#64748B]">
            Live customer support complaints from the current
            organization.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1050px] text-left">
            <thead>
              <tr className="border-b border-[#202938] text-[10px] uppercase tracking-[0.12em] text-[#64748B]">
                <th className="px-5 py-3">Ticket</th>
                <th className="px-5 py-3">Customer</th>
                <th className="px-5 py-3">Category</th>
                <th className="px-5 py-3">Priority</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Created</th>
                <th className="px-5 py-3 text-right">
                  Lifecycle
                </th>
              </tr>
            </thead>

            <tbody>
              {filteredComplaints.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-5 py-10 text-center text-sm text-[#64748B]"
                  >
                    No support complaints found.
                  </td>
                </tr>
              ) : (
                filteredComplaints.map((complaint) => {
                  const nextStatus = nextComplaintStatus(
                    complaint.status,
                  );

                  return (
                    <tr
                      key={complaint.id}
                      className="border-b border-[#202938]/80"
                    >
                      <td className="px-5 py-4">
                        <p className="text-xs font-medium text-[#F8FAFC]">
                          {complaint.complaint_number}
                        </p>

                        <p className="mt-1 max-w-[280px] truncate text-xs text-[#64748B]">
                          {complaint.subject}
                        </p>
                      </td>

                      <td className="px-5 py-4">
                        <p className="text-xs text-[#CBD5E1]">
                          {complaint.customer_name}
                        </p>

                        <p className="mt-1 text-[11px] text-[#64748B]">
                          {complaint.customer_number}
                        </p>
                      </td>

                      <td className="px-5 py-4 text-xs text-[#CBD5E1]">
                        {complaint.category}
                      </td>

                      <td className="px-5 py-4 text-xs text-amber-400">
                        {complaint.priority}
                      </td>

                      <td className="px-5 py-4 text-xs text-blue-400">
                        {complaint.status}
                      </td>

                      <td className="px-5 py-4 text-xs text-[#64748B]">
                        {formatDate(complaint.created_at)}
                      </td>

                      <td className="px-5 py-4 text-right">
                        {nextStatus ? (
                          <button
                            type="button"
                            disabled={
                              actionId === complaint.id
                            }
                            onClick={() =>
                              void advanceComplaint(complaint)
                            }
                            className="border border-[#334155] px-3 py-2 text-[11px] text-[#CBD5E1] transition hover:border-blue-500 hover:text-blue-400 disabled:opacity-50"
                          >
                            {actionId === complaint.id
                              ? "Updating..."
                              : `Move to ${nextStatus}`}
                          </button>
                        ) : (
                          <span className="text-xs text-emerald-400">
                            CLOSED
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      <div className="flex items-center gap-2 text-[11px] text-[#64748B]">
        <Clock3 className="h-3.5 w-3.5" />
        Metrics are calculated from current tenant support API
        records. No correlation confidence or network telemetry is
        inferred.
      </div>
    </div>
  );
}