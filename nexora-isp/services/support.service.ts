import { apiClient } from "@/services/api-client";

export type ComplaintStatus =
  | "OPEN"
  | "NEW"
  | "ACKNOWLEDGED"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "WAITING_CUSTOMER"
  | "WAITING_PARTS"
  | "ESCALATED"
  | "RESOLVED"
  | "CUSTOMER_CONFIRMED"
  | "CLOSED"
  | "CANCELLED";

export type ComplaintPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ComplaintCategory =
  | "CONNECTIVITY"
  | "SPEED"
  | "BILLING"
  | "DEVICE"
  | "INSTALLATION"
  | "ROUTER_ISSUE"
  | "ONU_ISSUE"
  | "FIBER_CABLE_DAMAGE"
  | "POWER_ISSUE"
  | "PAYMENT_RELATED"
  | "CONFIGURATION"
  | "OTHER";

export type ComplaintSource =
  | "CUSTOMER_PORTAL"
  | "PHONE"
  | "WHATSAPP"
  | "SMS"
  | "WALK_IN"
  | "STAFF"
  | "SYSTEM"
  | "OTHER";

export type SLAStatus = "ON_TRACK" | "DUE_SOON" | "BREACHED" | "RESOLVED";

export type CustomerConfirmation = "PENDING" | "CONFIRMED" | "REJECTED";

export type ComplaintTimelineEvent = {
  id: string;
  event_type: string;
  actor_email: string | null;
  actor_name: string;
  previous_value: string;
  new_value: string;
  summary: string;
  notes: string;
  metadata: Record<string, any>;
  created_at: string;
};

export type ComplaintInternalNote = {
  id: string;
  author_email: string | null;
  author_name: string;
  note: string;
  is_internal: boolean;
  created_at: string;
};

export type Complaint = {
  id: string;
  complaint_number: string;
  customer_id: string;
  customer_number: string;
  customer_name: string;
  customer_phone: string;
  customer_address: string;
  service_account_id: string | null;
  service_number: string | null;
  category: ComplaintCategory;
  priority: ComplaintPriority;
  source: ComplaintSource;
  status: ComplaintStatus;
  subject: string;
  description: string;
  assigned_to_id: string | null;
  assigned_to_email: string | null;
  assigned_to_name: string | null;
  assigned_by_email: string | null;
  assigned_at: string | null;
  reassignment_reason: string;
  first_response_at: string | null;
  response_due_at: string | null;
  resolution_due_at: string | null;
  is_response_sla_breached: boolean;
  is_resolution_sla_breached: boolean;
  sla_status: SLAStatus;
  is_escalated: boolean;
  escalation_level: number;
  escalation_reason: string;
  escalated_by_email: string | null;
  escalated_at: string | null;
  escalated_to_email: string | null;
  diagnosis_category: string;
  resolution_summary: string;
  resolution_notes: string;
  resolved_by_email: string | null;
  resolved_at: string | null;
  customer_confirmation: CustomerConfirmation;
  customer_confirmed_at: string | null;
  customer_feedback_rating: number | null;
  customer_feedback_notes: string;
  closed_at: string | null;
  linked_incident_id: string | null;
  linked_incident_number: string | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
  timeline_events?: ComplaintTimelineEvent[];
  internal_notes?: ComplaintInternalNote[];
  work_orders_count?: number;
};

export type TechnicianWorkload = {
  technician_id: string;
  technician_name: string;
  email: string;
  role: string;
  open_tickets: number;
};

export type SupportDashboardMetrics = {
  total_complaints: number;
  open_complaints: number;
  critical_complaints: number;
  unassigned_complaints: number;
  in_progress_complaints: number;
  waiting_complaints: number;
  escalated_complaints: number;
  resolved_complaints: number;
  closed_complaints: number;
  sla_breached_complaints: number;
  avg_resolution_hours: number;
  category_breakdown: Array<{ category: string; count: number }>;
  priority_breakdown: Array<{ priority: string; count: number }>;
  technician_workloads: TechnicianWorkload[];
};

export type ComplaintSLAPolicy = {
  id?: string;
  priority: ComplaintPriority;
  response_target_minutes: number;
  resolution_target_hours: number;
  escalation_threshold_hours: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
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

export type IncidentStatus =
  | "OPEN"
  | "INVESTIGATING"
  | "IDENTIFIED"
  | "MONITORING"
  | "RESOLVED";

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

export interface ComplaintQueryParams {
  status?: string;
  priority?: string;
  category?: string;
  source?: string;
  sla_status?: string;
  assigned_to_id?: string;
  customer_id?: string;
  service_account_id?: string;
  is_unassigned?: boolean;
  search?: string;
}

export interface CreateComplaintPayload {
  customer_id: string;
  service_account_id?: string | null;
  category: ComplaintCategory;
  priority: ComplaintPriority;
  source?: ComplaintSource;
  subject: string;
  description: string;
  assigned_to_id?: string | null;
  linked_incident_id?: string | null;
}

export const supportService = {
  getComplaints(params?: ComplaintQueryParams): Promise<Complaint[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.status) searchParams.append("status", params.status);
      if (params.priority) searchParams.append("priority", params.priority);
      if (params.category) searchParams.append("category", params.category);
      if (params.source) searchParams.append("source", params.source);
      if (params.sla_status) searchParams.append("sla_status", params.sla_status);
      if (params.assigned_to_id) searchParams.append("assigned_to_id", params.assigned_to_id);
      if (params.customer_id) searchParams.append("customer_id", params.customer_id);
      if (params.service_account_id) searchParams.append("service_account_id", params.service_account_id);
      if (params.is_unassigned !== undefined) searchParams.append("is_unassigned", String(params.is_unassigned));
      if (params.search) searchParams.append("search", params.search);
    }
    const query = searchParams.toString();
    return apiClient.get<Complaint[]>(`/support/complaints/${query ? `?${query}` : ""}`);
  },

  getComplaintDetail(complaintId: string): Promise<Complaint> {
    return apiClient.get<Complaint>(`/support/complaints/${complaintId}/`);
  },

  createComplaint(payload: CreateComplaintPayload): Promise<Complaint> {
    return apiClient.post<Complaint>("/support/complaints/", payload);
  },

  assignComplaint(complaintId: string, technicianId: string, notes = ""): Promise<Complaint> {
    return apiClient.post<Complaint>(`/support/complaints/${complaintId}/assign/`, {
      technician_id: technicianId,
      notes,
    });
  },

  reassignComplaint(complaintId: string, technicianId: string, reason: string, notes = ""): Promise<Complaint> {
    return apiClient.post<Complaint>(`/support/complaints/${complaintId}/reassign/`, {
      technician_id: technicianId,
      reason,
      notes,
    });
  },

  transitionComplaint(complaintId: string, targetStatus: ComplaintStatus, notes = "", resolutionNotes = ""): Promise<Complaint> {
    return apiClient.post<Complaint>(`/support/complaints/${complaintId}/transition/`, {
      target_status: targetStatus,
      notes,
      resolution_notes: resolutionNotes,
    });
  },

  escalateComplaint(complaintId: string, reason: string, escalatedToId?: string | null): Promise<Complaint> {
    return apiClient.post<Complaint>(`/support/complaints/${complaintId}/escalate/`, {
      reason,
      escalated_to_id: escalatedToId || null,
    });
  },

  addInternalNote(complaintId: string, note: string): Promise<ComplaintInternalNote> {
    return apiClient.post<ComplaintInternalNote>(`/support/complaints/${complaintId}/notes/`, {
      note,
    });
  },

  getInternalNotes(complaintId: string): Promise<ComplaintInternalNote[]> {
    return apiClient.get<ComplaintInternalNote[]>(`/support/complaints/${complaintId}/notes/`);
  },

  resolveComplaint(complaintId: string, diagnosisCategory: string, resolutionSummary: string, resolutionNotes = ""): Promise<Complaint> {
    return apiClient.post<Complaint>(`/support/complaints/${complaintId}/resolve/`, {
      diagnosis_category: diagnosisCategory,
      resolution_summary: resolutionSummary,
      resolution_notes: resolutionNotes,
    });
  },

  closeComplaint(complaintId: string, confirmation: CustomerConfirmation, feedbackRating?: number | null, feedbackNotes = ""): Promise<Complaint> {
    return apiClient.post<Complaint>(`/support/complaints/${complaintId}/close/`, {
      confirmation,
      feedback_rating: feedbackRating || null,
      feedback_notes: feedbackNotes,
    });
  },

  getTimeline(complaintId: string): Promise<ComplaintTimelineEvent[]> {
    return apiClient.get<ComplaintTimelineEvent[]>(`/support/complaints/${complaintId}/timeline/`);
  },

  getDashboardMetrics(): Promise<SupportDashboardMetrics> {
    return apiClient.get<SupportDashboardMetrics>("/support/dashboard/metrics/");
  },

  getSLAPolicies(): Promise<ComplaintSLAPolicy[]> {
    return apiClient.get<ComplaintSLAPolicy[]>("/support/sla-policies/");
  },

  updateSLAPolicies(policies: Partial<ComplaintSLAPolicy>[]): Promise<ComplaintSLAPolicy[]> {
    return apiClient.put<ComplaintSLAPolicy[]>("/support/sla-policies/", { policies });
  },

  getIncidents(params?: any): Promise<Incident[]> {
    return apiClient.get<Incident[]>("/support/incidents/");
  },

  getIncidentDetail(incidentId: string): Promise<Incident> {
    return apiClient.get<Incident>(`/support/incidents/${incidentId}/`);
  },

  createIncident(payload: any): Promise<Incident> {
    return apiClient.post<Incident>("/support/incidents/", payload);
  },

  transitionIncident(incidentId: string, targetStatus: IncidentStatus, rootCause = "", resolutionNotes = ""): Promise<Incident> {
    return apiClient.post<Incident>(`/support/incidents/${incidentId}/status-transitions/`, {
      target_status: targetStatus,
      root_cause: rootCause,
      resolution_notes: resolutionNotes,
    });
  },
};