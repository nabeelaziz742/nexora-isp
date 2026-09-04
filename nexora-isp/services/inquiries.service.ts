import { apiRequest } from "@/services/api-client";

export type InquiryStatus =
  | "NEW"
  | "CONTACTED"
  | "FEASIBILITY_PENDING"
  | "FEASIBLE"
  | "NOT_FEASIBLE"
  | "FOLLOW_UP"
  | "CONVERTED"
  | "LOST"
  | "CANCELLED";

export type FeasibilityStatus =
  | "PENDING"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "FEASIBLE"
  | "NOT_FEASIBLE"
  | "CANCELLED";

export type NotFeasibleReason =
  | "NO_COVERAGE"
  | "NO_PORT"
  | "NO_NODE"
  | "CAPACITY_UNAVAILABLE"
  | "INFRASTRUCTURE_UNAVAILABLE"
  | "DISTANCE_LIMITATION"
  | "OTHER";

export interface InquiryItem {
  id: string;
  inquiry_number: string;
  full_name: string;
  phone: string;
  alternate_phone?: string;
  email?: string;
  cnic?: string;
  address_line: string;
  country?: string;
  city: string;
  area: string;
  preferred_package?: string;
  preferred_package_name?: string;
  preferred_package_speed?: number;
  preferred_package_price?: string;
  connection_type: "FIBER" | "WIRELESS" | "COPPER" | "OTHER";
  source: string;
  assigned_staff?: string;
  assigned_staff_name?: string;
  dealer?: string;
  dealer_name?: string;
  status: InquiryStatus;
  notes?: string;
  follow_up_date?: string | null;
  converted_customer?: string | null;
  converted_customer_number?: string | null;
  converted_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface InquiryCreatePayload {
  full_name: string;
  phone: string;
  alternate_phone?: string;
  email?: string;
  cnic?: string;
  address_line: string;
  country?: string;
  city: string;
  area: string;
  preferred_package?: string;
  connection_type?: string;
  source?: string;
  assigned_staff?: string;
  dealer?: string;
  notes?: string;
  follow_up_date?: string | null;
}

export interface FeasibilityAssessmentItem {
  id: string;
  feasibility_number: string;
  inquiry?: string;
  inquiry_number?: string;
  customer?: string;
  customer_number?: string;
  address_line: string;
  city: string;
  area: string;
  package?: string;
  package_name?: string;
  connection_type: string;
  network_node?: string;
  network_node_name?: string;
  assigned_technician?: string;
  assigned_technician_name?: string;
  status: FeasibilityStatus;
  not_feasible_reason?: NotFeasibleReason | "";
  not_feasible_details?: string;
  assessment_date?: string | null;
  completion_date?: string | null;
  remarks?: string;
  created_at: string;
  updated_at: string;
}

export interface FeasibilityCreatePayload {
  inquiry?: string;
  customer?: string;
  address_line: string;
  city: string;
  area: string;
  package?: string;
  connection_type?: string;
  network_node?: string;
  assigned_technician?: string;
  status?: FeasibilityStatus;
  remarks?: string;
}

export const inquiriesService = {
  getInquiries(params?: {
    status?: string;
    city?: string;
    area?: string;
    package_id?: string;
    source?: string;
    search?: string;
  }) {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.city) query.set("city", params.city);
    if (params?.area) query.set("area", params.area);
    if (params?.package_id) query.set("package_id", params.package_id);
    if (params?.source) query.set("source", params.source);
    if (params?.search) query.set("search", params.search);

    const qs = query.toString();
    return apiRequest<InquiryItem[]>(`/customers/inquiries/${qs ? `?${qs}` : ""}`);
  },

  getInquiry(id: string) {
    return apiRequest<InquiryItem>(`/customers/inquiries/${id}/`);
  },

  createInquiry(data: InquiryCreatePayload) {
    return apiRequest<InquiryItem>("/customers/inquiries/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateInquiry(id: string, data: Partial<InquiryCreatePayload>) {
    return apiRequest<InquiryItem>(`/customers/inquiries/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  transitionStatus(id: string, data: { status: InquiryStatus; notes?: string; follow_up_date?: string | null }) {
    return apiRequest<InquiryItem>(`/customers/inquiries/${id}/status-transitions/`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  convertInquiry(
    id: string,
    data: {
      internet_package_id: string;
      billing_day?: number;
      due_day?: number;
      network_node_id?: string;
      assigned_ip?: string;
      device_id?: string;
    }
  ) {
    return apiRequest<{
      status: string;
      customer_id: string;
      service_account_id: string;
      detail: string;
    }>(`/customers/inquiries/${id}/convert/`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Feasibility Assessments
  getFeasibilities(params?: { inquiry_id?: string; status?: string; search?: string }) {
    const query = new URLSearchParams();
    if (params?.inquiry_id) query.set("inquiry_id", params.inquiry_id);
    if (params?.status) query.set("status", params.status);
    if (params?.search) query.set("search", params.search);

    const qs = query.toString();
    return apiRequest<FeasibilityAssessmentItem[]>(`/customers/feasibilities/${qs ? `?${qs}` : ""}`);
  },

  getFeasibility(id: string) {
    return apiRequest<FeasibilityAssessmentItem>(`/customers/feasibilities/${id}/`);
  },

  createFeasibility(data: FeasibilityCreatePayload) {
    return apiRequest<FeasibilityAssessmentItem>("/customers/feasibilities/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateFeasibility(id: string, data: Partial<FeasibilityAssessmentItem>) {
    return apiRequest<FeasibilityAssessmentItem>(`/customers/feasibilities/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },
};
