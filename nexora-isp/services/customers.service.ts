import { apiRequest } from "@/services/api-client";

export type CustomerServiceStatus =
  | "ACTIVE"
  | "GRACE_PERIOD"
  | "SUSPENSION_PENDING"
  | "SUSPENDED_NON_PAYMENT"
  | "RESTORE_PENDING";

export interface CustomerListItem {
  id: string;
  customer_number: string;
  full_name: string;
  phone: string;
  email: string;
  area: string;
  city: string;
  is_active: boolean;
  service_number: string | null;
  service_status: CustomerServiceStatus | null;
  package_name: string | null;
  monthly_price: string | number | null;
  created_at: string;
}

export interface InternetPackage {
  id: string;
  name: string;
  code: string;
  description?: string;
  download_speed_mbps: number;
  upload_speed_mbps: number;
  monthly_price: string | number;
  is_active: boolean;
  subscribers_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface InternetPackagePayload {
  name: string;
  code: string;
  description?: string;
  download_speed_mbps: number;
  upload_speed_mbps: number;
  monthly_price: number | string;
  is_active?: boolean;
}

export interface CustomerNetworkAssignment {
  id: string;
  network_node_id: string;
  network_node_name: string;
  network_node_code: string;
  username: string;
  ip_address: string | null;
  is_active: boolean;
}

export interface CustomerDeviceAssignment {
  id: string;
  device_id: string;
  asset_tag: string;
  device_type: string;
  device_status: string;
  assigned_at: string;
  returned_at: string | null;
  return_condition: string | null;
  is_active: boolean;
}

export interface CustomerBillingProfile {
  billing_cycle: string;
  billing_day: number;
  due_day: number;
  is_active: boolean;
}

export interface CustomerServiceAccount {
  id: string;
  service_number: string;
  status: CustomerServiceStatus;
  activated_at: string | null;
  internet_package: InternetPackage;
  network_assignment: CustomerNetworkAssignment | null;
  device_assignments: CustomerDeviceAssignment[];
  billing_profile: CustomerBillingProfile | null;
}

export interface CustomerNotificationPreference {
  sms_enabled: boolean;
  whatsapp_enabled: boolean;
}

export interface CustomerDetail {
  id: string;
  customer_number: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  alternate_phone: string;
  email: string;
  address_line: string;
  area: string;
  city: string;
  is_active: boolean;
  service_accounts: CustomerServiceAccount[];
  notification_preference: CustomerNotificationPreference | null;
  created_at: string;
  updated_at: string;
}

export interface CustomerActivationPayload {
  internet_package_id: string;
  network_node_id: string;
  device_id?: string | null;
  first_name: string;
  last_name?: string;
  phone: string;
  alternate_phone?: string;
  email?: string;
  address_line: string;
  area?: string;
  city: string;
  network_username?: string;
  network_ip_address?: string | null;
  device_assignment_notes?: string;
  billing_day: number;
  due_day: number;
  sms_enabled?: boolean;
  whatsapp_enabled?: boolean;
}

export interface CustomerActivationResponse {
  detail: string;
  customer: {
    id: string;
    customer_number: string;
    full_name: string;
    phone: string;
  };
  service_account: {
    id: string;
    service_number: string;
    status: CustomerServiceStatus;
    internet_package_id: string;
  };
  network_assignment: {
    id: string;
    network_node_id: string;
    username: string;
    ip_address: string | null;
  };
  provisioning_request: {
    id: string;
    action: string;
    status: string;
  };
  device_assignment: {
    id: string;
    device_id: string;
    asset_tag: string;
    device_type: string;
    device_status: string;
  } | null;
}

export interface CustomerUpdatePayload {
  first_name?: string;
  last_name?: string;
  phone?: string;
  alternate_phone?: string;
  email?: string;
  address_line?: string;
  area?: string;
  city?: string;
  is_active?: boolean;
  sms_enabled?: boolean;
  whatsapp_enabled?: boolean;
}

export interface GetCustomersParams {
  search?: string;
  status?: CustomerServiceStatus | "";
  city?: string;
  area?: string;
  package_id?: string;
  is_active?: boolean | string;
}

interface GetPackagesParams {
  search?: string;
  status?: "active" | "inactive" | "";
}

function buildQueryString(params?: Record<string, string | boolean | undefined>) {
  if (!params) return "";
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (typeof value === "boolean") {
      searchParams.set(key, value ? "true" : "false");
    } else if (value && String(value).trim()) {
      searchParams.set(key, String(value).trim());
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

export const customersService = {
  async getCustomers(params?: GetCustomersParams): Promise<CustomerListItem[]> {
    const res = await apiRequest<any>(
      `/customers/${buildQueryString(params as Record<string, string | boolean | undefined>)}`
    );
    return Array.isArray(res) ? res : (res?.results ?? []);
  },

  getCustomer(customerId: string): Promise<CustomerDetail> {
    return apiRequest<CustomerDetail>(`/customers/${customerId}/`);
  },

  updateCustomer(
    customerId: string,
    payload: Partial<CustomerUpdatePayload>
  ): Promise<CustomerDetail> {
    return apiRequest<CustomerDetail>(`/customers/${customerId}/`, {
      method: "PATCH",
      body: payload,
    });
  },

  toggleCustomerStatus(customerId: string): Promise<CustomerDetail> {
    return apiRequest<CustomerDetail>(`/customers/${customerId}/status/`, {
      method: "PATCH",
    });
  },

  async getInternetPackages(params?: GetPackagesParams): Promise<InternetPackage[]> {
    const res = await apiRequest<any>(
      `/customers/packages/${buildQueryString(params as Record<string, string | undefined>)}`
    );
    return Array.isArray(res) ? res : (res?.results ?? []);
  },

  getInternetPackage(packageId: string): Promise<InternetPackage> {
    return apiRequest<InternetPackage>(`/customers/packages/${packageId}/`);
  },

  createInternetPackage(payload: InternetPackagePayload): Promise<InternetPackage> {
    return apiRequest<InternetPackage>("/customers/packages/", {
      method: "POST",
      body: payload,
    });
  },

  updateInternetPackage(
    packageId: string,
    payload: Partial<InternetPackagePayload>
  ): Promise<InternetPackage> {
    return apiRequest<InternetPackage>(`/customers/packages/${packageId}/`, {
      method: "PUT",
      body: payload,
    });
  },

  deleteInternetPackage(packageId: string): Promise<void> {
    return apiRequest<void>(`/customers/packages/${packageId}/`, {
      method: "DELETE",
    });
  },

  toggleInternetPackageStatus(packageId: string): Promise<InternetPackage> {
    return apiRequest<InternetPackage>(`/customers/packages/${packageId}/status/`, {
      method: "PATCH",
    });
  },

  activateCustomer(
    payload: CustomerActivationPayload
  ): Promise<CustomerActivationResponse> {
    return apiRequest<CustomerActivationResponse>("/customers/activate/", {
      method: "POST",
      body: payload,
    });
  },
};