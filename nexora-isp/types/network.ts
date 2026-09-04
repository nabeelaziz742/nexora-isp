export type NetworkMetricStatus =
  | "healthy"
  | "warning"
  | "critical"
  | "neutral";

export interface NetworkMetric {
  id: string;
  label: string;
  value: string;
  description: string;
  trend?: string;
  status: NetworkMetricStatus;
}

export type PopType =
  | "CORE"
  | "AGGREGATION"
  | "DISTRIBUTION"
  | "TOWER"
  | "CABINET"
  | "CENTRAL_OFFICE"
  | "OTHER";

export type PopStatus =
  | "ACTIVE"
  | "MAINTENANCE"
  | "DEGRADED"
  | "OFFLINE";

export interface PointOfPresence {
  id: string;
  code: string;
  name: string;
  pop_type: PopType;
  area: string | null;
  area_name?: string;
  area_city?: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  rack_capacity_units: number;
  power_backup_type: string;
  status: PopStatus;
  supervisor: string | null;
  supervisor_name?: string | null;
  notes: string;
  is_active: boolean;
  nodes_count: number;
  active_subscribers_count: number;
  created_at: string;
  updated_at: string;
  nodes?: NetworkNode[];
}

export interface NetworkNode {
  id: string;
  name: string;
  code: string;
  node_type: string;
  pop_site?: string | null;
  pop_site_name?: string | null;
  pop_site_code?: string | null;
  management_ip: string | null;
  location: string;
  is_active: boolean;
  assignment_count: number;
  created_at: string;
  updated_at: string;
}

export interface NetworkAssignment {
  id: string;
  service_account: string;
  service_number: string;
  service_status: string;
  customer_id: string;
  customer_number: string;
  customer_name: string;
  network_node: string;
  network_node_name: string;
  network_node_code: string;
  username: string;
  ip_address: string | null;
  is_active: boolean;
  assigned_at: string;
  updated_at: string;
}

export type ProvisioningAction =
  | "ACTIVATE"
  | "SUSPEND"
  | "RESTORE"
  | "CHANGE_PACKAGE";

export type ProvisioningStatus =
  | "PENDING"
  | "PROCESSING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED";

export interface ProvisioningRequest {
  id: string;
  service_account: string;
  service_number: string;
  customer_number: string;
  customer_name: string;
  network_assignment: string;
  network_node_id: string;
  network_node_name: string;
  network_node_code: string;
  action: ProvisioningAction;
  status: ProvisioningStatus;
  idempotency_key: string;
  requested_payload: Record<string, unknown>;
  provider_reference: string;
  error_message: string;
  requested_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
}

// Legacy network mock compatibility types.
// Real backend NetworkNode, NetworkAssignment, and
// ProvisioningRequest types above remain unchanged.

export type LegacyNetworkNodeStatus =
  | "HEALTHY"
  | "DEGRADED"
  | "OFFLINE";

export interface LegacyNetworkNode {
  id: string;
  nodeCode: string;
  name: string;
  area: string;
  status: LegacyNetworkNodeStatus;
  ipAddress: string;
  connectedCustomers: number;
  capacity: number;
  utilization: number;
  latency: number | null;
  uptime: string;
  lastChecked: string;
}

export type NetworkTopologyNodeType =
  | "INTERNET"
  | "CORE_ROUTER"
  | "DISTRIBUTION_NODE";

export interface NetworkTopologyNode {
  id: string;
  label: string;
  subtitle: string;
  type: NetworkTopologyNodeType;
  status: LegacyNetworkNodeStatus;
  utilization: number;
  connectedCustomers?: number;
}

export type NetworkEventSeverity =
  | "CRITICAL"
  | "WARNING"
  | "INFO";

export type NetworkEventStatus =
  | "INVESTIGATING"
  | "ACTIVE"
  | "RESOLVED";

export interface NetworkEvent {
  id: string;
  eventCode: string;
  title: string;
  description: string;
  nodeName: string;
  severity: NetworkEventSeverity;
  status: NetworkEventStatus;
  affectedCustomers: number;
  detectedAt: string;
}