import { apiRequest, normalizeList, type ListResponse } from "@/services/api-client";
import type {
  AutomatedRunResult,
  OverdueEligibilityItem,
  ServiceSuspensionLog,
  SuspensionDashboardMetrics,
  SuspensionPolicy,
} from "@/types/suspension";

// The eligibility API returns service_account_id / customer_phone / current_status /
// invoices_snapshot; map them onto the field names the UI uses.
type RawEligibilityItem = Partial<OverdueEligibilityItem> & {
  service_account_id?: string;
  customer_phone?: string;
  current_status?: string;
  invoices_snapshot?: OverdueEligibilityItem["unpaid_invoices"];
};

function toEligibilityItem(raw: RawEligibilityItem): OverdueEligibilityItem {
  return {
    ...raw,
    service_id: raw.service_id ?? raw.service_account_id ?? "",
    phone: raw.phone ?? raw.customer_phone ?? "",
    status: raw.status ?? raw.current_status ?? "",
    unpaid_invoices: raw.unpaid_invoices ?? raw.invoices_snapshot ?? [],
  } as OverdueEligibilityItem;
}

export const suspensionService = {
  getDashboardMetrics(): Promise<SuspensionDashboardMetrics> {
    return apiRequest<SuspensionDashboardMetrics>("/customers/suspensions/dashboard/");
  },

  async getOverdueEligibility(): Promise<OverdueEligibilityItem[]> {
    const res = await apiRequest<ListResponse<RawEligibilityItem>>("/customers/suspensions/eligibility/");
    return normalizeList<RawEligibilityItem>(res).map(toEligibilityItem);
  },

  async getSuspendedServices(): Promise<OverdueEligibilityItem[]> {
    const res = await apiRequest<ListResponse<RawEligibilityItem>>("/customers/suspensions/suspended/");
    return normalizeList<RawEligibilityItem>(res).map(toEligibilityItem);
  },

  async getSuspensionHistory(serviceId?: string): Promise<ServiceSuspensionLog[]> {
    const query = serviceId ? `?service_account_id=${encodeURIComponent(serviceId)}` : "";
    const res = await apiRequest<ListResponse<ServiceSuspensionLog>>(`/customers/suspensions/history/${query}`);
    return normalizeList<ServiceSuspensionLog>(res);
  },

  getPolicy(): Promise<SuspensionPolicy> {
    return apiRequest<SuspensionPolicy>("/customers/suspensions/policy/");
  },

  updatePolicy(data: Partial<SuspensionPolicy>): Promise<SuspensionPolicy> {
    return apiRequest<SuspensionPolicy>("/customers/suspensions/policy/", {
      method: "PUT",
      body: data,
    });
  },

  runAutomatedEngine(): Promise<AutomatedRunResult> {
    return apiRequest<AutomatedRunResult>("/customers/suspensions/run/", {
      method: "POST",
    });
  },

  suspendService(serviceId: string, payload: { reason: string; trigger_type?: string }): Promise<{
    message: string;
    log: ServiceSuspensionLog;
  }> {
    return apiRequest<{ message: string; log: ServiceSuspensionLog }>(
      `/customers/services/${serviceId}/suspend/`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  restoreService(serviceId: string, payload: { reason: string; trigger_type?: string }): Promise<{
    message: string;
    log: ServiceSuspensionLog;
  }> {
    return apiRequest<{ message: string; log: ServiceSuspensionLog }>(
      `/customers/services/${serviceId}/restore/`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  getCustomerCommunicationHistory(customerId: string): Promise<Array<{
    id: string;
    template_name: string;
    channel: string;
    recipient: string;
    status: string;
    subject: string;
    body: string;
    error_message?: string;
    created_at: string;
    dispatched_at: string | null;
  }>> {
    return apiRequest(`/communications/customer/${customerId}/history/`);
  },
};
