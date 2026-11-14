import { apiRequest } from "@/services/api-client";

export type DealerPaymentMethod = "CASH" | "MOBILE_WALLET" | "BANK_TRANSFER";

export interface DealerRights {
  can_view_customers: boolean;
  can_collect_payments: boolean;
  can_recharge: boolean;
  can_request_customers: boolean;
  can_view_collections: boolean;
}

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
  name: string;
  rights: DealerRights;
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
    commission_type?: "PERCENTAGE" | "FLAT_PER_USER";
    commission_rate?: string;
  };
  organization_name: string;
  month: string;
  total_customers: number;
  active_connections: number;
  suspended_connections: number;
  expiring_in_3_days: number;
  total_outstanding?: string;
  collected_this_month?: string;
  collected_by_me_this_month: string;
  commission_this_month?: string;
}

export interface DealerCustomerRow {
  service_id: string;
  service_number: string;
  customer_number: string;
  customer_name: string;
  phone: string;
  area: string;
  package_name: string;
  monthly_price: string;
  status: string;
  billing_mode: "MONTHLY" | "PREPAID";
  expiry_date: string | null;
  days_to_expiry: number | null;
  outstanding: string;
  oldest_due_date: string | null;
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
  collected_by_me: boolean;
  collected_by: string;
}

export interface DealerCollections {
  month: string;
  total_collected: string;
  collected_by_me: string;
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
  rights: DealerRights;
}

export interface DealerPortalAccess {
  has_login: boolean;
  is_enabled: boolean;
  email: string;
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

export const dealerPortalService = {
  getRequests() {
    return apiRequest<{
      results: DealerRequestRow[];
      packages: { id: string; name: string; monthly_price: string }[];
      default_city: string;
    }>("/dealer-portal/requests/");
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

  collectPayment(
    serviceId: string,
    payload: { amount: string; payment_method: DealerPaymentMethod; reference?: string; notes?: string },
  ) {
    return apiRequest<{ receipt: DealerReceipt; service: DealerCustomerRow }>(
      `/dealer-portal/services/${serviceId}/payments/`,
      { method: "POST", body: payload },
    );
  },

  recharge(serviceId: string, payload: { months: number; payment_method: DealerPaymentMethod; reference?: string }) {
    return apiRequest<{ receipt: DealerReceipt | null; amount: string; new_expiry_date: string; service: DealerCustomerRow }>(
      `/dealer-portal/services/${serviceId}/recharge/`,
      { method: "POST", body: payload },
    );
  },

  getCollections(month?: string) {
    return apiRequest<DealerCollections>(`/dealer-portal/collections/${month ? `?month=${month}` : ""}`);
  },

  // The dealer's own employees (dealer login only).
  getEmployees() {
    return apiRequest<{ results: DealerEmployee[]; max_employees: number }>("/dealer-portal/employees/");
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

  // Owner / admin side, from the Dealers page.
  getAccess(dealerId: string) {
    return apiRequest<DealerPortalAccess>(`/customers/dealers/${dealerId}/portal-access/`);
  },

  setAccess(dealerId: string, payload: { email: string; password: string }) {
    return apiRequest<DealerPortalAccess>(`/customers/dealers/${dealerId}/portal-access/`, {
      method: "POST",
      body: payload,
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
