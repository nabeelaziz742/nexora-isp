import type { LucideIcon } from "lucide-react";

export type InventoryCategory =
  | "ONU_ONT"
  | "ROUTER"
  | "NETWORK_EQUIPMENT"
  | "FIBER_EQUIPMENT";

export type InventoryStockStatus =
  | "AVAILABLE"
  | "ASSIGNED"
  | "TECHNICIAN_CUSTODY"
  | "IN_REPAIR"
  | "FAULTY";

export type InventoryHealthTone =
  | "primary"
  | "healthy"
  | "warning"
  | "critical";

export interface InventoryMetric {
  id: string;
  label: string;
  value: string;
  description: string;
  icon: LucideIcon;
  tone: InventoryHealthTone;
}

export interface InventoryAsset {
  id: string;
  assetCode: string;
  deviceName: string;
  category: InventoryCategory;
  manufacturer: string;
  model: string;
  serialNumber: string;
  macAddress: string | null;
  stockStatus: InventoryStockStatus;
  warehouseLocation: string;
  assignedCustomer: string | null;
  customerCode: string | null;
  assignedTechnician: string | null;
  technicianCode: string | null;
  connectedNode: string | null;
  lastUpdated: string;
}

export interface InventoryStockItem {
  id: string;
  category: InventoryCategory;
  itemName: string;
  totalUnits: number;
  availableUnits: number;
  assignedUnits: number;
  technicianUnits: number;
  repairUnits: number;
  minimumStockLevel: number;
}

export interface InventoryIntelligenceItem {
  id: string;
  title: string;
  description: string;
  severity: "WARNING" | "CRITICAL" | "INFO";
  actionLabel: string;
}