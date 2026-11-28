import { apiBlob, apiRequest } from "@/services/api-client";
import type { ImportBatch, ImportPreview } from "@/services/customer-import.service";
import type { CommissionType, DealerPayout } from "@/services/dealers.service";
import type { JumpSessionResponse } from "@/services/jump-session";

export type DealerPaymentMethod = "CASH" | "MOBILE_WALLET" | "BANK_TRANSFER";

export interface DealerRights {
  // Customer
  can_view_all_customers: boolean;
  can_view_customers: boolean;
  can_request_customers: boolean;
  can_import_customers: boolean;
  can_export_customers: boolean;
  can_edit_customers: boolean;
  can_deactivate_customers: boolean;
  can_recharge: boolean;
  // Collection
  can_collect_payments: boolean;
  can_view_collections: boolean;
  can_view_ledger: boolean;
  // System
  can_manage_complaints: boolean;
  can_web_login: boolean;
  can_mobile_login: boolean;
  can_view_packages: boolean;
  can_manage_sms_templates: boolean;
  can_view_sms_log: boolean;
  can_view_areas: boolean;
  can_manage_areas: boolean;
  // Admin
  can_manage_employees: boolean;
  can_view_dashboard: boolean;
  can_change_payment_date: boolean;
  can_reverse_payments: boolean;
  can_view_all_collections: boolean;
  can_edit_company_info: boolean;
  // Messaging
  can_send_sms: boolean;
  can_broadcast_sms: boolean;
  can_cancel_sms: boolean;
  // Accounts
  can_view_accounts: boolean;
  can_view_journal: boolean;
  can_add_journal_entries: boolean;
  can_void_journal_entries: boolean;
}

export interface DealerRightItem {
  key: keyof DealerRights;
  label: string;
}

export interface DealerRightGroup {
  key: string;
  label: string;
  rights: DealerRightItem[];
}

export const DEALER_RIGHT_GROUPS: DealerRightGroup[] = [
  {
    key: "customer",
    label: "Customer",
    rights: [
      { key: "can_view_all_customers", label: "All customers" },
      { key: "can_view_customers", label: "Customer list" },
      { key: "can_request_customers", label: "Add customer" },
      { key: "can_import_customers", label: "Import customers" },
      { key: "can_export_customers", label: "PDF / Excel export" },
      { key: "can_edit_customers", label: "Edit customer" },
      { key: "can_deactivate_customers", label: "Deactivate customer" },
      { key: "can_recharge", label: "Renew bill" },
    ],
  },
  {
    key: "collection",
    label: "Collection",
    rights: [
      { key: "can_collect_payments", label: "Collect fee" },
      { key: "can_view_collections", label: "Collection view" },
      { key: "can_view_ledger", label: "Customer ledger" },
    ],
  },
  {
    key: "system",
    label: "System",
    rights: [
      { key: "can_manage_complaints", label: "Complaint" },
      { key: "can_web_login", label: "Web login" },
      { key: "can_mobile_login", label: "Mobile login" },
      { key: "can_view_packages", label: "Packages" },
      { key: "can_manage_sms_templates", label: "SMS templates" },
      { key: "can_view_sms_log", label: "View SMS log" },
      { key: "can_view_areas", label: "Areas" },
      { key: "can_manage_areas", label: "Add / update areas" },
    ],
  },
  {
    key: "admin",
    label: "Admin",
    rights: [
      { key: "can_manage_employees", label: "Add / edit employees" },
      { key: "can_view_dashboard", label: "Dashboard" },
      { key: "can_change_payment_date", label: "Change payment date" },
      { key: "can_reverse_payments", label: "Reverse fee" },
      { key: "can_view_all_collections", label: "All collections" },
      { key: "can_edit_company_info", label: "Company info" },
    ],
  },
  {
    key: "messaging",
    label: "Messaging",
    rights: [
      { key: "can_send_sms", label: "Send SMS" },
      { key: "can_broadcast_sms", label: "Broadcast SMS" },
      { key: "can_cancel_sms", label: "Cancel pending SMS" },
    ],
  },
  {
    key: "accounts",
    label: "Accounts",
    rights: [
      { key: "can_view_accounts", label: "Accounts" },
      { key: "can_view_journal", label: "Journal view" },
      { key: "can_add_journal_entries", label: "Journal add" },
      { key: "can_void_journal_entries", label: "Void journal entry" },
    ],
  },
];

export const ALL_DEALER_RIGHTS: DealerRights = {
  can_view_all_customers: true,
  can_view_customers: true,
  can_request_customers: true,
  can_import_customers: true,
  can_export_customers: true,
  can_edit_customers: true,
  can_deactivate_customers: true,
  can_recharge: true,
  can_collect_payments: true,
  can_view_collections: true,
  can_view_ledger: true,
  can_manage_complaints: true,
  can_web_login: true,
  can_mobile_login: true,
  can_view_packages: true,
  can_manage_sms_templates: true,
  can_view_sms_log: true,
  can_view_areas: true,
  can_manage_areas: true,
  can_manage_employees: true,
  can_view_dashboard: true,
  can_change_payment_date: true,
  can_reverse_payments: true,
  can_view_all_collections: true,
  can_edit_company_info: true,
  can_send_sms: true,
  can_broadcast_sms: true,
  can_cancel_sms: true,
  can_view_accounts: true,
  can_view_journal: true,
  can_add_journal_entries: true,
  can_void_journal_entries: true,
};

export const DEFAULT_EMPLOYEE_RIGHTS: DealerRights = {
  can_view_all_customers: false,
  can_view_customers: true,
  can_request_customers: false,
  can_import_customers: false,
  can_export_customers: false,
  can_edit_customers: false,
  can_deactivate_customers: false,
  can_recharge: false,
  can_collect_payments: true,
  can_view_collections: false,
  can_view_ledger: false,
  can_manage_complaints: false,
  can_web_login: true,
  can_mobile_login: false,
  can_view_packages: false,
  can_manage_sms_templates: false,
  can_view_sms_log: false,
  can_view_areas: false,
  can_manage_areas: false,
  can_manage_employees: false,
  can_view_dashboard: true,
  can_change_payment_date: false,
  can_reverse_payments: false,
  can_view_all_collections: false,
  can_edit_company_info: false,
  can_send_sms: false,
  can_broadcast_sms: false,
  can_cancel_sms: false,
  can_view_accounts: false,
  can_view_journal: false,
  can_add_journal_entries: false,
  can_void_journal_entries: false,
};

export interface DealerCashHandover {
  id: string;
  amount: string;
  received_by_type: "DEALER" | "ISP";
  received_by: string;
  notes: string;
  created_at: string;
}

export interface DealerMe {
  is_dealer: boolean;
  employee_id?: string | null;
  name: string;
  impersonated_by?: string | null;
  impersonated_by_name?: string | null;
  jump_kind?: string | null;
  rights: DealerRights;
  right_groups?: DealerRightGroup[];
  // Employees only: cash collected and not yet handed over.
  cash_in_hand?: string;
  last_cash_handover?: DealerCashHandover | null;
}

export interface EmployeeCashRow {
  employee_id: string;
  name: string;
  phone: string;
  is_active: boolean;
  cash_in_hand: string;
  last_handover: DealerCashHandover | null;
}

export interface EmployeeCashTeam {
  total_cash_in_hand: string;
  results: EmployeeCashRow[];
}

export type ExpenseCategory = "BIKE" | "FOOD" | "OTHER";
export type ExpenseStatus = "PENDING" | "APPROVED" | "REJECTED";

export interface DealerExpense {
  id: string;
  dealer_name: string;
  dealer_code: string;
  employee_id: string;
  employee_name: string;
  category: ExpenseCategory;
  category_label: string;
  amount: string;
  spent_on: string;
  description: string;
  status: ExpenseStatus;
  reviewed_by: string;
  reviewed_at: string | null;
  review_note: string;
  created_at: string;
}

export interface DealerExpensePayload {
  category: ExpenseCategory;
  amount: string;
  spent_on: string;
  description?: string;
}

export interface CashReceivedResult {
  handover: DealerCashHandover;
  employee: EmployeeCashRow;
}

// Money and commission fields are left out for employees who may not see them.
export interface DealerSummary {
  me: DealerMe;
  dealer: {
    name: string;
    company_name: string;
    dealer_code: string;
    commission_type?: CommissionType;
    commission_rate?: string;
  };
  organization_name: string;
  month: string;
  show_dashboard?: boolean;
  total_customers?: number;
  active_connections?: number;
  suspended_connections?: number;
  expiring_in_3_days?: number;
  total_outstanding?: string;
  collected_this_month?: string;
  collected_by_me_this_month?: string;
  commission_this_month?: string;
  payout?: DealerPayout;
  parent_dealer_name?: string | null;
}

export interface DealerCustomerRow {
  service_id: string;
  customer_id: string;
  service_number: string;
  customer_number: string;
  customer_name: string;
  first_name: string;
  last_name: string;
  phone: string;
  alternate_phone: string;
  cnic: string;
  address_line: string;
  city: string;
  area: string;
  package_name: string;
  monthly_price: string;
  status: string;
  customer_is_active: boolean;
  billing_mode: "MONTHLY" | "PREPAID";
  expiry_date: string | null;
  days_to_expiry: number | null;
  outstanding: string;
  oldest_due_date: string | null;
  assigned_employee_id: string | null;
  assigned_employee_name: string;
}

export interface DealerCustomerEditPayload {
  first_name: string;
  last_name?: string;
  phone: string;
  alternate_phone?: string;
  cnic?: string;
  address_line: string;
  area?: string;
}

export interface DealerCustomerLedgerEntry {
  id: string;
  date: string;
  type: "INVOICE" | "PAYMENT";
  reference: string;
  service_number: string;
  description: string;
  debit: string;
  credit: string;
  is_reversed: boolean;
  running_balance: string;
}

export interface DealerCustomerLedger {
  customer: {
    id: string;
    customer_number: string;
    full_name: string;
    phone: string;
  };
  current_balance: string;
  entries: DealerCustomerLedgerEntry[];
}

export interface DealerAssignOption {
  id: string;
  full_name: string;
  email: string;
}

export interface DealerReceipt {
  payment_id: string;
  payment_number: string;
  amount: string;
  payment_method: string;
  paid_at: string | null;
}

export interface DealerCollectionRow {
  payment_id: string;
  payment_number: string;
  paid_at: string | null;
  customer_name: string;
  service_number: string;
  amount: string;
  payment_method: string;
  reference: string;
  is_reversed: boolean;
  reversal_reason?: string;
  reversed_at?: string | null;
  can_reverse?: boolean;
  collected_by_me: boolean;
  collected_by: string;
}

export interface DealerCollections {
  month: string;
  total_collected: string;
  collected_by_me: string;
  can_view_all_collections?: boolean;
  commission?: string;
  by_person: { name: string; total: string }[];
  results: DealerCollectionRow[];
}

export interface DealerEmployee {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone: string;
  is_active: boolean;
  rights: DealerRights;
  created_at: string;
}

export interface DealerEmployeePayload {
  first_name: string;
  last_name?: string;
  phone?: string;
  email: string;
  password: string;
  rights: Partial<DealerRights>;
}

export interface DealerPortalAccess {
  has_login: boolean;
  is_enabled: boolean;
  email: string;
  // Masked phone the password was sent to (after a send).
  sent_to?: string;
}

export interface DealerRequestRow {
  id: string;
  inquiry_number: string;
  full_name: string;
  phone: string;
  area: string;
  package_name: string;
  status: string;
  status_label: string;
  created_at: string;
}

export interface DealerRequestPayload {
  full_name: string;
  phone: string;
  alternate_phone?: string;
  cnic?: string;
  address_line: string;
  city: string;
  area?: string;
  preferred_package?: string | null;
  notes?: string;
}

export interface DealerArea {
  id: string;
  name: string;
  city: string;
  notes: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DealerAreaPayload {
  name: string;
  city?: string;
  notes?: string;
  is_active?: boolean;
}

export interface DealerComplaintRow {
  id: string;
  complaint_number: string;
  customer_id: string;
  customer_name: string;
  customer_phone: string;
  service_id: string | null;
  service_number: string;
  category: string;
  category_label: string;
  priority: string;
  priority_label: string;
  status: string;
  status_label: string;
  source: string;
  subject: string;
  description: string;
  resolution_summary: string;
  created_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface DealerComplaintCustomerOption {
  customer_id: string;
  service_id: string;
  customer_name: string;
  service_number: string;
  phone: string;
}

export interface DealerComplaintCreatePayload {
  customer_id: string;
  service_account_id?: string | null;
  category: string;
  priority: string;
  subject: string;
  description: string;
}

export interface DealerAccountsOverview {
  month: string;
  is_sub_dealer: boolean;
  parent_dealer_name: string | null;
  commission_note: string;
  collected_this_month: string;
  commission_earned: string;
  payout: DealerPayout | null;
  payouts_received_this_month: string;
  payouts_received_total: string;
  employee_cash_in_hand_total: string;
  employee_cash_breakdown: { employee_id: string; name: string; cash_in_hand: string }[];
  approved_expenses_this_month: string;
  pending_expenses_count: number;
  manual_income_this_month: string;
  manual_expense_this_month: string;
  net_cash_flow_this_month: string;
  recent_settlements: {
    id: string;
    settlement_number: string;
    settlement_date: string;
    period_start: string;
    period_end: string;
    amount: string;
    notes: string;
  }[];
}

export interface DealerJournalRow {
  id: string;
  date: string;
  source: string;
  source_label: string;
  kind: "INCOME" | "EXPENSE";
  amount: string;
  description: string;
  recorded_by: string;
  is_manual: boolean;
  is_void: boolean;
  void_reason: string;
  voided_at: string | null;
  can_void: boolean;
}

export interface DealerJournalResponse {
  period: string;
  from: string;
  to: string;
  total_income: string;
  total_expense: string;
  net: string;
  results: DealerJournalRow[];
}

export interface DealerSmsTemplate {
  id: string;
  name: string;
  body: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DealerSmsLogRow {
  id: string;
  customer_id: string;
  customer_name: string;
  recipient: string;
  template_name: string;
  message: string;
  status: string;
  can_cancel: boolean;
  error_message: string;
  created_at: string;
  sent_at: string | null;
}

export interface DealerSmsOptionsResponse {
  gateway_connected: boolean;
  banner: string;
  templates: DealerSmsTemplate[];
  customers: DealerComplaintCustomerOption[];
}

export interface DealerCompanyInfo {
  dealer_code: string;
  name: string;
  company_name: string;
  phone: string;
  alternate_phone: string;
  email: string;
  address_line: string;
  city: string;
  area: string;
  status: string;
  can_edit: boolean;
}

export interface DealerAboutInfo {
  organization: {
    name: string;
    phone: string;
    email: string;
    address: string;
    city: string;
  };
  dealer_code: string;
  powered_by: string;
}

export interface DealerPackage {
  id: string;
  name: string;
  code: string;
  download_speed_mbps: number;
  upload_speed_mbps: number;
  monthly_price: string;
  description: string;
}

export const dealerPortalService = {
  getRequests() {
    return apiRequest<{
      results: DealerRequestRow[];
      packages: { id: string; name: string; monthly_price: string }[];
      areas?: { id: string; name: string; city: string }[];
      default_city: string;
    }>("/dealer-portal/requests/");
  },

  getAreas(status: "" | "active" | "inactive" = "") {
    return apiRequest<{ results: DealerArea[] }>(
      `/dealer-portal/areas/${status ? `?status=${status}` : ""}`,
    );
  },

  createArea(payload: DealerAreaPayload) {
    return apiRequest<DealerArea>("/dealer-portal/areas/", { method: "POST", body: payload });
  },

  updateArea(areaId: string, payload: Partial<DealerAreaPayload>) {
    return apiRequest<DealerArea>(`/dealer-portal/areas/${areaId}/`, { method: "PATCH", body: payload });
  },

  toggleAreaStatus(areaId: string) {
    return apiRequest<DealerArea>(`/dealer-portal/areas/${areaId}/status/`, { method: "POST" });
  },

  getPackages() {
    return apiRequest<{ results: DealerPackage[] }>("/dealer-portal/packages/");
  },

  createRequest(payload: DealerRequestPayload) {
    return apiRequest<DealerRequestRow>("/dealer-portal/requests/", { method: "POST", body: payload });
  },

  getSummary() {
    return apiRequest<DealerSummary>("/dealer-portal/summary/");
  },

  getCustomers(params: { search?: string; show?: "" | "due" | "expiring" } = {}) {
    const query = new URLSearchParams();
    if (params.search) query.set("search", params.search);
    if (params.show) query.set("show", params.show);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return apiRequest<{ count: number; results: DealerCustomerRow[] }>(`/dealer-portal/customers/${suffix}`);
  },

  getAssignOptions() {
    return apiRequest<{ employees: DealerAssignOption[] }>("/dealer-portal/customers/assign-options/");
  },

  assignCustomers(customerIds: string[], employeeId: string | null) {
    return apiRequest<{ assigned_count: number; employee_id: string | null }>("/dealer-portal/customers/assign/", {
      method: "POST",
      body: { customer_ids: customerIds, employee_id: employeeId },
    });
  },

  getCustomerEditOptions(customerId: string) {
    return apiRequest<{
      customer: DealerCustomerEditPayload & { id: string; customer_number: string };
      areas: { id: string; name: string; city: string }[];
    }>(`/dealer-portal/customers/${customerId}/`);
  },

  updateCustomer(customerId: string, payload: Partial<DealerCustomerEditPayload>) {
    return apiRequest<{ customer: DealerCustomerEditPayload & { id: string }; services: DealerCustomerRow[] }>(
      `/dealer-portal/customers/${customerId}/`,
      { method: "PATCH", body: payload },
    );
  },

  deactivateCustomer(customerId: string, reason: string) {
    return apiRequest<{ detail: string; services: DealerCustomerRow[] }>(
      `/dealer-portal/customers/${customerId}/deactivate/`,
      { method: "POST", body: { reason } },
    );
  },

  getCustomerLedger(customerId: string) {
    return apiRequest<DealerCustomerLedger>(`/dealer-portal/customers/${customerId}/ledger/`);
  },

  exportCustomers(format: "xlsx" | "pdf", params: { search?: string; show?: "" | "due" | "expiring" } = {}) {
    const query = new URLSearchParams({ file_format: format });
    if (params.search) query.set("search", params.search);
    if (params.show) query.set("show", params.show);
    return apiBlob(`/dealer-portal/customers/export/?${query.toString()}`);
  },

  downloadImportTemplate(): Promise<Blob> {
    return apiBlob("/dealer-portal/import/template/");
  },

  previewImport(file: File): Promise<ImportPreview> {
    const form = new FormData();
    form.append("file", file);
    return apiRequest<ImportPreview>("/dealer-portal/import/preview/", {
      method: "POST",
      body: form,
      timeoutMs: 120_000,
    });
  },

  runImport(file: File): Promise<ImportBatch> {
    const form = new FormData();
    form.append("file", file);
    return apiRequest<ImportBatch>("/dealer-portal/import/", {
      method: "POST",
      body: form,
      timeoutMs: 300_000,
    });
  },

  getImportHistory(): Promise<ImportBatch[]> {
    return apiRequest<ImportBatch[]>("/dealer-portal/import/history/");
  },

  collectPayment(
    serviceId: string,
    payload: { amount: string; payment_method: DealerPaymentMethod; reference?: string; notes?: string; paid_at?: string },
  ) {
    return apiRequest<{ receipt: DealerReceipt; service: DealerCustomerRow }>(
      `/dealer-portal/services/${serviceId}/payments/`,
      { method: "POST", body: payload },
    );
  },

  recharge(
    serviceId: string,
    payload: { months: number; payment_method: DealerPaymentMethod; reference?: string; paid_at?: string },
  ) {
    return apiRequest<{ receipt: DealerReceipt | null; amount: string; new_expiry_date: string; service: DealerCustomerRow }>(
      `/dealer-portal/services/${serviceId}/recharge/`,
      { method: "POST", body: payload },
    );
  },

  reversePayment(paymentId: string, payload: { reason: string; reference?: string }) {
    return apiRequest<DealerReceipt & { is_reversed: boolean; reversal_reason: string; reversed_at: string | null }>(
      `/dealer-portal/payments/${paymentId}/reverse/`,
      { method: "POST", body: payload },
    );
  },

  getCollections(month?: string) {
    return apiRequest<DealerCollections>(`/dealer-portal/collections/${month ? `?month=${month}` : ""}`);
  },

  // The dealer's own employees (dealer or employee with can_manage_employees).
  getEmployees() {
    return apiRequest<{ results: DealerEmployee[]; max_employees: number; right_groups?: DealerRightGroup[] }>(
      "/dealer-portal/employees/",
    );
  },

  createEmployee(payload: DealerEmployeePayload) {
    return apiRequest<DealerEmployee>("/dealer-portal/employees/", { method: "POST", body: payload });
  },

  updateEmployee(
    id: string,
    payload: Partial<Pick<DealerEmployee, "first_name" | "last_name" | "phone" | "is_active">> & {
      rights?: Partial<DealerRights>;
    },
  ) {
    return apiRequest<DealerEmployee>(`/dealer-portal/employees/${id}/`, { method: "PATCH", body: payload });
  },

  resetEmployeePassword(id: string, password: string) {
    return apiRequest<{ detail: string }>(`/dealer-portal/employees/${id}/password/`, {
      method: "POST",
      body: { password },
    });
  },

  // Dealer: every employee's cash in hand. (An employee gets their own instead.)
  getTeamCash() {
    return apiRequest<EmployeeCashTeam>("/dealer-portal/cash/");
  },

  getMyCash() {
    return apiRequest<{ cash_in_hand: string; history: DealerCashHandover[] }>("/dealer-portal/cash/");
  },

  receiveEmployeeCash(employeeId: string, notes = "") {
    return apiRequest<CashReceivedResult>(`/dealer-portal/employees/${employeeId}/cash-received/`, {
      method: "POST",
      body: { notes },
    });
  },

  // Employee: own expense requests. Dealer: every employee's (read only).
  getExpenses() {
    return apiRequest<{ results: DealerExpense[] }>("/dealer-portal/expenses/");
  },

  requestExpense(payload: DealerExpensePayload) {
    return apiRequest<DealerExpense>("/dealer-portal/expenses/", { method: "POST", body: payload });
  },

  getComplaints(statusFilter = "") {
    const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
    return apiRequest<{
      results: DealerComplaintRow[];
      customers: DealerComplaintCustomerOption[];
      categories: { value: string; label: string }[];
      priorities: { value: string; label: string }[];
    }>(`/dealer-portal/complaints/${query}`);
  },

  createComplaint(payload: DealerComplaintCreatePayload) {
    return apiRequest<DealerComplaintRow>("/dealer-portal/complaints/", { method: "POST", body: payload });
  },

  getAccounts(month?: string) {
    return apiRequest<DealerAccountsOverview>(`/dealer-portal/accounts/${month ? `?month=${month}` : ""}`);
  },

  getJournal(params: { month?: string; from?: string; to?: string; kind?: "" | "INCOME" | "EXPENSE" } = {}) {
    const query = new URLSearchParams();
    if (params.month) query.set("month", params.month);
    if (params.from) query.set("from", params.from);
    if (params.to) query.set("to", params.to);
    if (params.kind) query.set("kind", params.kind);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return apiRequest<DealerJournalResponse>(`/dealer-portal/journal/${suffix}`);
  },

  addJournalEntry(payload: { date: string; kind: "INCOME" | "EXPENSE"; amount: string; description: string }) {
    return apiRequest<DealerJournalRow>("/dealer-portal/journal/", { method: "POST", body: payload });
  },

  voidJournalEntry(entryId: string, reason: string) {
    return apiRequest<{ id: string; is_void: boolean; void_reason: string; voided_at: string }>(
      `/dealer-portal/journal/${entryId}/void/`,
      { method: "POST", body: { reason } },
    );
  },

  exportJournal(params: { month?: string; from?: string; to?: string; kind?: "" | "INCOME" | "EXPENSE" } = {}) {
    const query = new URLSearchParams();
    if (params.month) query.set("month", params.month);
    if (params.from) query.set("from", params.from);
    if (params.to) query.set("to", params.to);
    if (params.kind) query.set("kind", params.kind);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return apiBlob(`/dealer-portal/journal/export/${suffix}`);
  },

  getSmsTemplates() {
    return apiRequest<{ results: DealerSmsTemplate[] }>("/dealer-portal/sms-templates/");
  },

  createSmsTemplate(payload: { name: string; body: string; is_active?: boolean }) {
    return apiRequest<DealerSmsTemplate>("/dealer-portal/sms-templates/", { method: "POST", body: payload });
  },

  updateSmsTemplate(templateId: string, payload: Partial<{ name: string; body: string; is_active: boolean }>) {
    return apiRequest<DealerSmsTemplate>(`/dealer-portal/sms-templates/${templateId}/`, {
      method: "PATCH",
      body: payload,
    });
  },

  deactivateSmsTemplate(templateId: string) {
    return apiRequest<DealerSmsTemplate>(`/dealer-portal/sms-templates/${templateId}/`, { method: "DELETE" });
  },

  getSmsOptions() {
    return apiRequest<DealerSmsOptionsResponse>("/dealer-portal/sms/options/");
  },

  sendSms(payload: { customer_id: string; template_id?: string | null; message?: string }) {
    return apiRequest<{ queued: number; gateway_connected: boolean; banner: string; entry: DealerSmsLogRow }>(
      "/dealer-portal/sms/send/",
      { method: "POST", body: payload },
    );
  },

  broadcastSms(payload: { audience: "ALL" | "DUE" | "EXPIRING"; template_id?: string | null; message?: string }) {
    return apiRequest<{ queued: number; audience: string; gateway_connected: boolean; banner: string }>(
      "/dealer-portal/sms/broadcast/",
      { method: "POST", body: payload },
    );
  },

  getSmsLog(statusFilter = "") {
    const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
    return apiRequest<{ gateway_connected: boolean; banner: string; results: DealerSmsLogRow[] }>(
      `/dealer-portal/sms-log/${query}`,
    );
  },

  cancelSms(queueId: string) {
    return apiRequest<DealerSmsLogRow>(`/dealer-portal/sms-log/${queueId}/cancel/`, { method: "POST", body: {} });
  },

  getCompanyInfo() {
    return apiRequest<DealerCompanyInfo>("/dealer-portal/company-info/");
  },

  updateCompanyInfo(
    payload: Partial<
      Pick<DealerCompanyInfo, "company_name" | "phone" | "alternate_phone" | "email" | "address_line" | "city" | "area">
    >,
  ) {
    return apiRequest<DealerCompanyInfo>("/dealer-portal/company-info/", { method: "PATCH", body: payload });
  },

  getAbout() {
    return apiRequest<DealerAboutInfo>("/dealer-portal/about/");
  },

  jumpIntoDealer(dealerId: string) {
    return apiRequest<JumpSessionResponse>(`/customers/dealers/${dealerId}/jump/`, { method: "POST", body: {} });
  },

  jumpIntoEmployee(employeeId: string) {
    return apiRequest<JumpSessionResponse>(`/dealer-portal/employees/${employeeId}/jump/`, {
      method: "POST",
      body: {},
    });
  },

  // Owner / admin side, from the Dealers page.
  getAccess(dealerId: string) {
    return apiRequest<DealerPortalAccess>(`/customers/dealers/${dealerId}/portal-access/`);
  },

  // Create the login or resend: the system makes a new password and emails it (WhatsApp too when connected).
  sendLogin(dealerId: string, email: string) {
    return apiRequest<DealerPortalAccess>(`/customers/dealers/${dealerId}/portal-access/`, {
      method: "POST",
      body: { email },
    });
  },

  getDealerEmployeeCash(dealerId: string) {
    return apiRequest<EmployeeCashTeam>(`/customers/dealers/${dealerId}/employee-cash/`);
  },

  officeReceiveEmployeeCash(dealerId: string, employeeId: string, notes = "") {
    return apiRequest<CashReceivedResult>(
      `/customers/dealers/${dealerId}/employees/${employeeId}/cash-received/`,
      { method: "POST", body: { notes } },
    );
  },

  getOfficeExpenses(status: "" | ExpenseStatus = "") {
    return apiRequest<{ counts: Record<ExpenseStatus, number>; results: DealerExpense[] }>(
      `/customers/dealer-expenses/${status ? `?status=${status}` : ""}`,
    );
  },

  reviewExpense(expenseId: string, decision: "APPROVE" | "REJECT", note = "") {
    return apiRequest<DealerExpense>(`/customers/dealer-expenses/${expenseId}/review/`, {
      method: "POST",
      body: { decision, note },
    });
  },

  revokeAccess(dealerId: string) {
    return apiRequest<DealerPortalAccess>(`/customers/dealers/${dealerId}/portal-access/`, { method: "DELETE" });
  },
};
