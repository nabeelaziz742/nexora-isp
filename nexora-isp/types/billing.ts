export type InvoiceStatus =
  | "UNPAID"
  | "PARTIALLY_PAID"
  | "PAID";

export type PaymentMethod =
  | "CASH"
  | "BANK_TRANSFER"
  | "CARD"
  | "MOBILE_WALLET"
  | "OTHER";

export type InvoiceDueState =
  | ""
  | "OVERDUE"
  | "DUE"
  | "PAID";

export interface BillingSummary {
  currency: string;
  total_invoiced: string;
  total_paid: string;
  total_outstanding: string;
  overdue_outstanding: string;
  invoice_count: number;
  unpaid_count: number;
  partially_paid_count: number;
  paid_count: number;
  overdue_count: number;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  service_account: string;
  service_number: string;
  customer_id: string;
  customer_number: string;
  customer_name: string;
  package_name: string;
  billing_period_start: string;
  billing_period_end: string;
  issue_date: string;
  due_date: string;
  status: InvoiceStatus;
  total_amount: string;
  paid_amount: string;
  outstanding_amount: string;
  created_at: string;
  updated_at: string;
}

export interface InvoiceLine {
  id: string;
  description: string;
  amount: string;
  created_at: string;
}

export interface PaymentAllocation {
  id: string;
  payment: string;
  payment_number: string;
  payment_method: PaymentMethod;
  payment_reference: string;
  amount: string;
  paid_at: string;
  created_at: string;
}

export interface InvoiceDetail extends Invoice {
  lines: InvoiceLine[];
  allocations: PaymentAllocation[];
}

export interface Payment {
  id: string;
  payment_number: string;
  service_account: string;
  service_number: string;
  customer_id: string;
  customer_number: string;
  customer_name: string;
  amount: string;
  allocated_amount: string;
  unallocated_amount: string;
  payment_method: PaymentMethod;
  reference: string;
  notes: string;
  received_by_email: string | null;
  paid_at: string;
  created_at: string;
  updated_at: string;
}

export interface RecordInvoicePaymentPayload {
  amount: string;
  payment_method: PaymentMethod;
  reference?: string;
  notes?: string;
  paid_at?: string | null;
}

export interface InvoiceFilters {
  status?: InvoiceStatus | "";
  search?: string;
  billing_period?: string;
  due_state?: InvoiceDueState;
  service_account_id?: string;
  customer_id?: string;
}

export interface PaymentFilters {
  search?: string;
  payment_method?: PaymentMethod | "";
  service_account_id?: string;
  customer_id?: string;
}

// Legacy billing UI compatibility types.
// These remain available for existing components that are
// not currently rendered by the real billing operations page.

export type BillingMetricStatus =
  | "healthy"
  | "warning"
  | "critical"
  | "neutral";

export type BillStatus =
  | "PAID"
  | "UNPAID"
  | "GRACE_PERIOD"
  | "SUSPENSION_PENDING"
  | "OVERDUE";

export type PaymentStatus =
  | "VERIFIED"
  | "PENDING_VERIFICATION"
  | "FAILED";

export type BillingServiceStatus =
  | "ACTIVE"
  | "GRACE_PERIOD"
  | "SUSPENSION_PENDING"
  | "SUSPENDED_NON_PAYMENT"
  | "RESTORE_PENDING";

export interface BillingMetric {
  id: string;
  label: string;
  value: string;
  description: string;
  trend?: string;
  status: BillingMetricStatus;
}

export interface BillingAutomationSettings {
  gracePeriodDays: number;
  autoSuspensionEnabled: boolean;
  finalWarningHoursBeforeSuspension: number;
  autoRestoreAfterPaymentEnabled: boolean;
  billNotificationEnabled: boolean;
  paymentReminderEnabled: boolean;
}

export interface BillingLifecycleSummary {
  status: BillingServiceStatus;
  label: string;
  customerCount: number;
  description: string;
}

export interface CustomerBill {
  id: string;
  billCode: string;
  customerName: string;
  customerCode: string;
  packageName: string;
  billingMonth: string;
  amount: number;
  dueDate: string;
  billStatus: BillStatus;
  serviceStatus: BillingServiceStatus;
  paymentStatus?: PaymentStatus;
  connectedNode: string;
  lastAction: string;
}

export interface PaymentActivity {
  id: string;
  paymentCode: string;
  customerName: string;
  customerCode: string;
  amount: number;
  method: string;
  status: PaymentStatus;
  receivedAt: string;
}