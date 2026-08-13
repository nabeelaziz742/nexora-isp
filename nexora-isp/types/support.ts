export type TicketPriority =
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL";

export type TicketStatus =
  | "OPEN"
  | "INVESTIGATING"
  | "ASSIGNED"
  | "RESOLVED";

export type IncidentSeverity =
  | "MINOR"
  | "MAJOR"
  | "CRITICAL";

export type IncidentStatus =
  | "DETECTED"
  | "INVESTIGATING"
  | "MITIGATING"
  | "RESOLVED";

export type SupportMetricStatus =
  | "healthy"
  | "warning"
  | "critical"
  | "neutral";

export interface SupportMetric {
  id: string;
  label: string;
  value: string;
  description: string;
  trend?: string;
  status: SupportMetricStatus;
}

export interface SupportTicket {
  id: string;
  ticketCode: string;
  customerName: string;
  customerCode: string;
  subject: string;
  category: string;
  priority: TicketPriority;
  status: TicketStatus;
  connectedNode: string;
  incidentCode?: string;
  assignedTo?: string;
  createdAt: string;
}

export interface NetworkIncident {
  id: string;
  incidentCode: string;
  title: string;
  affectedNode: string;
  area: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  affectedCustomers: number;
  linkedTickets: number;
  detectedAt: string;
  lastUpdated: string;
}

export interface ComplaintCorrelation {
  id: string;
  title: string;
  description: string;
  nodeCode: string;
  complaintCount: number;
  affectedCustomers: number;
  confidence: number;
  timeWindow: string;
  suggestedIncidentCode: string;
}