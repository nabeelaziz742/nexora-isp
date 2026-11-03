export type InvoiceStatus =
  | "UNPAID"
  | "PARTIALLY_PAID"
  | "PAID"
  | "CANCELLED"
  | "WRITTEN_OFF";

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
  collection_rate?: string;
  invoice_count: number;
  unpaid_count: number;
  partially_paid_count: number;
  paid_count: number;
  overdue_count: number;
  cancelled_count?: number;
  written_off_count: number;
  total_written_off: string;
  total_bad_debt_recovered: string;
  total_advance: string;
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
  cancelled_at?: string | null;
  cancellation_reason?: string;
  total_amount: string;
  paid_amount: string;
  outstanding_amount: string;
  written_off_amount: string;
  bad_debt_recovered_amount: string;
  written_off_at: string | null;
  write_off_reason: string;
  created_at: string;
  updated_at: string;
}

export interface BadDebtRecoveryPayload {
  amount: string;
  payment_method: PaymentMethod;
  reference?: string;
  notes?: string;
}

export type BillingCycle = "MONTHLY" | "PREPAID";

export interface ServiceRechargePayload {
  months: number;
  payment_method: PaymentMethod;
  reference?: string;
  notes?: string;
}

export interface ServiceRechargeResult {
  service_account_id: string;
  service_number: string;
  service_status: string;
  invoice_id: string;
  invoice_number: string;
  payment_id: string | null;
  payment_number: string | null;
  months: number;
  amount: string;
  previous_expiry_date: string | null;
  new_expiry_date: string;
  restored: boolean;
}

export interface BillingModePayload {
  billing_cycle: BillingCycle;
  expiry_date?: string | null;
}

export interface ExpiringService {
  service_account_id: string;
  service_number: string;
  customer_id: string;
  customer_name: string;
  customer_phone: string;
  package_name: string;
  monthly_price: string;
  status: string;
  expiry_date: string;
  days_left: number;
}

export interface ExpiringServicesResponse {
  days: number;
  count: number;
  results: ExpiringService[];
}

export interface InvoiceLine {
  id: string;
  description: string;
  quantity?: number;
  unit_price?: string | null;
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
  is_reversed: boolean;
  reversed_at?: string | null;
  reversal_reason?: string;
  reversal_reference?: string;
  received_by_email: string | null;
  paid_at: string;
  created_at: string;
  updated_at: string;
  allocations?: PaymentAllocation[];
}

export interface RecordInvoicePaymentPayload {
  amount: string;
  payment_method: PaymentMethod;
  reference?: string;
  notes?: string;
  paid_at?: string | null;
}

export interface PaymentAllocationInput {
  invoice_id: string;
  amount: string;
}

export interface RecordPaymentWithAllocationsPayload {
  service_account_id: string;
  amount: string;
  payment_method: PaymentMethod;
  reference?: string;
  notes?: string;
  allocations?: PaymentAllocationInput[];
  paid_at?: string | null;
}

export interface PaymentReversalPayload {
  reversal_reason: string;
  reversal_reference?: string;
}

export interface CustomInvoiceLineItem {
  description: string;
  amount: string;
  quantity?: number;
  unit_price?: string;
}

export interface CustomInvoicePayload {
  service_account_id: string;
  billing_period_start: string;
  billing_period_end: string;
  issue_date: string;
  due_date: string;
  line_items: CustomInvoiceLineItem[];
  notes?: string;
}

export interface MonthlyBillingRunPayload {
  billing_year: number;
  billing_month: number;
}

export interface MonthlyBillingRunResult {
  billing_year: number;
  billing_month: number;
  eligible_services: number;
  generated_invoices: number;
  skipped_existing_invoices: number;
  failed_services: number;
}

export interface FinancialLedgerEntry {
  type: "INVOICE" | "PAYMENT" | "PAYMENT_REVERSED" | "WRITE_OFF";
  date: string;
  timestamp: string;
  reference: string;
  description: string;
  debit: string;
  credit: string;
  balance: string;
  status: string;
  service_number: string;
  customer_name: string;
  customer_id: string;
  service_account_id: string;
  object_id: string;
}

export interface FinancialLedger {
  currency: string;
  total_debit: string;
  total_credit: string;
  closing_balance: string;
  // Credit the customer has paid ahead; applied to the next invoice automatically.
  advance_balance: string;
  entries: FinancialLedgerEntry[];
}

export interface PaymentReceiptAllocation {
  invoice_number: string;
  billing_period: string;
  invoice_total: string;
  allocated_amount: string;
  invoice_remaining: string;
  invoice_status: string;
}

export interface PaymentReceipt {
  organization_name: string;
  organization_code: string;
  currency: string;
  payment_number: string;
  payment_id: string;
  payment_date: string;
  payment_method: PaymentMethod;
  reference: string;
  amount: string;
  is_reversed: boolean;
  reversed_at: string | null;
  reversal_reason: string;
  notes: string;
  received_by_name: string;
  customer: {
    id: string;
    customer_number: string;
    full_name: string;
    phone: string;
    address: string;
    city: string;
    area: string;
  };
  service_number: string;
  allocations: PaymentReceiptAllocation[];
  customer_remaining_balance: string;
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