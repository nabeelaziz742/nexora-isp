export type FieldJobPriority =
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL";

export type FieldJobStatus =
  | "UNASSIGNED"
  | "ASSIGNED"
  | "EN_ROUTE"
  | "ON_SITE"
  | "COMPLETED";

export type TechnicianStatus =
  | "AVAILABLE"
  | "EN_ROUTE"
  | "ON_SITE"
  | "OFF_DUTY";

export type FieldMetricStatus =
  | "healthy"
  | "warning"
  | "critical"
  | "neutral";

export interface FieldMetric {
  id: string;
  label: string;
  value: string;
  description: string;
  trend?: string;
  status: FieldMetricStatus;
}

export interface FieldJob {
  id: string;
  jobCode: string;
  title: string;
  customerName: string;
  customerCode: string;
  area: string;
  priority: FieldJobPriority;
  status: FieldJobStatus;
  technicianName?: string;
  ticketCode: string;
  incidentCode?: string;
  connectedNode: string;
  scheduledWindow: string;
  slaRemaining: string;
  slaAtRisk: boolean;
}

export interface Technician {
  id: string;
  technicianCode: string;
  name: string;
  status: TechnicianStatus;
  currentArea: string;
  activeJobs: number;
  completedToday: number;
  averageResolutionTime: string;
  currentJobCode?: string;
}

export interface DispatchJob {
  id: string;
  jobCode: string;
  title: string;
  area: string;
  priority: FieldJobPriority;
  ticketCode: string;
  connectedNode: string;
  waitingTime: string;
  suggestedTechnician?: string;
  incidentCode?: string;
}