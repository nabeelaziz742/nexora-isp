import { apiClient } from "@/services/api-client";

export type WorkOrderStatus =
  | "CREATED"
  | "ASSIGNED"
  | "DISPATCHED"
  | "ONSITE"
  | "COMPLETED";

export type WorkOrderPriority =
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL";

export type WorkOrderType =
  | "INSTALLATION"
  | "REPAIR"
  | "DEVICE_REPLACEMENT"
  | "NETWORK_MAINTENANCE"
  | "SITE_VISIT"
  | "OTHER";

export type WorkOrder = {
  id: string;
  work_order_number: string;
  work_type: WorkOrderType;
  priority: WorkOrderPriority;
  status: WorkOrderStatus;
  title: string;
  customer_number: string | null;
  customer_name: string | null;
  service_number: string | null;
  network_node_name: string | null;
  network_node_code: string | null;
  complaint_number: string | null;
  incident_number: string | null;
  assigned_technician_email: string | null;
  assigned_technician_name: string | null;
  assigned_at: string | null;
  dispatched_at: string | null;
  onsite_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkOrderDetail = WorkOrder & {
  description: string;
  customer_id: string | null;
  service_account_id: string | null;
  service_status: string | null;
  network_node_id: string | null;
  complaint_id: string | null;
  incident_id: string | null;
  assigned_technician_id: string | null;
  created_by_email: string | null;
  dispatch_notes: string;
  onsite_notes: string;
  completion_notes: string;
};

export type Technician = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
};

export type SupportComplaint = {
  id: string;
  complaint_number: string;
  customer_id: string;
  customer_number: string;
  customer_name: string;
  service_account_id: string | null;
  service_number: string | null;
  category: string;
  priority: string;
  status: string;
  subject: string;
  description: string;
};

export type SupportIncident = {
  id: string;
  incident_number: string;
  network_node_id: string | null;
  network_node_name: string | null;
  network_node_code: string | null;
  title: string;
  description: string;
  severity: string;
  status: string;
};

export type CurrentSession = {
  user: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
  };
  organization: {
    id: string;
    name: string;
    code: string;
  };
  role: "OWNER" | "STAFF" | "TECHNICIAN";
};

export type CreateWorkOrderInput = {
  customer_id?: string | null;
  service_account_id?: string | null;
  network_node_id?: string | null;
  complaint_id?: string | null;
  incident_id?: string | null;
  work_type: WorkOrderType;
  priority: WorkOrderPriority;
  title: string;
  description: string;
};

export const fieldOperationsService = {
  getSession(): Promise<CurrentSession> {
    return apiClient.get<CurrentSession>(
      "/auth/me/",
    );
  },

  getWorkOrders(): Promise<WorkOrder[]> {
    return apiClient.get<WorkOrder[]>(
      "/field-operations/work-orders/",
    );
  },

  getTechnicians(): Promise<Technician[]> {
    return apiClient.get<Technician[]>(
      "/tenant/technicians/",
    );
  },

  getComplaints(): Promise<SupportComplaint[]> {
    return apiClient.get<SupportComplaint[]>(
      "/support/complaints/",
    );
  },

  getIncidents(): Promise<SupportIncident[]> {
    return apiClient.get<SupportIncident[]>(
      "/support/incidents/",
    );
  },

  createWorkOrder(
    input: CreateWorkOrderInput,
  ): Promise<WorkOrderDetail> {
    return apiClient.post<WorkOrderDetail>(
      "/field-operations/work-orders/",
      input,
    );
  },

  assignTechnician(
    workOrderId: string,
    technicianId: string,
  ): Promise<WorkOrderDetail> {
    return apiClient.post<WorkOrderDetail>(
      `/field-operations/work-orders/${workOrderId}/assignments/`,
      {
        technician_id: technicianId,
      },
    );
  },

  async createAndAssignWorkOrder(
    input: CreateWorkOrderInput,
    technicianId: string,
  ): Promise<WorkOrderDetail> {
    const workOrder = await this.createWorkOrder(input);

    return this.assignTechnician(
      workOrder.id,
      technicianId,
    );
  },

  dispatchWorkOrder(
    workOrderId: string,
    dispatchNotes: string,
  ): Promise<WorkOrderDetail> {
    return apiClient.post<WorkOrderDetail>(
      `/field-operations/work-orders/${workOrderId}/dispatches/`,
      {
        dispatch_notes: dispatchNotes,
      },
    );
  },

  markOnsite(
    workOrderId: string,
    onsiteNotes: string,
  ): Promise<WorkOrderDetail> {
    return apiClient.post<WorkOrderDetail>(
      `/field-operations/work-orders/${workOrderId}/onsite-transitions/`,
      {
        onsite_notes: onsiteNotes,
      },
    );
  },

  completeWorkOrder(
    workOrderId: string,
    completionNotes: string,
  ): Promise<WorkOrderDetail> {
    return apiClient.post<WorkOrderDetail>(
      `/field-operations/work-orders/${workOrderId}/completions/`,
      {
        completion_notes: completionNotes,
      },
    );
  },
};