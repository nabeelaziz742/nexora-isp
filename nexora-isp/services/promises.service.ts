import { apiRequest } from "@/services/api-client";

export type PromiseStatus =
  | "PENDING"
  | "ACTIVE"
  | "FULFILLED"
  | "BROKEN"
  | "EXPIRED"
  | "CANCELLED";

export interface PromiseToPayItem {
  id: string;
  promise_number: string;
  customer: string;
  customer_name: string;
  customer_number: string;
  customer_phone: string;
  service_account: string;
  service_number: string;
  invoice?: string | null;
  invoice_number?: string | null;
  outstanding_amount: string | number;
  promised_amount: string | number;
  promise_date: string;
  deadline: string;
  status: PromiseStatus;
  notes?: string;
  failure_reason?: string;
  completed_at?: string | null;
  created_by?: string;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface PromiseCreatePayload {
  customer_id: string;
  service_account_id: string;
  invoice_id?: string;
  promised_amount: string | number;
  promise_date: string;
  deadline: string;
  notes?: string;
  status?: PromiseStatus;
}

export const promisesService = {
  getPromises(params?: {
    customer_id?: string;
    service_account_id?: string;
    status?: string;
    search?: string;
  }) {
    const query = new URLSearchParams();
    if (params?.customer_id) query.set("customer_id", params.customer_id);
    if (params?.service_account_id) query.set("service_account_id", params.service_account_id);
    if (params?.status) query.set("status", params.status);
    if (params?.search) query.set("search", params.search);

    const qs = query.toString();
    return apiRequest<PromiseToPayItem[]>(`/billing/promises/${qs ? `?${qs}` : ""}`);
  },

  getPromise(id: string) {
    return apiRequest<PromiseToPayItem>(`/billing/promises/${id}/`);
  },

  createPromise(data: PromiseCreatePayload) {
    return apiRequest<PromiseToPayItem>("/billing/promises/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updatePromise(id: string, data: { notes?: string; deadline?: string }) {
    return apiRequest<PromiseToPayItem>(`/billing/promises/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  transitionStatus(
    id: string,
    data: { status: PromiseStatus; failure_reason?: string; notes?: string }
  ) {
    return apiRequest<PromiseToPayItem>(`/billing/promises/${id}/status-transitions/`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};
