import { apiRequest } from "@/services/api-client";

import type {
  BillingSummary,
  CustomInvoicePayload,
  FinancialLedger,
  Invoice,
  InvoiceDetail,
  InvoiceFilters,
  MonthlyBillingRunPayload,
  MonthlyBillingRunResult,
  Payment,
  PaymentFilters,
  PaymentReceipt,
  PaymentReversalPayload,
  RecordInvoicePaymentPayload,
  RecordPaymentWithAllocationsPayload,
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

  async getInvoices(
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

    const res = await apiRequest<any>(
      `/billing/invoices/${query}`,
    );
    return Array.isArray(res) ? res : (res?.results ?? []);
  },

  getInvoice(
    invoiceId: string,
  ): Promise<InvoiceDetail> {
    return apiRequest<InvoiceDetail>(
      `/billing/invoices/${invoiceId}/`,
    );
  },

  cancelInvoice(
    invoiceId: string,
    cancellationReason: string,
  ): Promise<Invoice> {
    return apiRequest<Invoice>(
      `/billing/invoices/${invoiceId}/cancel/`,
      {
        method: "POST",
        body: { cancellation_reason: cancellationReason },
      },
    );
  },

  createCustomInvoice(
    payload: CustomInvoicePayload,
  ): Promise<InvoiceDetail> {
    return apiRequest<InvoiceDetail>(
      "/billing/invoices/custom/",
      {
        method: "POST",
        body: payload,
      },
    );
  },

  runMonthlyBilling(
    payload: MonthlyBillingRunPayload,
  ): Promise<MonthlyBillingRunResult> {
    return apiRequest<MonthlyBillingRunResult>(
      "/billing/invoices/monthly-run/",
      {
        method: "POST",
        body: payload,
      },
    );
  },

  async getPayments(
    filters: PaymentFilters = {},
  ): Promise<Payment[]> {
    const query = buildQuery({
      search: filters.search,
      payment_method: filters.payment_method,
      service_account_id:
        filters.service_account_id,
      customer_id: filters.customer_id,
    });

    const res = await apiRequest<any>(
      `/billing/payments/${query}`,
    );
    return Array.isArray(res) ? res : (res?.results ?? []);
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

  recordPaymentWithAllocations(
    payload: RecordPaymentWithAllocationsPayload,
  ): Promise<Payment> {
    return apiRequest<Payment>(
      "/billing/payments/record/",
      {
        method: "POST",
        body: payload,
      },
    );
  },

  reversePayment(
    paymentId: string,
    payload: PaymentReversalPayload,
  ): Promise<Payment> {
    return apiRequest<Payment>(
      `/billing/payments/${paymentId}/reverse/`,
      {
        method: "POST",
        body: payload,
      },
    );
  },

  getReceipt(
    paymentId: string,
  ): Promise<PaymentReceipt> {
    return apiRequest<PaymentReceipt>(
      `/billing/payments/${paymentId}/receipt/`,
    );
  },

  getLedger(params: {
    customer_id?: string;
    service_account_id?: string;
    start_date?: string;
    end_date?: string;
  } = {}): Promise<FinancialLedger> {
    const query = buildQuery(params);
    return apiRequest<FinancialLedger>(
      `/billing/ledger/${query}`,
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