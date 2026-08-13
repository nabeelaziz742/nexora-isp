import { apiClient } from "@/services/api-client";

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
};