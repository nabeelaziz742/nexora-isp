import { apiRequest } from "@/services/api-client";

export type DealerPaymentMethod = "CASH" | "MOBILE_WALLET" | "BANK_TRANSFER";

export interface DealerSummary {
  dealer: {
    name: string;
    company_name: string;
    dealer_code: string;
    commission_type: "PERCENTAGE" | "FLAT_PER_USER";
    commission_rate: string;
  };
  organization_name: string;
  month: string;
  total_customers: number;
  active_connections: number;
  suspended_connections: number;
  expiring_in_3_days: number;
  total_outstanding: string;
  collected_this_month: string;
  collected_by_me_this_month: string;
  commission_this_month: string;
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
}

export interface DealerCollections {
  month: string;
  total_collected: string;
  collected_by_me: string;
  commission: string;
  results: DealerCollectionRow[];
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

  revokeAccess(dealerId: string) {
    return apiRequest<DealerPortalAccess>(`/customers/dealers/${dealerId}/portal-access/`, { method: "DELETE" });
  },
};
