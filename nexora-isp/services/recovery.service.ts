import { apiClient } from "@/services/api-client";

export type AllocationPriority = "LOW" | "NORMAL" | "HIGH" | "CRITICAL";

export type AllocationStatus =
  | "ALLOCATED"
  | "IN_PROGRESS"
  | "CONTACTED"
  | "PROMISE_RECEIVED"
  | "PAYMENT_COLLECTED"
  | "NO_RESPONSE"
  | "FAILED"
  | "ESCALATED"
  | "COMPLETED"
  | "CANCELLED";

export interface DefaulterInvoiceItem {
  id: string;
  invoice_number: string;
  due_date: string;
  total_amount: string;
  paid_amount: string;
  balance: string;
  days_overdue: number;
}

export interface DefaulterActiveAllocation {
  id: string;
  allocation_number: string;
  assigned_staff_id: string;
  assigned_staff_name: string;
  status: AllocationStatus;
  priority: AllocationPriority;
  due_date: string | null;
}

export interface DefaulterActivePromise {
  id: string;
  promise_number: string;
  promised_amount: string;
  deadline: string;
  status: string;
}

export interface DefaulterItem {
  customer_id: string;
  customer_number: string;
  full_name: string;
  phone: string;
  city: string;
  area: string;
  service_account_id: string;
  internet_id: string;
  total_overdue: string | number;
  overdue_invoices_count: number;
  oldest_due_date: string;
  max_days_overdue: number;
  aging_bucket: "0-30" | "31-60" | "61-90" | "90+";
  invoices: DefaulterInvoiceItem[];
  active_allocation: DefaulterActiveAllocation | null;
  active_promise: DefaulterActivePromise | null;
}

export interface RecoveryAllocationItem {
  id: string;
  allocation_number: string;
  customer: string;
  customer_name: string;
  customer_number: string;
  customer_phone: string;
  customer_city: string;
  customer_area: string;
  service_account: string | null;
  internet_id: string | null;
  invoice: string | null;
  invoice_number: string | null;
  outstanding_amount: string;
  assigned_staff: string;
  assigned_staff_name: string;
  assigned_staff_email: string;
  assigned_by: string | null;
  assigned_by_name: string | null;
  assigned_date: string;
  due_date: string | null;
  priority: AllocationPriority;
  status: AllocationStatus;
  notes: string;
  reassigned_from: string | null;
  reassigned_from_number: string | null;
  reassignment_reason: string;
  linked_promise: string | null;
  linked_promise_number: string | null;
  completed_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateAllocationPayload {
  customer_id: string;
  service_account_id?: string | null;
  invoice_id?: string | null;
  assigned_staff_id: string;
  outstanding_amount?: number | string | null;
  due_date?: string | null;
  priority?: AllocationPriority;
  notes?: string;
}

export interface ReassignAllocationPayload {
  new_assigned_staff_id: string;
  reassignment_reason: string;
  due_date?: string | null;
  priority?: AllocationPriority;
  notes?: string;
}

export interface StatusTransitionPayload {
  new_status: AllocationStatus;
  notes?: string;
  linked_promise_id?: string | null;
}

export interface RecoveryDashboardMetrics {
  total_assigned: number;
  active_count: number;
  today_followups: number;
  promises_count: number;
  completed_count: number;
  total_outstanding_assigned: string | number;
  total_defaulters_in_system: number;
}

function buildQuery(params?: Record<string, string | undefined>) {
  if (!params) return "";
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== "") {
      query.append(key, val);
    }
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export const recoveryService = {
  getDefaulters(params?: {
    search?: string;
    city?: string;
    area?: string;
    aging_bucket?: string;
    min_amount?: string;
    has_active_allocation?: string;
  }): Promise<DefaulterItem[]> {
    return apiClient.get<DefaulterItem[]>(
      `/billing/defaulters/${buildQuery(params)}`,
    );
  },

  getAllocations(params?: {
    status?: string;
    operator_id?: string;
    customer_id?: string;
    priority?: string;
    area?: string;
    search?: string;
  }): Promise<RecoveryAllocationItem[]> {
    return apiClient.get<RecoveryAllocationItem[]>(
      `/billing/allocations/${buildQuery(params)}`,
    );
  },

  getAllocation(allocationId: string): Promise<RecoveryAllocationItem> {
    return apiClient.get<RecoveryAllocationItem>(
      `/billing/allocations/${allocationId}/`,
    );
  },

  createAllocation(
    payload: CreateAllocationPayload,
  ): Promise<RecoveryAllocationItem> {
    return apiClient.post<RecoveryAllocationItem>(
      "/billing/allocations/",
      payload,
    );
  },

  reassignAllocation(
    allocationId: string,
    payload: ReassignAllocationPayload,
  ): Promise<RecoveryAllocationItem> {
    return apiClient.post<RecoveryAllocationItem>(
      `/billing/allocations/${allocationId}/reassign/`,
      payload,
    );
  },

  transitionStatus(
    allocationId: string,
    payload: StatusTransitionPayload,
  ): Promise<RecoveryAllocationItem> {
    return apiClient.post<RecoveryAllocationItem>(
      `/billing/allocations/${allocationId}/status-transitions/`,
      payload,
    );
  },

  getDashboardMetrics(): Promise<RecoveryDashboardMetrics> {
    return apiClient.get<RecoveryDashboardMetrics>(
      "/billing/recovery-dashboard/",
    );
  },
};
