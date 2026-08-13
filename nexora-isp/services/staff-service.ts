import { apiClient } from "@/services/api-client";

export type StaffRole =
  | "OWNER"
  | "STAFF"
  | "TECHNICIAN";

export type OrganizationStaff = {
  id: string;
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: StaffRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type CreateStaffPayload = {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  role: "STAFF" | "TECHNICIAN";
};

export const staffService = {
  getStaff(): Promise<OrganizationStaff[]> {
    return apiClient.get<OrganizationStaff[]>(
      "/tenant/staff/",
    );
  },

  createStaff(
    payload: CreateStaffPayload,
  ): Promise<OrganizationStaff> {
    return apiClient.post<OrganizationStaff>(
      "/tenant/staff/",
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
};