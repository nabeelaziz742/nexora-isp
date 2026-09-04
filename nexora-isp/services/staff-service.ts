import { apiClient } from "@/services/api-client";

export type BaseStaffRole = "OWNER" | "STAFF" | "TECHNICIAN";

export type OperationalRole =
  | "OWNER"
  | "ADMIN"
  | "MANAGER"
  | "ACCOUNTANT"
  | "OPERATOR"
  | "RECOVERY_OFFICER"
  | "TECHNICIAN"
  | "SUPPORT_OFFICER"
  | "FIELD_OFFICER"
  | "STAFF";

export type StaffStatus = "ACTIVE" | "INACTIVE" | "SUSPENDED" | "TERMINATED";

export interface OrganizationStaff {
  id: string;
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: BaseStaffRole;
  operational_role: OperationalRole;
  staff_code: string;
  status: StaffStatus;
  phone: string;
  alternate_phone: string;
  cnic: string;
  department: string;
  designation: string;
  assigned_area_id: string | null;
  assigned_area_name: string | null;
  joining_date: string | null;
  notes: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateStaffPayload {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  role?: OperationalRole;
  phone?: string;
  alternate_phone?: string;
  cnic?: string;
  department?: string;
  designation?: string;
  assigned_area_id?: string | null;
  supervisor_id?: string | null;
  joining_date?: string | null;
  notes?: string;
}

export interface UpdateStaffPayload {
  first_name?: string;
  last_name?: string;
  role?: OperationalRole;
  phone?: string;
  alternate_phone?: string;
  cnic?: string;
  department?: string;
  designation?: string;
  assigned_area_id?: string | null;
  supervisor_id?: string | null;
  joining_date?: string | null;
  notes?: string;
}

export interface OperatorWorkload {
  total_assigned: number;
  pending_count: number;
  contacted_count: number;
  promises_count: number;
  payments_collected_count: number;
  completed_count: number;
  outstanding_assigned_amount: string;
}

export interface OperatorListItem {
  membership_id: string;
  user_id: string;
  staff_code: string;
  full_name: string;
  email: string;
  phone: string;
  role: OperationalRole;
  department: string;
  designation: string;
  assigned_area_id: string | null;
  assigned_area_name: string | null;
  status: StaffStatus;
  workload: OperatorWorkload;
}

export interface OperatorActiveAllocation {
  id: string;
  allocation_number: string;
  customer_id: string;
  customer_name: string;
  customer_number: string;
  phone: string;
  outstanding_amount: string;
  priority: "LOW" | "NORMAL" | "HIGH" | "CRITICAL";
  status: string;
  assigned_date: string;
  due_date: string | null;
}

export interface OperatorWorkloadDetail {
  membership_id: string;
  user_id: string;
  staff_code: string;
  full_name: string;
  email: string;
  phone: string;
  role: OperationalRole;
  assigned_area_name: string | null;
  workload: OperatorWorkload;
  active_allocations: OperatorActiveAllocation[];
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

export const staffService = {
  getStaff(params?: {
    role?: string;
    status?: string;
    department?: string;
    area_id?: string;
    search?: string;
  }): Promise<OrganizationStaff[]> {
    return apiClient.get<OrganizationStaff[]>(
      `/tenant/staff/${buildQuery(params)}`,
    );
  },

  getStaffMember(membershipId: string): Promise<OrganizationStaff> {
    return apiClient.get<OrganizationStaff>(`/tenant/staff/${membershipId}/`);
  },

  createStaff(payload: CreateStaffPayload): Promise<OrganizationStaff> {
    return apiClient.post<OrganizationStaff>("/tenant/staff/", payload);
  },

  updateStaff(
    membershipId: string,
    payload: UpdateStaffPayload,
  ): Promise<OrganizationStaff> {
    return apiClient.patch<OrganizationStaff>(
      `/tenant/staff/${membershipId}/`,
      payload,
    );
  },

  setActiveState(
    membershipId: string,
    isActive: boolean,
  ): Promise<OrganizationStaff> {
    return apiClient.patch<OrganizationStaff>(
      `/tenant/staff/${membershipId}/active-state/`,
      {
        is_active: isActive,
      },
    );
  },

  setStatus(
    membershipId: string,
    status: StaffStatus,
  ): Promise<OrganizationStaff> {
    return apiClient.patch<OrganizationStaff>(
      `/tenant/staff/${membershipId}/status/`,
      {
        status,
      },
    );
  },

  getOperators(params?: {
    area_id?: string;
    search?: string;
  }): Promise<OperatorListItem[]> {
    return apiClient.get<OperatorListItem[]>(
      `/tenant/operators/${buildQuery(params)}`,
    );
  },

  getOperatorWorkload(userId: string): Promise<OperatorWorkloadDetail> {
    return apiClient.get<OperatorWorkloadDetail>(
      `/tenant/operators/${userId}/workload/`,
    );
  },
};