import { apiBlob, apiClient } from "@/services/api-client";

export type SubscriberOverview = {
  total_customers: number;
  active_customers: number;
  inactive_customers: number;
  total_services: number;
  active_services: number;
  non_active_services: number;
  customers_with_services: number;
  customers_without_services: number;
  total_packages: number;
  active_packages: number;
};

export type ServiceStatusDistribution = {
  status: string;
  service_count: number;
};

export type PackageContribution = {
  package_id: string;
  package_code: string;
  package_name: string;
  download_speed_mbps: number;
  upload_speed_mbps: number;
  monthly_price: string;
  is_active: boolean;
  service_count: number;
  active_service_count: number;
};

export type PackageRevenueContext = {
  package_id: string;
  package_code: string;
  package_name: string;
  service_count: number;
  invoiced_amount: string;
  collected_amount: string;
  outstanding_amount: string;
};

export const reportsService = {
  getSubscriberOverview(): Promise<SubscriberOverview> {
    return apiClient.get<SubscriberOverview>(
      "/reports/subscriber-overview/",
    );
  },

  getServiceStatusDistribution(): Promise<
    ServiceStatusDistribution[]
  > {
    return apiClient.get<ServiceStatusDistribution[]>(
      "/reports/service-status-distribution/",
    );
  },

  getPackageContribution(): Promise<
    PackageContribution[]
  > {
    return apiClient.get<PackageContribution[]>(
      "/reports/package-contribution/",
    );
  },

  getPackageRevenueContext(): Promise<
    PackageRevenueContext[]
  > {
    return apiClient.get<PackageRevenueContext[]>(
      "/reports/package-revenue-context/",
    );
  },

  getReversalsReport(filters: ReversalsFilters = {}): Promise<ReversalsReport> {
    return apiClient.get<ReversalsReport>(
      `/reports/audit/reversals/${reversalsQuery(filters)}`,
    );
  },

  downloadReversalsCsv(filters: ReversalsFilters = {}): Promise<Blob> {
    const query = reversalsQuery({ ...filters });
    return apiBlob(
      `/reports/audit/reversals/${query ? `${query}&` : "?"}format=csv`,
    );
  },
};

export type ReversalEventType =
  | "PAYMENT_REVERSED"
  | "INVOICE_VOIDED"
  | "INVOICE_WRITTEN_OFF"
  | "POS_SALE_CANCELLED"
  | "CUSTOMER_DEACTIVATED";

export interface ReversalsFilters {
  start_date?: string;
  end_date?: string;
  actor_id?: string;
  event_type?: ReversalEventType | "";
}

export interface ReversalRecord {
  id: string;
  event_type: ReversalEventType;
  event_label: string;
  reference: string;
  customer_number: string;
  customer_name: string;
  amount: string;
  reason: string;
  actor_id: string | null;
  actor_name: string;
  created_at: string;
}

export interface ReversalsReport {
  records: ReversalRecord[];
  total_count: number;
  total_amount: string;
  by_type: { event_type: ReversalEventType; event_label: string; count: number; amount: string }[];
  by_actor: { actor_id: string | null; actor_name: string; count: number; amount: string }[];
}

function reversalsQuery(filters: ReversalsFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}