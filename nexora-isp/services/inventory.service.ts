import { apiClient } from "@/services/api-client";

export type InventoryDeviceStatus =
  | "AVAILABLE"
  | "ASSIGNED"
  | "FAULTY"
  | "IN_REPAIR"
  | "RETIRED"
  | "SOLD";

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

export type ReturnCondition = "GOOD" | "DAMAGED" | "FAULTY";

export type InventoryItemCategory =
  | "CABLES_CONNECTORS"
  | "OPTICAL_SPLITTERS"
  | "ROUTERS_AP"
  | "ONU_ONT"
  | "POWER_ADAPTERS"
  | "ACCESSORIES"
  | "TOOLS_EQUIPMENT"
  | "OTHER";

export type InventoryItemUnit =
  | "PIECES"
  | "METERS"
  | "ROLLS"
  | "PACKS"
  | "BOXES";

export type InventoryItem = {
  id: string;
  name: string;
  code: string;
  category: InventoryItemCategory;
  unit_of_measure: InventoryItemUnit;
  unit_cost_price: string;
  unit_selling_price: string;
  quantity_on_hand: string;
  quantity_damaged: string;
  reorder_threshold: number;
  is_low_stock: boolean;
  is_serialized: boolean;
  is_active: boolean;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type StockMovement = {
  id: string;
  item: string;
  item_name: string;
  item_code: string;
  movement_type: string;
  quantity: string;
  previous_quantity: string;
  new_quantity: string;
  unit_cost: string;
  reference_type: string;
  reference_id: string;
  notes: string;
  created_by_name: string;
  created_at: string;
};

export type PaginatedResult<T> = {
  count: number;
  total_pages: number;
  current_page: number;
  results: T[];
};

export const inventoryService = {
  // Serialized Devices
  getDevices(): Promise<InventoryDevice[]> {
    return apiClient.get<InventoryDevice[]>("/inventory/devices/");
  },

  getAssignments(): Promise<DeviceAssignment[]> {
    return apiClient.get<DeviceAssignment[]>("/inventory/assignments/");
  },

  assignDevice(
    deviceId: string,
    serviceAccountId: string,
    assignmentNotes = "",
  ): Promise<DeviceAssignment> {
    return apiClient.post<DeviceAssignment>("/inventory/assignments/assign/", {
      device_id: deviceId,
      service_account_id: serviceAccountId,
      assignment_notes: assignmentNotes,
    });
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

  // Quantity-based Inventory Items
  getItems(params?: {
    category?: string;
    search?: string;
    low_stock?: boolean;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResult<InventoryItem>> {
    const query = new URLSearchParams();
    if (params?.category) query.set("category", params.category);
    if (params?.search) query.set("search", params.search);
    if (params?.low_stock) query.set("low_stock", "true");
    if (params?.is_active !== undefined) query.set("is_active", String(params.is_active));
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    return apiClient.get<PaginatedResult<InventoryItem>>(
      `/inventory/items/${qs ? `?${qs}` : ""}`,
    );
  },

  getItem(id: string): Promise<InventoryItem> {
    return apiClient.get<InventoryItem>(`/inventory/items/${id}/`);
  },

  createItem(payload: Partial<InventoryItem>): Promise<InventoryItem> {
    return apiClient.post<InventoryItem>("/inventory/items/", payload);
  },

  updateItem(id: string, payload: Partial<InventoryItem>): Promise<InventoryItem> {
    return apiClient.patch<InventoryItem>(`/inventory/items/${id}/`, payload);
  },

  restockItem(
    id: string,
    payload: { quantity: number | string; unit_cost?: number | string; notes?: string },
  ): Promise<InventoryItem> {
    return apiClient.post<InventoryItem>(`/inventory/items/${id}/restock/`, payload);
  },

  adjustItem(
    id: string,
    payload: { new_quantity: number | string; reason?: string; notes?: string },
  ): Promise<InventoryItem> {
    return apiClient.post<InventoryItem>(`/inventory/items/${id}/adjust/`, payload);
  },

  damageItem(
    id: string,
    payload: { quantity: number | string; notes?: string },
  ): Promise<InventoryItem> {
    return apiClient.post<InventoryItem>(`/inventory/items/${id}/damage/`, payload);
  },

  disposeItem(
    id: string,
    payload: { quantity: number | string; notes?: string },
  ): Promise<InventoryItem> {
    return apiClient.post<InventoryItem>(`/inventory/items/${id}/dispose/`, payload);
  },

  getMovements(params?: {
    item_id?: string;
    movement_type?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResult<StockMovement>> {
    const query = new URLSearchParams();
    if (params?.item_id) query.set("item_id", params.item_id);
    if (params?.movement_type) query.set("movement_type", params.movement_type);
    if (params?.search) query.set("search", params.search);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    return apiClient.get<PaginatedResult<StockMovement>>(
      `/inventory/movements/${qs ? `?${qs}` : ""}`,
    );
  },
};