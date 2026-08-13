export type CustomerServiceStatus =
  | "ACTIVE"
  | "GRACE_PERIOD"
  | "SUSPENSION_PENDING"
  | "SUSPENDED_NON_PAYMENT"
  | "RESTORE_PENDING";

export interface Customer {
  id: string;
  customerCode: string;
  name: string;
  phone: string;
  area: string;
  packageName: string;
  monthlyBill: number;
  serviceStatus: CustomerServiceStatus;
  pppoeUsername: string;
  connectedNode: string;
  ipAddress: string;
}