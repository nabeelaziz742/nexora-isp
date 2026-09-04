import { apiRequest } from "@/services/api-client";
import type {
  AutomatedRunResult,
  OverdueEligibilityItem,
  ServiceSuspensionLog,
  SuspensionDashboardMetrics,
  SuspensionPolicy,
} from "@/types/suspension";

export const suspensionService = {
  getDashboardMetrics(): Promise<SuspensionDashboardMetrics> {
    return apiRequest<SuspensionDashboardMetrics>("/customers/suspensions/dashboard/");
  },

  getOverdueEligibility(): Promise<OverdueEligibilityItem[]> {
    return apiRequest<OverdueEligibilityItem[]>("/customers/suspensions/eligibility/");
  },

  getSuspensionHistory(serviceId?: string): Promise<ServiceSuspensionLog[]> {
    const query = serviceId ? `?service_id=${serviceId}` : "";
    return apiRequest<ServiceSuspensionLog[]>(`/customers/suspensions/history/${query}`);
  },

  getPolicy(): Promise<SuspensionPolicy> {
    return apiRequest<SuspensionPolicy>("/customers/suspensions/policy/");
  },

  updatePolicy(data: Partial<SuspensionPolicy>): Promise<SuspensionPolicy> {
    return apiRequest<SuspensionPolicy>("/customers/suspensions/policy/", {
      method: "PUT",
      body: JSON.stringify(data),
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
        body: JSON.stringify(payload),
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
        body: JSON.stringify(payload),
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
