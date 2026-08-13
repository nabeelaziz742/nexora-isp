import { apiClient } from "@/services/api-client";

export type ComplaintStatus =
  | "OPEN"
  | "IN_PROGRESS"
  | "RESOLVED"
  | "CLOSED";

export type IncidentStatus =
  | "OPEN"
  | "INVESTIGATING"
  | "IDENTIFIED"
  | "MONITORING"
  | "RESOLVED";

export type Complaint = {
  id: string;
  complaint_number: string;
  customer_id: string;
  customer_number: string;
  customer_name: string;
  service_account_id: string | null;
  service_number: string | null;
  category: string;
  priority: string;
  status: ComplaintStatus;
  subject: string;
  description: string;
  resolution_notes: string;
  created_by_email: string | null;
  resolved_by_email: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
};

export type AffectedService = {
  service_account_id: string;
  service_number: string;
  service_status: string;
  customer_id: string;
  customer_number: string;
  customer_name: string;
  added_at: string;
};

export type Incident = {
  id: string;
  incident_number: string;
  network_node_id: string | null;
  network_node_name: string | null;
  network_node_code: string | null;
  title: string;
  description: string;
  severity: string;
  status: IncidentStatus;
  root_cause: string;
  resolution_notes: string;
  created_by_email: string | null;
  resolved_by_email: string | null;
  started_at: string;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
  affected_services: AffectedService[];
};

export const supportService = {
  getComplaints(): Promise<Complaint[]> {
    return apiClient.get<Complaint[]>(
      "/support/complaints/",
    );
  },

  getIncidents(): Promise<Incident[]> {
    return apiClient.get<Incident[]>(
      "/support/incidents/",
    );
  },

  transitionComplaint(
    complaintId: string,
    targetStatus: ComplaintStatus,
    resolutionNotes = "",
  ): Promise<Complaint> {
    return apiClient.post<Complaint>(
      `/support/complaints/${complaintId}/status-transitions/`,
      {
        target_status: targetStatus,
        resolution_notes: resolutionNotes,
      },
    );
  },

  transitionIncident(
    incidentId: string,
    targetStatus: IncidentStatus,
    rootCause = "",
    resolutionNotes = "",
  ): Promise<Incident> {
    return apiClient.post<Incident>(
      `/support/incidents/${incidentId}/status-transitions/`,
      {
        target_status: targetStatus,
        root_cause: rootCause,
        resolution_notes: resolutionNotes,
      },
    );
  },
};