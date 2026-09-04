import { apiRequest } from "@/services/api-client";

export type DealerStatus = "ACTIVE" | "INACTIVE" | "SUSPENDED" | "TERMINATED";
export type CommissionType = "PERCENTAGE" | "FLAT_PER_SUBSCRIBER";

export interface DealerItem {
  id: string;
  dealer_code: string;
  name: string;
  company_name?: string;
  cnic?: string;
  phone: string;
  alternate_phone?: string;
  email?: string;
  address_line?: string;
  country?: string;
  city?: string;
  area?: string;
  assigned_area?: string;
  assigned_area_name?: string;
  commission_rate_percentage: string | number;
  commission_type: CommissionType;
  joining_date: string;
  status: DealerStatus;
  notes?: string;
  customers_count?: number;
  created_at: string;
  updated_at: string;
}

export interface DealerCreatePayload {
  name: string;
  company_name?: string;
  cnic?: string;
  phone: string;
  alternate_phone?: string;
  email?: string;
  address_line?: string;
  country?: string;
  city?: string;
  area?: string;
  assigned_area?: string;
  commission_rate_percentage?: number | string;
  commission_type?: CommissionType;
  joining_date?: string;
  status?: DealerStatus;
  notes?: string;
}

export interface Dealer360Data {
  dealer: DealerItem;
  metrics: {
    total_customers: number;
    active_customers: number;
    inactive_customers: number;
    total_invoiced: string;
    total_collected: string;
    total_outstanding: string;
    calculated_commission: string;
  };
  customers: {
    id: string;
    customer_number: string;
    full_name: string;
    phone: string;
    is_active: boolean;
    created_at: string;
    service_number: string | null;
    service_status: string | null;
    package_name: string | null;
    monthly_price: string | number | null;
  }[];
  recent_collections: {
    id: string;
    payment_number: string;
    amount: string;
    payment_method: string;
    paid_at: string;
    customer_name: string;
    customer_number: string;
  }[];
}

export const dealersService = {
  getDealers(params?: { status?: string; city?: string; area?: string; search?: string }) {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.city) query.set("city", params.city);
    if (params?.area) query.set("area", params.area);
    if (params?.search) query.set("search", params.search);

    const qs = query.toString();
    return apiRequest<DealerItem[]>(`/customers/dealers/${qs ? `?${qs}` : ""}`);
  },

  getDealer(id: string) {
    return apiRequest<DealerItem>(`/customers/dealers/${id}/`);
  },

  createDealer(data: DealerCreatePayload) {
    return apiRequest<DealerItem>("/customers/dealers/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateDealer(id: string, data: Partial<DealerCreatePayload>) {
    return apiRequest<DealerItem>(`/customers/dealers/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  toggleStatus(id: string) {
    return apiRequest<{ id: string; dealer_code: string; name: string; status: DealerStatus }>(
      `/customers/dealers/${id}/status/`,
      {
        method: "PATCH",
      }
    );
  },

  getDealer360(id: string) {
    return apiRequest<Dealer360Data>(`/customers/dealers/${id}/360/`);
  },
};
