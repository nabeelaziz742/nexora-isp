import { apiRequest } from "@/services/api-client";

import type {
  BillingSummary,
  Invoice,
  InvoiceDetail,
  InvoiceFilters,
  Payment,
  PaymentFilters,
  RecordInvoicePaymentPayload,
} from "@/types/billing";

function buildQuery(
  values: Record<string, string | undefined>,
): string {
  const params = new URLSearchParams();

  Object.entries(values).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });

  const query = params.toString();

  return query ? `?${query}` : "";
}

export const billingService = {
  getSummary(): Promise<BillingSummary> {
    return apiRequest<BillingSummary>(
      "/billing/summary/",
    );
  },

  getInvoices(
    filters: InvoiceFilters = {},
  ): Promise<Invoice[]> {
    const query = buildQuery({
      status: filters.status,
      search: filters.search,
      billing_period: filters.billing_period,
      due_state: filters.due_state,
      service_account_id:
        filters.service_account_id,
      customer_id: filters.customer_id,
    });

    return apiRequest<Invoice[]>(
      `/billing/invoices/${query}`,
    );
  },

  getInvoice(
    invoiceId: string,
  ): Promise<InvoiceDetail> {
    return apiRequest<InvoiceDetail>(
      `/billing/invoices/${invoiceId}/`,
    );
  },

  getPayments(
    filters: PaymentFilters = {},
  ): Promise<Payment[]> {
    const query = buildQuery({
      search: filters.search,
      payment_method: filters.payment_method,
      service_account_id:
        filters.service_account_id,
      customer_id: filters.customer_id,
    });

    return apiRequest<Payment[]>(
      `/billing/payments/${query}`,
    );
  },

  recordInvoicePayment(
    invoiceId: string,
    payload: RecordInvoicePaymentPayload,
  ): Promise<Payment> {
    return apiRequest<Payment>(
      `/billing/invoices/${invoiceId}/payments/`,
      {
        method: "POST",
        body: payload,
      },
    );
  },

  generateInvoice(payload: {
    service_account_id: string;
    billing_year: number;
    billing_month: number;
  }): Promise<Invoice> {
    return apiRequest<Invoice>(
      "/billing/invoices/generate/",
      {
        method: "POST",
        body: payload,
      },
    );
  },
};