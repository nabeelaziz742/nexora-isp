import { apiRequest } from "@/services/api-client";

export interface CompanyProfile {
  id: string;
  name: string;
  code: string;
  phone: string;
  email: string;
  address: string;
  city: string;
  timezone: string;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const settingsService = {
  getCompanyProfile(): Promise<CompanyProfile> {
    return apiRequest<CompanyProfile>(`/tenant/organization/`);
  },

  updateCompanyProfile(data: Partial<CompanyProfile>): Promise<CompanyProfile> {
    return apiRequest<CompanyProfile>(`/tenant/organization/`, {
      method: "PATCH",
      body: data,
    });
  },
};
