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
  download_speed_mbps: number;
  upload_speed_mbps: number;
  monthly_price: string | number;
  is_active: boolean;
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
  notification_preference:
    | CustomerNotificationPreference
    | null;
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

interface GetCustomersParams {
  search?: string;
  status?: CustomerServiceStatus | "";
}

function buildQueryString(
  params?: GetCustomersParams,
) {
  const searchParams = new URLSearchParams();

  if (params?.search?.trim()) {
    searchParams.set(
      "search",
      params.search.trim(),
    );
  }

  if (params?.status) {
    searchParams.set("status", params.status);
  }

  const queryString = searchParams.toString();

  return queryString ? `?${queryString}` : "";
}

export const customersService = {
  getCustomers(
    params?: GetCustomersParams,
  ): Promise<CustomerListItem[]> {
    return apiRequest<CustomerListItem[]>(
      `/customers/${buildQueryString(params)}`,
    );
  },

  getCustomer(
    customerId: string,
  ): Promise<CustomerDetail> {
    return apiRequest<CustomerDetail>(
      `/customers/${customerId}/`,
    );
  },

  getInternetPackages(): Promise<
    InternetPackage[]
  > {
    return apiRequest<InternetPackage[]>(
      "/customers/packages/",
    );
  },

  activateCustomer(
    payload: CustomerActivationPayload,
  ): Promise<CustomerActivationResponse> {
    return apiRequest<CustomerActivationResponse>(
      "/customers/activate/",
      {
        method: "POST",
        body: payload,
      },
    );
  },
};