export interface CommandCenterSummary {
  total_customers: number;
  active_services: number;
  outstanding_amount: number;
  active_incidents: number;
  open_complaints: number;
  open_work_orders: number;
  pending_provisioning_requests: number;
  failed_notifications: number;
  operational_health_score: number;
}

export interface CommandCenterAlert {
  id: string;
  title: string;
  severity: string;
  created_at: string;
}

export type PriorityQueueRecord = Record<
  string,
  unknown
>;

export interface PriorityQueuesResponse {
  pending_provisioning: PriorityQueueRecord[];
  critical_complaints: PriorityQueueRecord[];
  critical_incidents: PriorityQueueRecord[];
  critical_work_orders: PriorityQueueRecord[];
  failed_notifications: PriorityQueueRecord[];
  inventory_attention: PriorityQueueRecord[];
}

export interface RecentActivityItem {
  id: string;
  title: string;
  description: string;
  created_at: string;
}

export type MetricTone =
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "intelligence";

export interface CommandMetric {
  id?: string;
  label: string;
  value: string | number;
  change?: string;
  tone: MetricTone;
  helper?: string;
}

export type DailyBriefingSeverity =
  | "warning"
  | "critical"
  | "intelligence"
  | "info";

export interface DailyBriefingItem {
  id: string;
  title: string;
  description: string;
  severity: DailyBriefingSeverity;
}

export type IncidentStatus =
  | "Identified"
  | "Investigating";

export type IncidentSeverity = "Major";

export interface ActiveIncident {
  id: string;
  node: string;
  title: string;
  impactedCustomers: number;
  relatedComplaints: number;
  status: IncidentStatus;
  severity: IncidentSeverity;
}