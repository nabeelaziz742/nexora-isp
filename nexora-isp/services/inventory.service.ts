import { apiClient } from "@/services/api-client";

export type InventoryDeviceStatus =
  | "AVAILABLE"
  | "ASSIGNED"
  | "FAULTY"
  | "IN_REPAIR"
  | "RETIRED";

export type InventoryDevice = {
  id: string;
  asset_tag: string;
  device_type: string;
  manufacturer: string;
  model_name: string;
  serial_number: string;
  mac_address: string;
  status: InventoryDeviceStatus;
  notes: string;
  active_assignment_id: string | null;
  assigned_service_number: string | null;
  assigned_customer_number: string | null;
  assigned_customer_name: string | null;
  created_at: string;
  updated_at: string;
};

export type DeviceAssignment = {
  id: string;
  device: string;
  asset_tag: string;
  device_type: string;
  device_status: InventoryDeviceStatus;
  service_account: string;
  service_number: string;
  customer_id: string;
  customer_number: string;
  customer_name: string;
  assigned_by_email: string | null;
  returned_by_email: string | null;
  assigned_at: string;
  returned_at: string | null;
  return_condition: string;
  assignment_notes: string;
  return_notes: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ReturnCondition =
  | "GOOD"
  | "DAMAGED"
  | "FAULTY";

export const inventoryService = {
  getDevices(): Promise<InventoryDevice[]> {
    return apiClient.get<InventoryDevice[]>(
      "/inventory/devices/",
    );
  },

  getAssignments(): Promise<DeviceAssignment[]> {
    return apiClient.get<DeviceAssignment[]>(
      "/inventory/assignments/",
    );
  },

  assignDevice(
    deviceId: string,
    serviceAccountId: string,
    assignmentNotes = "",
  ): Promise<DeviceAssignment> {
    return apiClient.post<DeviceAssignment>(
      "/inventory/assignments/assign/",
      {
        device_id: deviceId,
        service_account_id: serviceAccountId,
        assignment_notes: assignmentNotes,
      },
    );
  },

  returnDevice(
    assignmentId: string,
    returnCondition: ReturnCondition,
    returnNotes = "",
  ): Promise<DeviceAssignment> {
    return apiClient.post<DeviceAssignment>(
      `/inventory/assignments/${assignmentId}/return/`,
      {
        return_condition: returnCondition,
        return_notes: returnNotes,
      },
    );
  },
};